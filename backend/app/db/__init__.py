"""
Database Package
----------------
Exposes database models and utilities.
"""

from app.db.database import Base, engine, SessionLocal, get_db, init_db, check_db_connection
from app.db.models import (
    User, Syllabus, Chat, Message, Plan, Feedback, TokenUsage,
    PlanStatus, MessageRole, DifficultyLevel
)

__all__ = [
    # Database setup
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "check_db_connection",
    
    # Models
    "User",
    "Syllabus",
    "Chat",
    "Message",
    "Plan",
    "Feedback",
    "TokenUsage",
    
    # Enums
    "PlanStatus",
    "MessageRole",
    "DifficultyLevel",
]