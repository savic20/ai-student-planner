"""
Syllabus API Routes
-------------------
HTTP endpoints for syllabus management.

ENDPOINTS:
- POST /syllabus/upload       - Upload and parse syllabus
- GET  /syllabus/             - Get all user's syllabi
- GET  /syllabus/{id}         - Get specific syllabus
- POST /syllabus/{id}/reparse - Re-parse existing syllabus
- DELETE /syllabus/{id}       - Delete syllabus
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.db.models import User
from app.models.syllabus import (
    SyllabusUploadResponse,
    SyllabusParseResponse,
    SyllabusListResponse,
    ParsedSyllabusData
)
from app.models.user import MessageResponse
from app.services.syllabus_service import get_syllabus_service
from app.utils.auth import get_current_active_user
from app.config import settings

# Create router
router = APIRouter()

# Get service
syllabus_service = get_syllabus_service()


# =============================================================================
# UPLOAD SYLLABUS
# =============================================================================

@router.post("/upload", response_model=SyllabusUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_syllabus(
    file: UploadFile = File(..., description="Syllabus file (PDF, DOCX, or TXT)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a syllabus file.
    
    ACCEPTS:
    - PDF (.pdf)
    - Word (.docx)
    - Plain text (.txt)
    
    MAX SIZE:
    10 MB (configurable in settings)
    
    PROCESS:
    1. Validate file type and size
    2. Extract text from file
    3. Parse with AI agent
    4. Store in database
    
    RESPONSE:
    Returns upload status immediately.
    Parsing happens in the background.
    
    EXAMPLE:
    ```bash
    curl -X POST "http://localhost:8000/syllabus/upload" \
      -H "Authorization: Bearer YOUR_TOKEN" \
      -F "file=@syllabus.pdf"
    ```
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size
    if len(file_content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB} MB"
        )
    
    # Upload and parse
    syllabus, error = await syllabus_service.upload_and_parse(
        db=db,
        user_id=current_user.id,
        file_content=file_content,
        filename=file.filename
    )
    
    if error:
        # Parsing failed, but file was saved
        if syllabus:
            return SyllabusUploadResponse(
                syllabus_id=syllabus.id,
                filename=syllabus.filename,
                file_size=syllabus.file_size,
                status="failed",
                message=f"Upload successful but parsing failed: {error}"
            )
        else:
            # File processing failed completely
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
    
    # Success
    return SyllabusUploadResponse(
        syllabus_id=syllabus.id,
        filename=syllabus.filename,
        file_size=syllabus.file_size,
        status="completed",
        message="Syllabus uploaded and parsed successfully"
    )


# =============================================================================
# GET ALL SYLLABI
# =============================================================================

@router.get("/", response_model=SyllabusListResponse)
async def get_syllabi(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all syllabi for current user.
    
    RETURNS:
    List of syllabi with their parsed data.
    
    EXAMPLE:
    ```bash
    curl -X GET "http://localhost:8000/syllabus/" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    syllabi = syllabus_service.get_user_syllabi(db, current_user.id)
    
    # Convert to response models
    syllabus_responses = []
    for s in syllabi:
        syllabus_responses.append(
            SyllabusParseResponse(
                syllabus_id=s.id,
                filename=s.filename,
                is_processed=s.is_processed,
                parsed_data=ParsedSyllabusData(**s.parsed_data) if s.parsed_data else None,
                raw_text=s.raw_text[:500] + "..." if s.raw_text and len(s.raw_text) > 500 else s.raw_text,
                processing_error=s.processing_error,
                created_at=s.created_at
            )
        )
    
    return SyllabusListResponse(
        syllabi=syllabus_responses,
        total=len(syllabus_responses)
    )


# =============================================================================
# GET SPECIFIC SYLLABUS
# =============================================================================

@router.get("/{syllabus_id}", response_model=SyllabusParseResponse)
async def get_syllabus(
    syllabus_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific syllabus by ID.
    
    SECURITY:
    Only returns if syllabus belongs to current user.
    
    EXAMPLE:
    ```bash
    curl -X GET "http://localhost:8000/syllabus/1" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    syllabus = syllabus_service.get_syllabus(db, syllabus_id, current_user.id)
    
    if not syllabus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Syllabus not found"
        )
    
    return SyllabusParseResponse(
        syllabus_id=syllabus.id,
        filename=syllabus.filename,
        is_processed=syllabus.is_processed,
        parsed_data=ParsedSyllabusData(**syllabus.parsed_data) if syllabus.parsed_data else None,
        raw_text=syllabus.raw_text,
        processing_error=syllabus.processing_error,
        created_at=syllabus.created_at
    )


# =============================================================================
# REPARSE SYLLABUS
# =============================================================================

@router.post("/{syllabus_id}/reparse", response_model=SyllabusParseResponse)
async def reparse_syllabus(
    syllabus_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Re-parse an existing syllabus.
    
    USE CASES:
    - Initial parsing failed
    - Want to try again with updated agent
    
    EXAMPLE:
    ```bash
    curl -X POST "http://localhost:8000/syllabus/1/reparse" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    syllabus, error = await syllabus_service.reparse_syllabus(
        db=db,
        syllabus_id=syllabus_id,
        user_id=current_user.id
    )
    
    if error and not syllabus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error
        )
    
    return SyllabusParseResponse(
        syllabus_id=syllabus.id,
        filename=syllabus.filename,
        is_processed=syllabus.is_processed,
        parsed_data=ParsedSyllabusData(**syllabus.parsed_data) if syllabus.parsed_data else None,
        raw_text=syllabus.raw_text[:500] + "..." if syllabus.raw_text and len(syllabus.raw_text) > 500 else syllabus.raw_text,
        processing_error=syllabus.processing_error,
        created_at=syllabus.created_at
    )


# =============================================================================
# DELETE SYLLABUS
# =============================================================================

@router.delete("/{syllabus_id}", response_model=MessageResponse)
async def delete_syllabus(
    syllabus_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a syllabus.
    
    SECURITY:
    Only deletes if syllabus belongs to current user.
    
    EXAMPLE:
    ```bash
    curl -X DELETE "http://localhost:8000/syllabus/1" \
      -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    success, error = syllabus_service.delete_syllabus(db, syllabus_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error
        )
    
    return MessageResponse(message="Syllabus deleted successfully")


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health/check")
async def syllabus_health():
    """
    Health check for syllabus service.
    """
    return {
        "status": "healthy",
        "service": "syllabus",
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "allowed_extensions": settings.ALLOWED_EXTENSIONS
    }