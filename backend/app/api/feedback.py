"""
Feedback API Routes
-------------------
HTTP endpoints for feedback and reflection.

ENDPOINTS:
- POST /feedback/submit       - Submit weekly feedback
- GET  /feedback/plan/{plan_id} - Get all feedback for a plan
- GET  /feedback/{id}          - Get specific feedback
- GET  /feedback/plan/{plan_id}/stats - Get aggregate statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import User
from app.models.feedback import (
    FeedbackSubmission,
    FeedbackResponse,
    FeedbackListResponse,
    ReflectionAnalysis
)
from app.services.feedback_service import get_feedback_service
from app.utils.auth import get_current_active_user

# Create router
router = APIRouter()

# Get service
feedback_service = get_feedback_service()


# =============================================================================
# SUBMIT FEEDBACK
# =============================================================================

@router.post("/submit", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    submission: FeedbackSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit weekly feedback and get AI analysis.
    
    WORKFLOW:
    1. User completes a week
    2. Submits feedback about difficulty, completion, challenges
    3. AI analyzes feedback
    4. Returns insights and suggestions
    
    REQUEST BODY:
    ```json
    {
      "plan_id": 1,
      "week_number": 1,
      "difficulty": "hard",
      "tasks_completed": 3,
      "tasks_total": 5,
      "challenges": "Too much work on Monday",
      "what_worked": "Evening study sessions",
      "suggested_changes": "Spread work more evenly"
    }
    ```
    
    RESPONSE:
    Returns feedback with AI analysis including:
    - Summary of the issue
    - Specific insights and recommendations
    - Suggested adjustments to the plan
    
    EXAMPLE:
    ```bash
    curl -X POST "http://localhost:8000/feedback/submit" \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "plan_id": 1,
        "week_number": 1,
        "difficulty": "hard",
        "tasks_completed": 3,
        "tasks_total": 5,
        "challenges": "Too much work"
      }'
    ```
    """
    try:
        feedback, analysis = await feedback_service.submit_feedback(
            db=db,
            user_id=current_user.id,
            submission=submission
        )
        
        return FeedbackResponse(
            feedback_id=feedback.id,
            plan_id=feedback.plan_id,
            week_number=feedback.week_number,
            difficulty=feedback.overall_difficulty,  # Fixed: use overall_difficulty
            analysis=analysis,
            created_at=feedback.created_at,
            message="Feedback submitted and analyzed successfully"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback submission failed: {str(e)}"
        )


# =============================================================================
# GET PLAN FEEDBACK
# =============================================================================

@router.get("/plan/{plan_id}", response_model=FeedbackListResponse)
async def get_plan_feedback(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all feedback for a plan.
    
    RETURNS:
    List of all feedback submissions with AI analyses.
    
    EXAMPLE:
    ```bash
    curl -X GET "http://localhost:8000/feedback/plan/1" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    feedback_list = feedback_service.get_plan_feedback(db, plan_id, current_user.id)
    
    # Convert to response models
    feedback_responses = []
    for f in feedback_list:
        # Parse stored data
        task_comp = f.task_completion or {}
        
        # Try to get AI analysis from adjustment_requests (we store it there now)
        analysis = None  # We don't store full analysis in DB anymore, just adjustments
        
        feedback_responses.append(
            FeedbackResponse(
                feedback_id=f.id,
                plan_id=f.plan_id,
                week_number=f.week_number,
                difficulty=f.overall_difficulty,
                analysis=analysis,
                created_at=f.created_at,
                message="Feedback retrieved"
            )
        )
    
    # Calculate stats
    stats = feedback_service.calculate_stats(db, plan_id, current_user.id)
    
    return FeedbackListResponse(
        feedback_items=feedback_responses,
        total=len(feedback_responses),
        average_difficulty=stats.get("avg_difficulty"),
        completion_rate=stats.get("avg_completion_rate")
    )


# =============================================================================
# GET SPECIFIC FEEDBACK
# =============================================================================

@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get specific feedback by ID.
    
    SECURITY:
    Only returns if feedback belongs to current user.
    
    EXAMPLE:
    ```bash
    curl -X GET "http://localhost:8000/feedback/1" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    feedback = feedback_service.get_feedback(db, feedback_id, current_user.id)
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    analysis = None  # Analysis not stored in current schema
    
    return FeedbackResponse(
        feedback_id=feedback.id,
        plan_id=feedback.plan_id,
        week_number=feedback.week_number,
        difficulty=feedback.overall_difficulty,
        analysis=analysis,
        created_at=feedback.created_at,
        message="Feedback retrieved"
    )


# =============================================================================
# GET STATISTICS
# =============================================================================

@router.get("/plan/{plan_id}/stats")
async def get_plan_stats(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregate statistics for a plan.
    
    RETURNS:
    ```json
    {
      "total_weeks": 4,
      "avg_completion_rate": 0.75,
      "avg_difficulty": "moderate",
      "improvement_trend": "improving"
    }
    ```
    
    EXAMPLE:
    ```bash
    curl -X GET "http://localhost:8000/feedback/plan/1/stats" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    stats = feedback_service.calculate_stats(db, plan_id, current_user.id)
    
    if stats["total_weeks"] == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feedback found for this plan"
        )
    
    return stats


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health/check")
async def feedback_health():
    """Health check for feedback service."""
    return {
        "status": "healthy",
        "service": "feedback",
        "ai_agent": "reflector_agent"
    }