"""
Authentication Service
----------------------
Business logic for user authentication (signup, login, etc.)

WHY SEPARATE SERVICES?
- Routes handle HTTP (requests/responses)
- Services handle business logic (database operations)
- This makes code reusable and testable
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Tuple
from datetime import datetime

from app.db.models import User
from app.models.user import UserSignup, UserLogin
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    validate_password_strength
)


# =============================================================================
# USER SIGNUP
# =============================================================================

def create_user(db: Session, user_data: UserSignup) -> Tuple[Optional[User], Optional[str]]:
    """
    Create a new user account.
    
    STEPS:
    1. Validate password strength
    2. Check if email already exists
    3. Hash the password
    4. Create user in database
    5. Return the user
    
    RETURNS:
    (user, error_message)
    - If successful: (User object, None)
    - If failed: (None, "Error message")
    
    USAGE:
    user, error = create_user(db, signup_data)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return user
    """
    
    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        return None, error_msg
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        return None, "Email already registered"
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    try:
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            semester=user_data.semester,
            major=user_data.major,
            is_active=True,
            is_verified=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user, None
    
    except IntegrityError:
        db.rollback()
        return None, "Email already registered"
    except Exception as e:
        db.rollback()
        return None, f"Failed to create user: {str(e)}"


# =============================================================================
# USER LOGIN
# =============================================================================

def authenticate_user(db: Session, login_data: UserLogin) -> Tuple[Optional[User], Optional[str]]:
    """
    Authenticate a user (verify credentials).
    
    STEPS:
    1. Find user by email
    2. Verify password
    3. Update last_login timestamp
    4. Return user
    
    RETURNS:
    (user, error_message)
    - If successful: (User object, None)
    - If failed: (None, "Error message")
    
    USAGE:
    user, error = authenticate_user(db, login_data)
    if error:
        raise HTTPException(status_code=401, detail=error)
    # Generate tokens
    """
    
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        return None, "Invalid email or password"
    
    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        return None, "Invalid email or password"
    
    # Check if user is active
    if not user.is_active:
        return None, "Account is deactivated"
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user, None


# =============================================================================
# TOKEN GENERATION
# =============================================================================

def generate_tokens(user: User) -> dict:
    """
    Generate access and refresh tokens for a user.
    
    RETURNS:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    
    USAGE:
    user, error = authenticate_user(db, login_data)
    tokens = generate_tokens(user)
    return tokens
    """
    
    token_data = {
        "sub": str(user.id),
        "email": user.email
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# =============================================================================
# USER RETRIEVAL
# =============================================================================

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Get a user by ID.
    
    USAGE:
    user = get_user_by_id(db, 123)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get a user by email.
    
    USAGE:
    user = get_user_by_email(db, "test@example.com")
    """
    return db.query(User).filter(User.email == email).first()


# =============================================================================
# USER UPDATE
# =============================================================================

def update_user_profile(db: Session, user_id: int, update_data: dict) -> Tuple[Optional[User], Optional[str]]:
    """
    Update user profile.
    
    ARGS:
    - user_id: ID of user to update
    - update_data: Dictionary of fields to update
    
    RETURNS:
    (user, error_message)
    
    USAGE:
    user, error = update_user_profile(db, 123, {"full_name": "New Name"})
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return None, "User not found"
    
    # Update fields
    for field, value in update_data.items():
        if value is not None and hasattr(user, field):
            setattr(user, field, value)
    
    try:
        db.commit()
        db.refresh(user)
        return user, None
    except Exception as e:
        db.rollback()
        return None, f"Failed to update user: {str(e)}"


def change_password(db: Session, user_id: int, current_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
    """
    Change user password.
    
    STEPS:
    1. Get user
    2. Verify current password
    3. Validate new password
    4. Hash and update
    
    RETURNS:
    (success, error_message)
    
    USAGE:
    success, error = change_password(db, 123, "OldPass123", "NewPass456")
    if not success:
        raise HTTPException(status_code=400, detail=error)
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return False, "User not found"
    
    # Verify current password
    if not verify_password(current_password, user.hashed_password):
        return False, "Current password is incorrect"
    
    # Validate new password
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        return False, error_msg
    
    # Hash and update
    user.hashed_password = hash_password(new_password)
    
    try:
        db.commit()
        return True, None
    except Exception as e:
        db.rollback()
        return False, f"Failed to change password: {str(e)}"


# =============================================================================
# USER DEACTIVATION
# =============================================================================

def deactivate_user(db: Session, user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Deactivate a user account.
    
    NOTE: This doesn't delete the user, just sets is_active=False
    """
    user = get_user_by_id(db, user_id)
    
    if not user:
        return False, "User not found"
    
    user.is_active = False
    
    try:
        db.commit()
        return True, None
    except Exception as e:
        db.rollback()
        return False, f"Failed to deactivate user: {str(e)}"


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    print("""
    AUTH SERVICE USAGE:
    
    1. Signup:
        user, error = create_user(db, signup_data)
        if error:
            return {"error": error}
        tokens = generate_tokens(user)
        return tokens
    
    2. Login:
        user, error = authenticate_user(db, login_data)
        if error:
            return {"error": error}
        tokens = generate_tokens(user)
        return tokens
    
    3. Update Profile:
        user, error = update_user_profile(db, user_id, {"full_name": "New Name"})
    
    4. Change Password:
        success, error = change_password(db, user_id, "old", "new")
    """)