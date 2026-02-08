"""
Syllabus Pydantic Models
------------------------
Request/response schemas for syllabus-related endpoints.

These define the structure of:
- Upload requests
- Parsed syllabus data
- API responses
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, date


# =============================================================================
# PARSED SYLLABUS DATA STRUCTURES
# =============================================================================

class Assignment(BaseModel):
    """
    A single assignment/task.
    
    EXAMPLE:
    {
        "name": "Essay 1: Literary Analysis",
        "due_date": "2024-10-15",
        "weight": 20,
        "type": "essay",
        "description": "Analyze themes in the novel"
    }
    """
    name: str = Field(..., description="Assignment name")
    due_date: Optional[str] = Field(None, description="Due date (YYYY-MM-DD)")
    weight: Optional[float] = Field(None, description="Percentage of final grade")
    type: Optional[str] = Field(None, description="Type: essay, homework, project, etc.")
    description: Optional[str] = Field(None, description="Assignment description")


class Exam(BaseModel):
    """
    An exam or test.
    
    EXAMPLE:
    {
        "name": "Midterm Exam",
        "date": "2024-10-20",
        "weight": 30,
        "type": "midterm",
        "topics": ["Chapters 1-5", "Lectures 1-10"]
    }
    """
    name: str = Field(..., description="Exam name")
    date: Optional[str] = Field(None, description="Exam date (YYYY-MM-DD)")
    weight: Optional[float] = Field(None, description="Percentage of final grade")
    type: Optional[str] = Field(None, description="Type: midterm, final, quiz")
    topics: Optional[List[str]] = Field(default=[], description="Topics covered")


class ImportantDate(BaseModel):
    """
    Important date (holidays, breaks, etc.)
    
    EXAMPLE:
    {
        "date": "2024-11-25",
        "event": "Thanksgiving Break",
        "type": "holiday"
    }
    """
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    event: str = Field(..., description="Event name")
    type: Optional[str] = Field(None, description="Type: holiday, deadline, etc.")


class ParsedSyllabusData(BaseModel):
    """
    Structured data extracted from syllabus.
    
    This is what the Parser Agent returns.
    
    EXAMPLE:
    {
        "course_name": "Introduction to Computer Science",
        "course_code": "CS 101",
        "instructor": "Dr. Jane Smith",
        "semester": "Fall 2024",
        "assignments": [...],
        "exams": [...],
        "important_dates": [...]
    }
    """
    course_name: Optional[str] = Field(None, description="Course name")
    course_code: Optional[str] = Field(None, description="Course code (e.g., CS 101)")
    instructor: Optional[str] = Field(None, description="Instructor name")
    semester: Optional[str] = Field(None, description="Semester (e.g., Fall 2024)")
    
    assignments: List[Assignment] = Field(default=[], description="List of assignments")
    exams: List[Exam] = Field(default=[], description="List of exams")
    important_dates: List[ImportantDate] = Field(default=[], description="Important dates")
    
    # Optional additional info
    office_hours: Optional[str] = Field(None, description="Office hours")
    textbook: Optional[str] = Field(None, description="Required textbook")
    grading_policy: Optional[str] = Field(None, description="Grading policy summary")


# =============================================================================
# API REQUEST/RESPONSE MODELS
# =============================================================================

class SyllabusUploadResponse(BaseModel):
    """
    Response after uploading a syllabus.
    
    RETURNED BY: POST /syllabus/upload
    
    EXAMPLE:
    {
        "syllabus_id": 1,
        "filename": "cs101_syllabus.pdf",
        "file_size": 245678,
        "status": "processing",
        "message": "Syllabus uploaded successfully. Processing..."
    }
    """
    syllabus_id: int = Field(..., description="Database ID of uploaded syllabus")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="Status: processing, completed, failed")
    message: str = Field(..., description="Status message")


class SyllabusParseResponse(BaseModel):
    """
    Response with parsed syllabus data.
    
    RETURNED BY: GET /syllabus/{id}
    
    EXAMPLE:
    {
        "syllabus_id": 1,
        "filename": "cs101_syllabus.pdf",
        "is_processed": true,
        "parsed_data": { ... },
        "raw_text": "Course Syllabus..."
    }
    """
    syllabus_id: int
    filename: str
    is_processed: bool = Field(..., description="Has parsing completed?")
    parsed_data: Optional[ParsedSyllabusData] = Field(None, description="Extracted data")
    raw_text: Optional[str] = Field(None, description="Raw extracted text")
    processing_error: Optional[str] = Field(None, description="Error if parsing failed")
    created_at: datetime


class SyllabusListResponse(BaseModel):
    """
    List of user's syllabi.
    
    RETURNED BY: GET /syllabus/
    """
    syllabi: List[SyllabusParseResponse]
    total: int


# =============================================================================
# VALIDATION
# =============================================================================

def validate_parsed_data(data: Dict[str, Any]) -> ParsedSyllabusData:
    """
    Validate and convert LLM output to ParsedSyllabusData.
    
    WHY THIS EXISTS:
    LLMs sometimes return slightly malformed JSON.
    This function fixes common issues and validates the data.
    
    USAGE:
    llm_output = {"course_name": "CS 101", "assignments": [...]}
    validated = validate_parsed_data(llm_output)
    """
    try:
        # Pydantic will validate and convert
        return ParsedSyllabusData(**data)
    except Exception as e:
        raise ValueError(f"Invalid syllabus data: {str(e)}")


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    # Example: Create parsed syllabus data
    parsed = ParsedSyllabusData(
        course_name="Introduction to AI",
        course_code="CS 401",
        instructor="Dr. Smith",
        semester="Fall 2024",
        assignments=[
            Assignment(
                name="Homework 1",
                due_date="2024-09-15",
                weight=10,
                type="homework"
            ),
            Assignment(
                name="Final Project",
                due_date="2024-12-10",
                weight=40,
                type="project"
            )
        ],
        exams=[
            Exam(
                name="Midterm",
                date="2024-10-20",
                weight=25,
                type="midterm"
            )
        ]
    )
    
    print("✅ Parsed syllabus data created:")
    print(parsed.model_dump_json(indent=2))