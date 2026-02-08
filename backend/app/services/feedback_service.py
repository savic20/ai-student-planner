"""
Feedback Service
----------------
Business logic for feedback collection and analysis.

RESPONSIBILITIES:
- Save user feedback
- Trigger Reflector Agent
- Store AI analysis
- Calculate aggregate stats
"""

import logging
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import Feedback, Plan, User
from app.models.feedback import (
    FeedbackSubmission,
    ReflectionAnalysis,
    FeedbackResponse
)
from app.agents.reflector_agent import ReflectorAgent

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service for managing feedback.
    
    USAGE:
    service = FeedbackService()
    feedback = await service.submit_feedback(db, user_id, submission)
    """
    
    def __init__(self):
        """Initialize feedback service"""
        self.reflector_agent = ReflectorAgent()
        logger.info("Feedback service initialized")
    
    async def submit_feedback(
        self,
        db: Session,
        user_id: int,
        submission: FeedbackSubmission
    ) -> Tuple[Feedback, Optional[ReflectionAnalysis]]:
        """
        Submit feedback and trigger AI analysis.
        
        WORKFLOW:
        1. Validate plan exists
        2. Save feedback to database
        3. Trigger Reflector Agent
        4. Save analysis
        
        RETURNS:
        (Feedback object, ReflectionAnalysis)
        """
        # Verify plan exists and belongs to user
        plan = db.query(Plan).filter(
            Plan.id == submission.plan_id,
            Plan.user_id == user_id
        ).first()
        
        if not plan:
            raise ValueError("Plan not found or access denied")
        
        # Get previous feedback for context
        previous_feedback = db.query(Feedback).filter(
            Feedback.plan_id == submission.plan_id,
            Feedback.week_number < submission.week_number
        ).order_by(Feedback.week_number).all()
        
        # Convert to Pydantic models
        previous_submissions = []
        for f in previous_feedback:
            task_comp = f.task_completion or {}
            previous_submissions.append(
                FeedbackSubmission(
                    plan_id=f.plan_id,
                    week_number=f.week_number,
                    difficulty=f.overall_difficulty,
                    tasks_completed=task_comp.get("completed", 0),
                    tasks_total=task_comp.get("total", 0),
                    challenges=None,
                    what_worked=None,
                    suggested_changes=None
                )
            )
        
        logger.info(f"Analyzing feedback for plan {submission.plan_id}, week {submission.week_number}...")
        
        # Trigger AI analysis
        analysis = await self.reflector_agent.analyze_feedback(
            feedback=submission,
            plan_data=plan.plan_data,
            previous_feedback=previous_submissions
        )
        
        # Save feedback to database
        feedback = Feedback(
            user_id=user_id,
            plan_id=submission.plan_id,
            week_number=submission.week_number,
            overall_difficulty=submission.difficulty.value,
            task_completion={
                "completed": submission.tasks_completed,
                "total": submission.tasks_total
            },
            comments=f"Challenges: {submission.challenges or 'None'}\nWhat worked: {submission.what_worked or 'None'}\nSuggested changes: {submission.suggested_changes or 'None'}\nNotes: {submission.extra_notes or 'None'}",
            adjustment_requests=analysis.adjustments if analysis else {},
            replan_triggered=False
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        logger.info(f"✅ Feedback saved (ID: {feedback.id})")
        
        return feedback, analysis
    
    def get_plan_feedback(
        self,
        db: Session,
        plan_id: int,
        user_id: int
    ) -> List[Feedback]:
        """
        Get all feedback for a plan.
        
        SECURITY:
        Only returns feedback if plan belongs to user.
        """
        # Verify plan ownership
        plan = db.query(Plan).filter(
            Plan.id == plan_id,
            Plan.user_id == user_id
        ).first()
        
        if not plan:
            return []
        
        feedback = db.query(Feedback).filter(
            Feedback.plan_id == plan_id
        ).order_by(Feedback.week_number).all()
        
        return feedback
    
    def get_feedback(
        self,
        db: Session,
        feedback_id: int,
        user_id: int
    ) -> Optional[Feedback]:
        """Get specific feedback by ID."""
        feedback = db.query(Feedback).filter(
            Feedback.id == feedback_id,
            Feedback.user_id == user_id
        ).first()
        
        return feedback
    
    def calculate_stats(
        self,
        db: Session,
        plan_id: int,
        user_id: int
    ) -> dict:
        """
        Calculate aggregate statistics.
        
        RETURNS:
        {
            "total_weeks": 4,
            "avg_completion_rate": 0.75,
            "avg_difficulty": "moderate",
            "improvement_trend": "improving"
        }
        """
        feedback_list = self.get_plan_feedback(db, plan_id, user_id)
        
        if not feedback_list:
            return {
                "total_weeks": 0,
                "avg_completion_rate": 0,
                "avg_difficulty": None,
                "improvement_trend": None
            }
        
        # Calculate averages
        total_weeks = len(feedback_list)
        
        # Calculate completion rate from task_completion JSON
        completion_rates = []
        for f in feedback_list:
            task_comp = f.task_completion or {}
            completed = task_comp.get("completed", 0)
            total = task_comp.get("total", 1)
            if total > 0:
                completion_rates.append(completed / total)
        
        avg_completion = sum(completion_rates) / len(completion_rates) if completion_rates else 0
        
        # Average difficulty (convert to numeric)
        difficulty_map = {
            "very_easy": 1,
            "easy": 2,
            "moderate": 3,
            "hard": 4,
            "very_hard": 5
        }
        avg_difficulty_num = sum(
            difficulty_map.get(f.overall_difficulty, 3)
            for f in feedback_list
        ) / total_weeks
        
        # Map back to string
        if avg_difficulty_num < 1.5:
            avg_difficulty = "very_easy"
        elif avg_difficulty_num < 2.5:
            avg_difficulty = "easy"
        elif avg_difficulty_num < 3.5:
            avg_difficulty = "moderate"
        elif avg_difficulty_num < 4.5:
            avg_difficulty = "hard"
        else:
            avg_difficulty = "very_hard"
        
        # Detect trend (if 3+ weeks)
        improvement_trend = None
        if total_weeks >= 3:
            recent_rates = []
            for f in feedback_list[-3:]:
                task_comp = f.task_completion or {}
                completed = task_comp.get("completed", 0)
                total = task_comp.get("total", 1)
                if total > 0:
                    recent_rates.append(completed / total)
            
            recent_completion = sum(recent_rates) / len(recent_rates) if recent_rates else 0
            
            if recent_completion > avg_completion + 0.1:
                improvement_trend = "improving"
            elif recent_completion < avg_completion - 0.1:
                improvement_trend = "declining"
            else:
                improvement_trend = "stable"
        
        return {
            "total_weeks": total_weeks,
            "avg_completion_rate": round(avg_completion, 2),
            "avg_difficulty": avg_difficulty,
            "improvement_trend": improvement_trend
        }


# =============================================================================
# GLOBAL SERVICE INSTANCE
# =============================================================================
_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """Get the global feedback service instance."""
    global _service
    if _service is None:
        _service = FeedbackService()
    return _service