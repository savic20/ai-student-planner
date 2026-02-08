"""
User Pydantic Models
--------------------
API request and response schemas for user-related endpoints.

EXPLANATION:
- These are NOT database models
- They define the structure of API requests/responses
- FastAPI uses these for automatic validation and documentation

DIFFERENCE:
- Database Model (ORM): Represents a table in PostgreSQL
- Pydantic Model: Represents JSON data in API requests/responses
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


# =============================================================================
# USER AUTHENTICATION SCHEMAS
# =============================================================================

class UserSignup(BaseModel):
    """
    Request body for user signup.
    
    WHAT THE USER SENDS:
    {
        "email": "student@university.edu",
        "password": "SecurePassword123",
        "full_name": "Jane Doe",
        "semester": "Fall 2024",
        "major": "Computer Science"
    }
    """
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=72, description="Password (8-72 characters)")
    full_name: Optional[str] = Field(None, description="User's full name")
    semester: Optional[str] = Field(None, description="Current semester (e.g., 'Fall 2024')")
    major: Optional[str] = Field(None, description="Major/field of study")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "student@university.edu",
                "password": "SecurePassword123",
                "full_name": "Jane Doe",
                "semester": "Fall 2024",
                "major": "Computer Science"
            }
        }


class UserLogin(BaseModel):
    """
    Request body for user login.
    
    WHAT THE USER SENDS:
    {
        "email": "student@university.edu",
        "password": "SecurePassword123"
    }
    """
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "student@university.edu",
                "password": "SecurePassword123"
            }
        }


class Token(BaseModel):
    """
    Response after successful login.
    
    WHAT WE SEND BACK:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    
    THE USER THEN USES THIS IN REQUESTS:
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    access_token: str = Field(..., description="JWT access token (short-lived)")
    refresh_token: str = Field(..., description="JWT refresh token (long-lived)")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")


class TokenRefresh(BaseModel):
    """
    Request body for refreshing access token.
    
    WHAT THE USER SENDS:
    {
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    """
    refresh_token: str = Field(..., description="Valid refresh token")


class TokenData(BaseModel):
    """
    Data extracted from a JWT token.
    
    This is used internally, not sent in API requests.
    """
    user_id: Optional[int] = None
    email: Optional[str] = None


# =============================================================================
# USER PROFILE SCHEMAS
# =============================================================================

class UserBase(BaseModel):
    """
    Base user data (shared fields).
    """
    email: EmailStr
    full_name: Optional[str] = None
    semester: Optional[str] = None
    major: Optional[str] = None


class UserResponse(UserBase):
    """
    Response when returning user data.
    
    WHAT WE SEND BACK:
    {
        "id": 1,
        "email": "student@university.edu",
        "full_name": "Jane Doe",
        "semester": "Fall 2024",
        "major": "Computer Science",
        "is_active": true,
        "is_verified": false,
        "created_at": "2024-10-01T12:00:00Z",
        "preferences": {"study_hours_per_day": 3}
    }
    
    NOTE: We do NOT return the hashed_password (security!)
    """
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    preferences: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True  # Allows conversion from ORM model


class UserUpdate(BaseModel):
    """
    Request body for updating user profile.
    
    All fields are optional (partial update).
    
    WHAT THE USER SENDS:
    {
        "full_name": "Jane Smith",  # Changed name
        "semester": "Spring 2025"    # Updated semester
    }
    """
    full_name: Optional[str] = None
    semester: Optional[str] = None
    major: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class PasswordChange(BaseModel):
    """
    Request body for changing password.
    
    WHAT THE USER SENDS:
    {
        "current_password": "OldPassword123",
        "new_password": "NewSecurePassword456"
    }
    """
    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(..., min_length=8, max_length=72, description="New password (8-72 characters)")


# =============================================================================
# MESSAGE SCHEMAS
# =============================================================================

class MessageResponse(BaseModel):
    """
    Generic response message.
    
    USAGE:
    return MessageResponse(message="User created successfully")
    
    RESPONSE:
    {
        "message": "User created successfully"
    }
    """
    message: str


class ErrorResponse(BaseModel):
    """
    Error response.
    
    USAGE:
    raise HTTPException(
        status_code=400,
        detail=ErrorResponse(error="Invalid credentials").dict()
    )
    
    RESPONSE:
    {
        "error": "Invalid credentials",
        "detail": "Email or password is incorrect"
    }
    """
    error: str
    detail: Optional[str] = None


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    # Example: Validate signup data
    signup_data = {
        "email": "test@example.com",
        "password": "SecurePass123",
        "full_name": "Test User"
    }
    
    try:
        user = UserSignup(**signup_data)
        print("✅ Signup data valid")
        print(user.model_dump_json(indent=2))
    except Exception as e:
        print(f"❌ Validation error: {e}")
    
    # Example: Invalid email
    invalid_data = {
        "email": "not-an-email",
        "password": "short"
    }
    
    try:
        user = UserSignup(**invalid_data)
    except Exception as e:
        print(f"\n❌ Expected validation error: {e}")