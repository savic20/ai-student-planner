"""
Syllabus Service
----------------
Business logic for syllabus management.

RESPONSIBILITIES:
- Save uploaded files
- Extract text from files
- Trigger parsing agent
- Store parsed data in database
- Retrieve syllabus data
"""

import logging
from typing import Optional, Tuple, List
from pathlib import Path
from sqlalchemy.orm import Session

from app.db.models import Syllabus, User
from app.models.syllabus import ParsedSyllabusData, SyllabusParseResponse
from app.utils.parsers import extract_text_from_file, validate_syllabus_content, FileParserError
from app.agents.parser_agent import ParserAgent
from app.config import settings

logger = logging.getLogger(__name__)


class SyllabusService:
    """
    Service for managing syllabi.
    
    USAGE:
    service = SyllabusService()
    syllabus = await service.upload_and_parse(db, user_id, file_content, filename)
    """
    
    def __init__(self):
        """Initialize syllabus service"""
        self.parser_agent = ParserAgent()
        
        # Ensure upload directory exists
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Syllabus service initialized")
    
    async def upload_and_parse(
        self,
        db: Session,
        user_id: int,
        file_content: bytes,
        filename: str
    ) -> Tuple[Syllabus, Optional[str]]:
        """
        Upload and parse a syllabus file.
        
        WORKFLOW:
        1. Extract text from file
        2. Validate content
        3. Save to database
        4. Parse with agent
        5. Update database with parsed data
        
        ARGS:
        - db: Database session
        - user_id: ID of user uploading
        - file_content: Raw file bytes
        - filename: Original filename
        
        RETURNS:
        (Syllabus object, error_message)
        - If successful: (syllabus, None)
        - If failed: (syllabus with error, error_message)
        
        EXAMPLE:
        with open("syllabus.pdf", "rb") as f:
            syllabus, error = await service.upload_and_parse(
                db, user_id=1, file_content=f.read(), filename="syllabus.pdf"
            )
        """
        try:
            # Step 1: Extract text from file
            logger.info(f"Extracting text from {filename}...")
            raw_text, file_type = extract_text_from_file(file_content, filename)
            
            # Step 2: Validate content
            if not validate_syllabus_content(raw_text):
                return None, "File does not appear to be a syllabus"
            
            # Step 3: Save to database (initial record)
            syllabus = Syllabus(
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                file_size=len(file_content),
                raw_text=raw_text,
                is_processed=False  # Will be updated after parsing
            )
            
            db.add(syllabus)
            db.commit()
            db.refresh(syllabus)
            
            logger.info(f"Syllabus saved to database (ID: {syllabus.id})")
            
            # Step 4: Parse with agent (async)
            try:
                logger.info(f"Parsing syllabus (ID: {syllabus.id})...")
                parsed_data = await self.parser_agent.parse_syllabus(raw_text)
                
                # Extract basic info
                syllabus.course_name = parsed_data.course_name
                syllabus.course_code = parsed_data.course_code
                syllabus.instructor = parsed_data.instructor
                
                # Store full parsed data as JSON
                syllabus.parsed_data = parsed_data.model_dump()
                syllabus.is_processed = True
                
                db.commit()
                db.refresh(syllabus)
                
                logger.info(f"✅ Syllabus parsed successfully (ID: {syllabus.id})")
                
                return syllabus, None
            
            except Exception as parse_error:
                # Parsing failed, but we still have the raw text
                logger.error(f"Parsing failed: {parse_error}")
                
                syllabus.processing_error = str(parse_error)
                syllabus.is_processed = False
                
                db.commit()
                db.refresh(syllabus)
                
                return syllabus, f"Parsing failed: {str(parse_error)}"
        
        except FileParserError as e:
            logger.error(f"File parsing error: {e}")
            return None, str(e)
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            db.rollback()
            return None, f"Upload failed: {str(e)}"
    
    def get_syllabus(self, db: Session, syllabus_id: int, user_id: int) -> Optional[Syllabus]:
        """
        Get a syllabus by ID.
        
        SECURITY:
        Only returns syllabus if it belongs to the user.
        
        RETURNS:
        Syllabus object or None if not found/unauthorized
        """
        syllabus = db.query(Syllabus).filter(
            Syllabus.id == syllabus_id,
            Syllabus.user_id == user_id
        ).first()
        
        return syllabus
    
    def get_user_syllabi(self, db: Session, user_id: int) -> List[Syllabus]:
        """
        Get all syllabi for a user.
        
        RETURNS:
        List of Syllabus objects, ordered by most recent first
        """
        syllabi = db.query(Syllabus).filter(
            Syllabus.user_id == user_id
        ).order_by(Syllabus.created_at.desc()).all()
        
        return syllabi
    
    def delete_syllabus(self, db: Session, syllabus_id: int, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a syllabus.
        
        SECURITY:
        Only deletes if syllabus belongs to the user.
        
        RETURNS:
        (success, error_message)
        """
        syllabus = self.get_syllabus(db, syllabus_id, user_id)
        
        if not syllabus:
            return False, "Syllabus not found"
        
        try:
            db.delete(syllabus)
            db.commit()
            
            logger.info(f"Syllabus deleted (ID: {syllabus_id})")
            return True, None
        
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            db.rollback()
            return False, f"Delete failed: {str(e)}"
    
    async def reparse_syllabus(
        self,
        db: Session,
        syllabus_id: int,
        user_id: int
    ) -> Tuple[Optional[Syllabus], Optional[str]]:
        """
        Re-parse an existing syllabus.
        
        USE CASE:
        - Parsing failed initially
        - User wants to try again
        - Agent was updated
        
        RETURNS:
        (syllabus, error_message)
        """
        syllabus = self.get_syllabus(db, syllabus_id, user_id)
        
        if not syllabus:
            return None, "Syllabus not found"
        
        if not syllabus.raw_text:
            return None, "No raw text available to parse"
        
        try:
            logger.info(f"Re-parsing syllabus (ID: {syllabus_id})...")
            
            parsed_data = await self.parser_agent.parse_syllabus(syllabus.raw_text)
            
            # Update database
            syllabus.course_name = parsed_data.course_name
            syllabus.course_code = parsed_data.course_code
            syllabus.instructor = parsed_data.instructor
            syllabus.parsed_data = parsed_data.model_dump()
            syllabus.is_processed = True
            syllabus.processing_error = None
            
            db.commit()
            db.refresh(syllabus)
            
            logger.info(f"✅ Re-parsing successful (ID: {syllabus_id})")
            
            return syllabus, None
        
        except Exception as e:
            logger.error(f"Re-parsing failed: {e}")
            
            syllabus.processing_error = str(e)
            db.commit()
            
            return syllabus, f"Re-parsing failed: {str(e)}"


# =============================================================================
# GLOBAL SERVICE INSTANCE
# =============================================================================
_service: Optional[SyllabusService] = None


def get_syllabus_service() -> SyllabusService:
    """
    Get the global syllabus service instance.
    
    USAGE:
    from app.services.syllabus_service import get_syllabus_service
    
    service = get_syllabus_service()
    syllabus, error = await service.upload_and_parse(...)
    """
    global _service
    if _service is None:
        _service = SyllabusService()
    return _service


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    print("""
    SYLLABUS SERVICE USAGE:
    
    1. Upload and parse:
        service = get_syllabus_service()
        with open("syllabus.pdf", "rb") as f:
            syllabus, error = await service.upload_and_parse(
                db, user_id=1, file_content=f.read(), filename="syllabus.pdf"
            )
        
        if error:
            print(f"Error: {error}")
        else:
            print(f"Success! Course: {syllabus.course_name}")
    
    2. Get user's syllabi:
        syllabi = service.get_user_syllabi(db, user_id=1)
        for s in syllabi:
            print(f"{s.course_name} - {s.filename}")
    
    3. Delete syllabus:
        success, error = service.delete_syllabus(db, syllabus_id=1, user_id=1)
    """)