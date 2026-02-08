"""
Plan Service
------------
Business logic for study plan management.

RESPONSIBILITIES:
- Generate plans from syllabi
- Save plans to database
- Retrieve user's plans
- Update task status
- Track plan versions
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import Plan, User, Syllabus
from app.models.syllabus import ParsedSyllabusData
from app.models.plan import StudyPlan, TaskUpdate, TaskStatus
from app.agents.planner_agent import PlannerAgent

logger = logging.getLogger(__name__)


class PlanService:
    """
    Service for managing study plans.
    
    USAGE:
    service = PlanService()
    plan = await service.generate_plan(db, user_id, syllabus_id, preferences)
    """
    
    def __init__(self):
        """Initialize plan service"""
        self.planner_agent = PlannerAgent()
        logger.info("Plan service initialized")
    
    async def generate_plan(
        self,
        db: Session,
        user_id: int,
        syllabus_id: int,
        preferences: Dict[str, Any]
    ) -> Plan:
        """
        Generate a new study plan from a syllabus.
        
        WORKFLOW:
        1. Get syllabus from database
        2. Verify ownership
        3. Check syllabus is parsed
        4. Generate plan with AI
        5. Save to database
        
        ARGS:
        - db: Database session
        - user_id: User creating the plan
        - syllabus_id: Syllabus to plan from
        - preferences: User study preferences
        
        RETURNS:
        Plan database object
        
        RAISES:
        ValueError if syllabus not found/accessible/unparsed
        
        EXAMPLE:
        plan = await service.generate_plan(
            db, user_id=1, syllabus_id=1,
            preferences={"study_hours_per_day": 3}
        )
        """
        # Get syllabus
        syllabus = db.query(Syllabus).filter(
            Syllabus.id == syllabus_id,
            Syllabus.user_id == user_id
        ).first()
        
        if not syllabus:
            raise ValueError("Syllabus not found or access denied")
        
        if not syllabus.is_processed or not syllabus.parsed_data:
            raise ValueError("Syllabus has not been parsed yet")
        
        # Convert to Pydantic model
        syllabus_data = ParsedSyllabusData(**syllabus.parsed_data)
        
        logger.info(f"Generating plan for syllabus {syllabus_id}...")
        
        # Generate plan with AI
        study_plan = await self.planner_agent.generate_plan(
            syllabus_data,
            preferences
        )
        
        # Create database record
        plan = Plan(
            user_id=user_id,
            syllabus_id=syllabus_id,
            title=study_plan.title,
            description=study_plan.description,
            plan_data=study_plan.model_dump(),
            status="active",  # New plans are active by default
            version_number=1
        )
        
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        logger.info(f"✅ Plan created (ID: {plan.id})")
        
        return plan
    
    def get_plan(self, db: Session, plan_id: int, user_id: int) -> Optional[Plan]:
        """
        Get a plan by ID.
        
        SECURITY:
        Only returns plan if it belongs to the user.
        
        RETURNS:
        Plan object or None
        """
        plan = db.query(Plan).filter(
            Plan.id == plan_id,
            Plan.user_id == user_id
        ).first()
        
        return plan
    
    def get_user_plans(
        self,
        db: Session,
        user_id: int,
        status: Optional[str] = None
    ) -> List[Plan]:
        """
        Get all plans for a user.
        
        ARGS:
        - db: Database session
        - user_id: User ID
        - status: Optional filter by status (active, completed, archived)
        
        RETURNS:
        List of Plan objects, ordered by most recent first
        """
        query = db.query(Plan).filter(Plan.user_id == user_id)
        
        if status:
            query = query.filter(Plan.status == status)
        
        plans = query.order_by(Plan.created_at.desc()).all()
        
        return plans
    
    def update_task_status(
        self,
        db: Session,
        plan_id: int,
        user_id: int,
        task_id: str,
        update_data: TaskUpdate
    ) -> Optional[Plan]:
        """
        Update a task's status within a plan.
        
        WORKFLOW:
        1. Get plan
        2. Find task in plan_data JSON
        3. Update task fields
        4. Save plan
        
        ARGS:
        - plan_id: Plan database ID
        - user_id: User ID (for security)
        - task_id: Task ID (e.g., "task_1")
        - update_data: TaskUpdate with new values
        
        RETURNS:
        Updated Plan or None if not found
        
        EXAMPLE:
        plan = service.update_task_status(
            db, plan_id=1, user_id=1, task_id="task_1",
            update_data=TaskUpdate(status=TaskStatus.COMPLETED)
        )
        """
        plan = self.get_plan(db, plan_id, user_id)
        
        if not plan or not plan.plan_data:
            return None
        
        # Find and update task in JSON
        plan_data = plan.plan_data
        task_found = False
        
        for week in plan_data.get("weeks", []):
            for task in week.get("tasks", []):
                if task.get("id") == task_id:
                    # Update task fields
                    if update_data.status is not None:
                        task["status"] = update_data.status.value
                    
                    if update_data.actual_duration_minutes is not None:
                        task["actual_duration_minutes"] = update_data.actual_duration_minutes
                    
                    if update_data.difficulty is not None:
                        task["difficulty"] = update_data.difficulty.value
                    
                    if update_data.notes is not None:
                        task["notes"] = update_data.notes
                    
                    task_found = True
                    break
            
            if task_found:
                break
        
        if not task_found:
            logger.warning(f"Task {task_id} not found in plan {plan_id}")
            return None
        
        # Update plan
        plan.plan_data = plan_data
        plan.updated_at = datetime.utcnow()
        
        # CRITICAL: Tell SQLAlchemy that plan_data was modified
        # Without this, PostgreSQL won't detect the JSON change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(plan, "plan_data")
        
        db.commit()
        db.refresh(plan)
        
        logger.info(f"Task {task_id} updated in plan {plan_id}")
        
        return plan
    
    def update_plan_status(
        self,
        db: Session,
        plan_id: int,
        user_id: int,
        new_status: str
    ) -> Optional[Plan]:
        """
        Update a plan's status.
        
        STATUS OPTIONS:
        - active: Currently using
        - completed: Finished
        - archived: Hidden from main view
        
        EXAMPLE:
        plan = service.update_plan_status(
            db, plan_id=1, user_id=1, new_status="completed"
        )
        """
        plan = self.get_plan(db, plan_id, user_id)
        
        if not plan:
            return None
        
        valid_statuses = ["active", "completed", "archived"]
        if new_status not in valid_statuses:
            logger.warning(f"Invalid status: {new_status}")
            return None
        
        plan.status = new_status
        plan.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(plan)
        
        logger.info(f"Plan {plan_id} status updated to {new_status}")
        
        return plan
    
    def delete_plan(
        self,
        db: Session,
        plan_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a plan.
        
        SECURITY:
        Only deletes if plan belongs to user.
        
        RETURNS:
        True if deleted, False if not found
        """
        plan = self.get_plan(db, plan_id, user_id)
        
        if not plan:
            return False
        
        db.delete(plan)
        db.commit()
        
        logger.info(f"Plan {plan_id} deleted")
        
        return True
    
    def get_plan_progress(
        self,
        db: Session,
        plan_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate plan progress statistics.
        
        RETURNS:
        {
            "total_tasks": 20,
            "completed_tasks": 5,
            "pending_tasks": 15,
            "progress_percentage": 25.0,
            "total_hours_planned": 60.0,
            "total_hours_actual": 15.0
        }
        """
        plan = self.get_plan(db, plan_id, user_id)
        
        if not plan or not plan.plan_data:
            return None
        
        total_tasks = 0
        completed_tasks = 0
        total_planned_minutes = 0
        total_actual_minutes = 0
        
        for week in plan.plan_data.get("weeks", []):
            for task in week.get("tasks", []):
                total_tasks += 1
                
                # Handle both string and enum values for status
                task_status = task.get("status")
                if task_status == "completed" or (hasattr(task_status, 'value') and task_status.value == "completed"):
                    completed_tasks += 1
                
                total_planned_minutes += task.get("duration_minutes", 0)
                
                # actual_duration_minutes might not exist yet
                actual_minutes = task.get("actual_duration_minutes", 0)
                if actual_minutes:
                    total_actual_minutes += actual_minutes
        
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": total_tasks - completed_tasks,
            "progress_percentage": round(progress_percentage, 1),
            "total_hours_planned": round(total_planned_minutes / 60, 1),
            "total_hours_actual": round(total_actual_minutes / 60, 1)
        }


# =============================================================================
# GLOBAL SERVICE INSTANCE
# =============================================================================
_service: Optional[PlanService] = None


def get_plan_service() -> PlanService:
    """
    Get the global plan service instance.
    
    USAGE:
    from app.services.plan_service import get_plan_service
    
    service = get_plan_service()
    plan = await service.generate_plan(...)
    """
    global _service
    if _service is None:
        _service = PlanService()
    return _service