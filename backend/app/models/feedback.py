"""
Feedback Pydantic Models
------------------------
Request/response schemas for feedback and reflection.

WORKFLOW:
1. User completes a week
2. System asks for feedback
3. Reflector agent analyzes
4. Plan gets adjusted
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class DifficultyLevel(str, Enum):
    """How difficult was the week?"""
    VERY_EASY = "very_easy"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    VERY_HARD = "very_hard"


class AdjustmentType(str, Enum):
    """Type of adjustment needed"""
    REDUCE_WORKLOAD = "reduce_workload"
    INCREASE_WORKLOAD = "increase_workload"
    REDISTRIBUTE_TASKS = "redistribute_tasks"
    ADD_BREAKS = "add_breaks"
    CHANGE_SCHEDULE = "change_schedule"
    NO_CHANGE = "no_change"


# =============================================================================
# FEEDBACK SUBMISSION
# =============================================================================

class FeedbackSubmission(BaseModel):
    """
    User's feedback for a week.
    
    EXAMPLE:
    {
        "plan_id": 1,
        "week_number": 1,
        "difficulty": "hard",
        "tasks_completed": 3,
        "tasks_total": 5,
        "challenges": "Too much work on Monday",
        "what_worked": "Evening study sessions were great",
        "suggested_changes": "Need more breaks"
    }
    """
    plan_id: int = Field(..., description="Plan being reviewed")
    week_number: int = Field(..., description="Which week")
    
    # Ratings
    difficulty: DifficultyLevel = Field(..., description="How hard was it?")
    
    # Completion stats
    tasks_completed: int = Field(..., description="How many tasks finished")
    tasks_total: int = Field(..., description="Total tasks planned")
    
    # Free text feedback
    challenges: Optional[str] = Field(None, description="What was difficult?")
    what_worked: Optional[str] = Field(None, description="What went well?")
    suggested_changes: Optional[str] = Field(None, description="What to change?")
    
    # Additional data
    extra_notes: Optional[str] = Field(None, description="Any other notes")


# =============================================================================
# REFLECTION ANALYSIS (AI OUTPUT)
# =============================================================================

class ReflectionInsight(BaseModel):
    """
    AI's analysis of feedback.
    
    EXAMPLE:
    {
        "observation": "User struggled with Monday workload",
        "recommendation": "Reduce Monday tasks by 30%",
        "adjustment_type": "reduce_workload"
    }
    """
    observation: str = Field(..., description="What the AI noticed")
    recommendation: str = Field(..., description="What to do about it")
    adjustment_type: AdjustmentType = Field(..., description="Type of change")
    confidence: float = Field(..., description="How confident (0-1)")


class ReflectionAnalysis(BaseModel):
    """
    Complete AI analysis of user's feedback.
    
    RETURNED BY: Reflector Agent
    
    EXAMPLE:
    {
        "summary": "Week was too difficult, user fell behind",
        "insights": [...],
        "overall_adjustment": "reduce_workload",
        "adjustments": {
            "reduce_daily_hours": 0.5,
            "add_buffer_days": 1
        }
    }
    """
    summary: str = Field(..., description="Overall summary")
    insights: List[ReflectionInsight] = Field(default=[], description="Specific insights")
    overall_adjustment: AdjustmentType = Field(..., description="Main change needed")
    
    # Specific adjustments
    adjustments: Dict[str, Any] = Field(
        default={},
        description="Specific parameters to change"
    )
    
    # Patterns detected
    patterns: List[str] = Field(default=[], description="Recurring patterns")


# =============================================================================
# FEEDBACK RESPONSE MODELS
# =============================================================================

class FeedbackResponse(BaseModel):
    """
    Response after submitting feedback.
    
    RETURNED BY: POST /feedback/submit
    """
    feedback_id: int = Field(..., description="Database ID")
    plan_id: int
    week_number: int
    difficulty: DifficultyLevel
    analysis: Optional[ReflectionAnalysis] = Field(None, description="AI analysis")
    created_at: datetime
    
    message: str = Field(
        default="Feedback recorded. Analyzing...",
        description="Status message"
    )


class FeedbackListResponse(BaseModel):
    """
    List of all feedback for a plan.
    
    RETURNED BY: GET /feedback/plan/{plan_id}
    """
    feedback_items: List[FeedbackResponse]
    total: int
    average_difficulty: Optional[str] = None
    completion_rate: Optional[float] = None


# =============================================================================
# ADJUSTMENT REQUEST
# =============================================================================

class AdjustmentRequest(BaseModel):
    """
    Request to adjust plan based on feedback.
    
    SENT TO: POST /plans/{id}/adjust
    
    EXAMPLE:
    {
        "feedback_ids": [1, 2, 3],
        "manual_adjustments": {
            "reduce_daily_hours": 1
        }
    }
    """
    feedback_ids: List[int] = Field(..., description="Which feedback to consider")
    manual_adjustments: Optional[Dict[str, Any]] = Field(
        None,
        description="Override AI suggestions"
    )


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    # Example: User submits feedback
    feedback = FeedbackSubmission(
        plan_id=1,
        week_number=1,
        difficulty=DifficultyLevel.HARD,
        tasks_completed=3,
        tasks_total=5,
        challenges="Too much work on Monday, couldn't finish everything",
        what_worked="Evening study sessions were productive",
        suggested_changes="Spread the work more evenly across the week"
    )
    
    print("✅ Feedback created:")
    print(feedback.model_dump_json(indent=2))
    
    # Example: AI analysis
    analysis = ReflectionAnalysis(
        summary="User found the week too difficult, only completed 60% of tasks",
        insights=[
            ReflectionInsight(
                observation="Monday had 3 tasks taking 6 hours total",
                recommendation="Reduce Monday to 2 tasks (4 hours)",
                adjustment_type=AdjustmentType.REDISTRIBUTE_TASKS,
                confidence=0.85
            )
        ],
        overall_adjustment=AdjustmentType.REDUCE_WORKLOAD,
        adjustments={
            "reduce_daily_hours": 1.0,
            "add_buffer_days": 1
        },
        patterns=["Struggles on Mondays", "Evening study works well"]
    )
    
    print("\n✅ Analysis created:")
    print(analysis.model_dump_json(indent=2))