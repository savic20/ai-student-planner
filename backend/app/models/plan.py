"""
Plan Pydantic Models
--------------------
Request/response schemas for study plan endpoints.

PLAN STRUCTURE:
- Plan: Overall semester plan
- Task: Individual study task (read chapter, do homework, etc.)
- Week: Group of tasks for one week
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class TaskType(str, Enum):
    """Type of study task"""
    READING = "reading"
    HOMEWORK = "homework"
    STUDY = "study"
    EXAM_PREP = "exam_prep"
    PROJECT = "project"
    REVIEW = "review"
    BREAK = "break"


class TaskStatus(str, Enum):
    """Completion status of a task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class DifficultyLevel(str, Enum):
    """Difficulty level for feedback"""
    VERY_EASY = "very_easy"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    VERY_HARD = "very_hard"


# =============================================================================
# TASK MODELS
# =============================================================================

class Task(BaseModel):
    """
    A single study task.
    
    EXAMPLE:
    {
        "id": "task_1",
        "title": "Read Chapter 3",
        "description": "Introduction to Functions",
        "date": "2024-09-10",
        "duration_minutes": 60,
        "type": "reading",
        "status": "pending",
        "related_assignment_id": null
    }
    """
    id: str = Field(..., description="Unique task ID")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    date: str = Field(..., description="Task date (YYYY-MM-DD)")
    duration_minutes: int = Field(..., description="Estimated duration in minutes")
    type: TaskType = Field(..., description="Type of task")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Completion status")
    priority: Optional[int] = Field(None, description="Priority (1-5, 5 is highest)")
    related_assignment_id: Optional[int] = Field(None, description="Link to syllabus assignment")


class WeekPlan(BaseModel):
    """
    Plan for one week.
    
    EXAMPLE:
    {
        "week_number": 1,
        "start_date": "2024-09-01",
        "end_date": "2024-09-07",
        "tasks": [...]
    }
    """
    week_number: int = Field(..., description="Week number in semester")
    start_date: str = Field(..., description="Week start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Week end date (YYYY-MM-DD)")
    tasks: List[Task] = Field(default=[], description="Tasks for this week")
    notes: Optional[str] = Field(None, description="Notes for the week")


# =============================================================================
# PLAN MODELS
# =============================================================================

class StudyPlan(BaseModel):
    """
    Complete study plan for the semester.
    
    EXAMPLE:
    {
        "title": "CS 101 Study Plan - Fall 2024",
        "description": "Personalized study schedule",
        "weeks": [...],
        "total_study_hours": 120,
        "preferences": {...}
    }
    """
    title: str = Field(..., description="Plan title")
    description: Optional[str] = Field(None, description="Plan description")
    weeks: List[WeekPlan] = Field(default=[], description="Weekly plans")
    total_study_hours: Optional[float] = Field(None, description="Total hours planned")
    preferences: Dict[str, Any] = Field(default={}, description="User preferences used")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


# =============================================================================
# REQUEST MODELS
# =============================================================================

class PlanGenerationRequest(BaseModel):
    """
    Request to generate a study plan.
    
    USER PROVIDES:
    - Which syllabus to plan for
    - Their preferences (study hours, breaks, etc.)
    
    EXAMPLE:
    {
        "syllabus_id": 1,
        "preferences": {
            "study_hours_per_day": 3,
            "study_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "preferred_study_time": "evening",
            "break_frequency": 30
        }
    }
    """
    syllabus_id: int = Field(..., description="ID of syllabus to create plan for")
    
    preferences: Dict[str, Any] = Field(
        default={},
        description="User study preferences"
    )
    
    # Common preference fields (with defaults)
    study_hours_per_day: Optional[float] = Field(
        default=3.0,
        description="Target study hours per day"
    )
    study_days: Optional[List[str]] = Field(
        default=["monday", "tuesday", "wednesday", "thursday", "friday"],
        description="Days available for studying"
    )
    break_days: Optional[List[str]] = Field(
        default=[],
        description="Days to avoid scheduling (e.g., for work/extracurriculars)"
    )
    
    @validator("preferences", pre=True)
    def merge_preferences(cls, v, values):
        """Merge top-level preference fields into preferences dict"""
        if v is None:
            v = {}
        
        # Add top-level fields to preferences dict
        if "study_hours_per_day" in values:
            v["study_hours_per_day"] = values["study_hours_per_day"]
        if "study_days" in values:
            v["study_days"] = values["study_days"]
        if "break_days" in values:
            v["break_days"] = values["break_days"]
        
        return v


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class PlanResponse(BaseModel):
    """
    Response with a study plan.
    
    RETURNED BY: POST /plans/generate, GET /plans/{id}
    """
    plan_id: int = Field(..., description="Database ID of the plan")
    title: str
    description: Optional[str]
    status: str = Field(..., description="Plan status: draft, active, completed")
    plan_data: StudyPlan = Field(..., description="The actual plan")
    created_at: datetime
    updated_at: Optional[datetime]
    version_number: int = Field(default=1, description="Plan version")


class PlanListResponse(BaseModel):
    """
    List of user's plans.
    
    RETURNED BY: GET /plans/
    """
    plans: List[PlanResponse]
    total: int


class PlanSummary(BaseModel):
    """
    Brief summary of a plan.
    
    USED IN: Plan lists, quick views
    """
    plan_id: int
    title: str
    course_name: Optional[str]
    status: str
    total_tasks: int
    completed_tasks: int
    progress_percentage: float
    created_at: datetime


# =============================================================================
# TASK UPDATE MODELS
# =============================================================================

class TaskUpdate(BaseModel):
    """
    Update a task's status.
    
    EXAMPLE:
    {
        "status": "completed",
        "actual_duration_minutes": 75,
        "difficulty": "moderate",
        "notes": "Took longer than expected but understood the material"
    }
    """
    status: Optional[TaskStatus] = None
    actual_duration_minutes: Optional[int] = None
    difficulty: Optional[DifficultyLevel] = None
    notes: Optional[str] = None


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    # Example: Create a study plan
    plan = StudyPlan(
        title="CS 101 Study Plan",
        description="Fall 2024 semester plan",
        weeks=[
            WeekPlan(
                week_number=1,
                start_date="2024-09-01",
                end_date="2024-09-07",
                tasks=[
                    Task(
                        id="task_1",
                        title="Read Chapter 1",
                        date="2024-09-02",
                        duration_minutes=60,
                        type=TaskType.READING
                    ),
                    Task(
                        id="task_2",
                        title="Do Homework 1",
                        date="2024-09-05",
                        duration_minutes=120,
                        type=TaskType.HOMEWORK
                    )
                ]
            )
        ],
        total_study_hours=3.0
    )
    
    print("✅ Study plan created:")
    print(plan.model_dump_json(indent=2))