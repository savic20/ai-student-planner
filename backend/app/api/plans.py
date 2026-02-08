"""
Plan API Routes
---------------
HTTP endpoints for study plan management.

ENDPOINTS:
- POST   /plans/generate       - Generate new plan from syllabus
- GET    /plans/               - Get all user's plans
- GET    /plans/{id}           - Get specific plan
- GET    /plans/{id}/progress  - Get plan progress stats
- PUT    /plans/{id}/status    - Update plan status
- PUT    /plans/{id}/tasks/{task_id} - Update task status
- DELETE /plans/{id}           - Delete plan
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db.models import User
from app.models.plan import (
    PlanGenerationRequest,
    PlanResponse,
    PlanListResponse,
    StudyPlan,
    TaskUpdate,
    PlanSummary
)
from app.models.user import MessageResponse
from app.services.plan_service import get_plan_service
from app.utils.auth import get_current_active_user

# Create router
router = APIRouter()

# Get service
plan_service = get_plan_service()


# =============================================================================
# GENERATE PLAN
# =============================================================================

@router.post("/generate", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_plan(
    request: PlanGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new study plan from a syllabus.
    
    PROCESS:
    1. Validates syllabus exists and is parsed
    2. Uses AI to generate personalized schedule
    3. Saves plan to database
    
    REQUEST BODY:
    ```json
    {
      "syllabus_id": 1,
      "study_hours_per_day": 3,
      "study_days": ["monday", "wednesday", "friday"],
      "preferences": {
        "preferred_study_time": "evening",
        "break_frequency": 30
      }
    }
    ```
    
    RESPONSE:
    Returns the generated plan with all tasks and schedules.
    
    EXAMPLE:
    ```bash
    curl -X POST "http://localhost:8000/plans/generate" \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"syllabus_id": 1, "study_hours_per_day": 3}'
    ```
    """
    try:
        plan = await plan_service.generate_plan(
            db=db,
            user_id=current_user.id,
            syllabus_id=request.syllabus_id,
            preferences=request.preferences
        )
        
        return PlanResponse(
            plan_id=plan.id,
            title=plan.title,
            description=plan.description,
            status=plan.status,
            plan_data=StudyPlan(**plan.plan_data),
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            version_number=plan.version_number
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan generation failed: {str(e)}"
        )


# =============================================================================
# GET ALL PLANS
# =============================================================================

@router.get("/", response_model=PlanListResponse)
async def get_plans(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all plans for current user.
    
    QUERY PARAMETERS:
    - status: Filter by status (active, completed, archived)
    
    RETURNS:
    List of plans with basic info.
    
    EXAMPLE:
    ```bash
    # Get all plans
    curl -X GET "http://localhost:8000/plans/" \
      -H "Authorization: Bearer YOUR_TOKEN"
    
    # Get only active plans
    curl -X GET "http://localhost:8000/plans/?status_filter=active" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    plans = plan_service.get_user_plans(db, current_user.id, status_filter)
    
    plan_responses = []
    for p in plans:
        plan_responses.append(
            PlanResponse(
                plan_id=p.id,
                title=p.title,
                description=p.description,
                status=p.status,
                plan_data=StudyPlan(**p.plan_data) if p.plan_data else None,
                created_at=p.created_at,
                updated_at=p.updated_at,
                version_number=p.version_number
            )
        )
    
    return PlanListResponse(
        plans=plan_responses,
        total=len(plan_responses)
    )


# =============================================================================
# GET SPECIFIC PLAN
# =============================================================================

@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific plan by ID.
    
    SECURITY:
    Only returns if plan belongs to current user.
    
    EXAMPLE:
    ```bash
    curl -X GET "http://localhost:8000/plans/1" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    plan = plan_service.get_plan(db, plan_id, current_user.id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    return PlanResponse(
        plan_id=plan.id,
        title=plan.title,
        description=plan.description,
        status=plan.status,
        plan_data=StudyPlan(**plan.plan_data) if plan.plan_data else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        version_number=plan.version_number
    )


# =============================================================================
# GET PLAN PROGRESS
# =============================================================================

@router.get("/{plan_id}/progress")
async def get_plan_progress(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get progress statistics for a plan.
    
    RETURNS:
    ```json
    {
      "total_tasks": 20,
      "completed_tasks": 5,
      "pending_tasks": 15,
      "progress_percentage": 25.0,
      "total_hours_planned": 60.0,
      "total_hours_actual": 15.0
    }
    ```
    
    EXAMPLE:
    ```bash
    curl -X GET "http://localhost:8000/plans/1/progress" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    progress = plan_service.get_plan_progress(db, plan_id, current_user.id)
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    return progress


# =============================================================================
# UPDATE TASK STATUS
# =============================================================================

@router.put("/{plan_id}/tasks/{task_id}", response_model=PlanResponse)
async def update_task(
    plan_id: int,
    task_id: str,
    update_data: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a task's status.
    
    REQUEST BODY:
    ```json
    {
      "status": "completed",
      "actual_duration_minutes": 75,
      "difficulty": "moderate",
      "notes": "Took longer than expected"
    }
    ```
    
    EXAMPLE:
    ```bash
    curl -X PUT "http://localhost:8000/plans/1/tasks/task_1" \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"status": "completed", "actual_duration_minutes": 60}'
    ```
    """
    plan = plan_service.update_task_status(
        db=db,
        plan_id=plan_id,
        user_id=current_user.id,
        task_id=task_id,
        update_data=update_data
    )
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan or task not found"
        )
    
    return PlanResponse(
        plan_id=plan.id,
        title=plan.title,
        description=plan.description,
        status=plan.status,
        plan_data=StudyPlan(**plan.plan_data) if plan.plan_data else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        version_number=plan.version_number
    )


# =============================================================================
# UPDATE PLAN STATUS
# =============================================================================

@router.put("/{plan_id}/status", response_model=PlanResponse)
async def update_plan_status(
    plan_id: int,
    new_status: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a plan's status.
    
    STATUS OPTIONS:
    - active: Currently using
    - completed: Finished
    - archived: Hidden from main view
    
    EXAMPLE:
    ```bash
    curl -X PUT "http://localhost:8000/plans/1/status?new_status=completed" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    plan = plan_service.update_plan_status(
        db=db,
        plan_id=plan_id,
        user_id=current_user.id,
        new_status=new_status
    )
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found or invalid status"
        )
    
    return PlanResponse(
        plan_id=plan.id,
        title=plan.title,
        description=plan.description,
        status=plan.status,
        plan_data=StudyPlan(**plan.plan_data) if plan.plan_data else None,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        version_number=plan.version_number
    )


# =============================================================================
# DELETE PLAN
# =============================================================================

@router.delete("/{plan_id}", response_model=MessageResponse)
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a plan.
    
    SECURITY:
    Only deletes if plan belongs to current user.
    
    EXAMPLE:
    ```bash
    curl -X DELETE "http://localhost:8000/plans/1" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    success = plan_service.delete_plan(db, plan_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    return MessageResponse(message="Plan deleted successfully")


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health/check")
async def plans_health():
    """Health check for plans service."""
    return {
        "status": "healthy",
        "service": "plans",
        "ai_agent": "planner_agent"
    }