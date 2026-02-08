"""
Database Models (ORM)
---------------------
Defines the structure of all database tables.

EXPLANATION FOR BEGINNERS:
Each class = one table in PostgreSQL
Each attribute = one column
Relationships = how tables connect to each other

EXAMPLE:
class User:
    id = Column(Integer)  →  CREATE TABLE users (id INTEGER)
    email = Column(String) →  email VARCHAR
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, JSON, Enum as SQLEnum, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.database import Base


# =============================================================================
# ENUMS (Predefined choices for certain fields)
# =============================================================================

class PlanStatus(str, enum.Enum):
    """Status of a study plan"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MessageRole(str, enum.Enum):
    """Who sent the chat message"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DifficultyLevel(str, enum.Enum):
    """How difficult a task was"""
    VERY_EASY = "very_easy"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    VERY_HARD = "very_hard"


# =============================================================================
# USER MODEL
# =============================================================================

class User(Base):
    """
    User account table.
    
    RELATIONSHIPS:
    - One user can have many syllabi
    - One user can have many chats
    - One user can have many plans
    """
    __tablename__ = "users"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Profile
    full_name = Column(String(255))
    semester = Column(String(50))  # e.g., "Fall 2024", "Spring 2025"
    major = Column(String(100))
    
    # Preferences (stored as JSON)
    # Example: {"study_hours_per_day": 3, "preferred_study_time": "morning"}
    preferences = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships (access related data)
    syllabi = relationship("Syllabus", back_populates="user", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


# =============================================================================
# SYLLABUS MODEL
# =============================================================================

class Syllabus(Base):
    """
    Uploaded course syllabi.
    
    WHAT THIS STORES:
    - Original uploaded file info
    - Extracted text from PDF/DOCX
    - Parsed structured data (assignments, deadlines, etc.)
    """
    __tablename__ = "syllabi"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # File Information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))  # Where the file is stored
    file_size = Column(Integer)  # Size in bytes
    file_type = Column(String(50))  # "pdf", "docx", "txt"
    
    # Course Information
    course_name = Column(String(255))
    course_code = Column(String(50))
    instructor = Column(String(255))
    
    # Content
    raw_text = Column(Text)  # Extracted text from file
    
    # Parsed Data (JSON structure)
    # Example: {
    #   "assignments": [{"name": "Essay 1", "due_date": "2024-10-15", "weight": 20}],
    #   "exams": [...],
    #   "schedule": [...]
    # }
    parsed_data = Column(JSON)
    
    # Processing Status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text)  # Store errors if parsing fails
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="syllabi")
    plans = relationship("Plan", back_populates="syllabus")
    
    def __repr__(self):
        return f"<Syllabus(id={self.id}, course={self.course_name})>"


# =============================================================================
# CHAT MODEL
# =============================================================================

class Chat(Base):
    """
    Chat conversations between user and AI.
    
    STRUCTURE:
    - Chat = a conversation session
    - Message = individual messages within a chat
    """
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Chat Metadata
    title = Column(String(255))  # Auto-generated from first message
    is_active = Column(Boolean, default=True)
    
    # Context (what the chat is about)
    # Example: {"syllabus_id": 123, "plan_id": 456}
    context = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chat(id={self.id}, title={self.title})>"


# =============================================================================
# MESSAGE MODEL
# =============================================================================

class Message(Base):
    """
    Individual messages in a chat.
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    # Message Content
    role = Column(SQLEnum(MessageRole), nullable=False)  # user/assistant/system
    content = Column(Text, nullable=False)
    
    # Metadata
    # Example: {"agent": "planner", "tokens": 150, "model": "llama-3.3-70b"}
    message_metadata = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"


# =============================================================================
# PLAN MODEL
# =============================================================================

class Plan(Base):
    """
    Study plans created by the AI.
    
    VERSIONING:
    - Each plan can have multiple versions
    - version_number tracks revisions
    - parent_plan_id links to previous version
    """
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    syllabus_id = Column(Integer, ForeignKey("syllabi.id", ondelete="SET NULL"), nullable=True)
    
    # Plan Metadata
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(PlanStatus), default=PlanStatus.DRAFT)
    
    # Versioning
    version_number = Column(Integer, default=1)
    parent_plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    
    # Plan Data (JSON structure)
    # Example: {
    #   "tasks": [
    #     {"id": 1, "name": "Read Chapter 1", "date": "2024-10-01", "duration": 60},
    #     ...
    #   ],
    #   "goals": ["Finish all assignments", "Score 85%+"],
    #   "constraints": {"max_hours_per_day": 4}
    # }
    plan_data = Column(JSON, nullable=False)
    
    # Agent that created this plan
    created_by_agent = Column(String(50))  # "planner", "reflector", etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="plans")
    syllabus = relationship("Syllabus", back_populates="plans")
    feedback = relationship("Feedback", back_populates="plan", cascade="all, delete-orphan")
    
    # Self-referential relationship for versioning
    parent_plan = relationship("Plan", remote_side=[id], backref="revisions")
    
    def __repr__(self):
        return f"<Plan(id={self.id}, title={self.title}, v{self.version_number})>"


# =============================================================================
# FEEDBACK MODEL
# =============================================================================

class Feedback(Base):
    """
    User feedback on study plans.
    
    PURPOSE:
    - Collect weekly reflections
    - Track task completion
    - Measure difficulty
    - Trigger plan adjustments
    """
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    
    # Feedback Content
    week_number = Column(Integer)  # Which week of the semester
    
    # Task Completion
    # Example: {"completed": [1, 2, 3], "missed": [4, 5], "partial": [6]}
    task_completion = Column(JSON)
    
    # Difficulty Rating
    overall_difficulty = Column(SQLEnum(DifficultyLevel))
    
    # Task-specific difficulty
    # Example: {"task_1": "easy", "task_2": "hard"}
    task_difficulty = Column(JSON)
    
    # Free-form feedback
    comments = Column(Text)
    
    # What the user wants to adjust
    # Example: {"reduce_workload": true, "add_break_days": ["Saturday"]}
    adjustment_requests = Column(JSON)
    
    # Has this feedback triggered a replan?
    replan_triggered = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    plan = relationship("Plan", back_populates="feedback")
    
    def __repr__(self):
        return f"<Feedback(id={self.id}, week={self.week_number})>"


# =============================================================================
# TOKEN USAGE MODEL (Track LLM costs)
# =============================================================================

class TokenUsage(Base):
    """
    Track LLM API usage for cost monitoring.
    """
    __tablename__ = "token_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # API Details
    provider = Column(String(50))  # "groq", "ollama"
    model = Column(String(100))
    
    # Token Counts
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Cost (if applicable)
    estimated_cost = Column(Float, default=0.0)
    
    # Context
    endpoint = Column(String(100))  # Which API endpoint was called
    agent = Column(String(50))  # Which agent made the request
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<TokenUsage(id={self.id}, tokens={self.total_tokens})>"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_model_by_tablename(tablename: str):
    """Get model class by table name"""
    models = {
        "users": User,
        "syllabi": Syllabus,
        "chats": Chat,
        "messages": Message,
        "plans": Plan,
        "feedback": Feedback,
        "token_usage": TokenUsage
    }
    return models.get(tablename)