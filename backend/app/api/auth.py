"""
Authentication API Routes
-------------------------
HTTP endpoints for user authentication.

ENDPOINTS:
- POST /auth/signup       - Create new account
- POST /auth/login        - Login and get tokens
- POST /auth/refresh      - Refresh access token
- GET  /auth/me           - Get current user profile
- PUT  /auth/me           - Update profile
- POST /auth/change-password - Change password
- POST /auth/logout       - Logout (future: token blacklist)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.models.user import (
    UserSignup, UserLogin, Token, TokenRefresh,
    UserResponse, UserUpdate, PasswordChange, MessageResponse
)
from app.services.auth_service import (
    create_user, authenticate_user, generate_tokens,
    update_user_profile, change_password
)
from app.utils.auth import get_current_active_user, verify_refresh_token_dependency
from app.utils.security import create_access_token

# Create router
router = APIRouter()


# =============================================================================
# SIGNUP ENDPOINT
# =============================================================================

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserSignup,
    db: Session = Depends(get_db)
):
    """
    Create a new user account.
    
    REQUEST:
    ```json
    {
        "email": "student@university.edu",
        "password": "SecurePassword123",
        "full_name": "Jane Doe",
        "semester": "Fall 2024",
        "major": "Computer Science"
    }
    ```
    
    RESPONSE (201 Created):
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    ```
    
    ERRORS:
    - 400: Email already registered, weak password
    """
    # Create user
    user, error = create_user(db, user_data)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Generate tokens
    tokens = generate_tokens(user)
    
    return tokens


# =============================================================================
# LOGIN ENDPOINT
# =============================================================================

@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    
    REQUEST:
    ```json
    {
        "email": "student@university.edu",
        "password": "SecurePassword123"
    }
    ```
    
    RESPONSE:
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    ```
    
    ERRORS:
    - 401: Invalid credentials
    - 403: Account deactivated
    """
    # Authenticate user
    user, error = authenticate_user(db, login_data)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Generate tokens
    tokens = generate_tokens(user)
    
    return tokens


# =============================================================================
# REFRESH TOKEN ENDPOINT
# =============================================================================

@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Get a new access token using refresh token.
    
    REQUEST:
    ```json
    {
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    
    RESPONSE:
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  # NEW
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  # SAME
        "token_type": "bearer"
    }
    ```
    
    WHY THIS EXISTS:
    - Access tokens expire after 30 minutes (security)
    - Instead of forcing user to login again, they use refresh token
    - Refresh tokens last 7 days
    
    ERRORS:
    - 401: Invalid or expired refresh token
    """
    from app.utils.security import verify_refresh_token
    from app.services.auth_service import get_user_by_id
    
    # Verify refresh token
    payload = verify_refresh_token(token_data.refresh_token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    user_id = int(payload.get("sub"))
    user = get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Generate new access token (keep same refresh token)
    new_access_token = create_access_token({
        "sub": str(user.id),
        "email": user.email
    })
    
    return {
        "access_token": new_access_token,
        "refresh_token": token_data.refresh_token,  # Return same refresh token
        "token_type": "bearer"
    }


# =============================================================================
# GET CURRENT USER PROFILE
# =============================================================================

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's profile.
    
    REQUIRES: Authorization: Bearer <access_token>
    
    RESPONSE:
    ```json
    {
        "id": 1,
        "email": "student@university.edu",
        "full_name": "Jane Doe",
        "semester": "Fall 2024",
        "major": "Computer Science",
        "is_active": true,
        "is_verified": false,
        "created_at": "2024-10-01T12:00:00Z",
        "preferences": {}
    }
    ```
    
    ERRORS:
    - 401: Invalid or missing token
    """
    return current_user


# =============================================================================
# UPDATE USER PROFILE
# =============================================================================

@router.put("/me", response_model=UserResponse)
async def update_me(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    
    REQUIRES: Authorization: Bearer <access_token>
    
    REQUEST:
    ```json
    {
        "full_name": "Jane Smith",
        "semester": "Spring 2025",
        "preferences": {"study_hours_per_day": 3}
    }
    ```
    
    RESPONSE: Updated user profile
    
    ERRORS:
    - 401: Invalid or missing token
    - 400: Update failed
    """
    # Convert Pydantic model to dict, exclude None values
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Update user
    user, error = update_user_profile(db, current_user.id, update_dict)
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return user


# =============================================================================
# CHANGE PASSWORD
# =============================================================================

@router.post("/change-password", response_model=MessageResponse)
async def change_user_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    
    REQUIRES: Authorization: Bearer <access_token>
    
    REQUEST:
    ```json
    {
        "current_password": "OldPassword123",
        "new_password": "NewSecurePassword456"
    }
    ```
    
    RESPONSE:
    ```json
    {
        "message": "Password changed successfully"
    }
    ```
    
    ERRORS:
    - 401: Invalid or missing token
    - 400: Current password incorrect, new password weak
    """
    success, error = change_password(
        db,
        current_user.id,
        password_data.current_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {"message": "Password changed successfully"}


# =============================================================================
# LOGOUT (Placeholder)
# =============================================================================

@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout current user.
    
    NOTE: JWT tokens are stateless, so we can't "revoke" them.
    
    FUTURE IMPLEMENTATION:
    - Add token to blacklist (Redis)
    - Client should delete the token
    
    REQUIRES: Authorization: Bearer <access_token>
    
    RESPONSE:
    ```json
    {
        "message": "Logged out successfully"
    }
    ```
    """
    # TODO: Add token to blacklist
    # For now, just return success (client should delete token)
    
    return {"message": "Logged out successfully"}


# =============================================================================
# HEALTH CHECK FOR AUTH
# =============================================================================

@router.get("/health")
async def auth_health():
    """
    Health check for auth endpoints.
    
    RESPONSE:
    ```json
    {
        "status": "healthy",
        "service": "authentication"
    }
    ```
    """
    return {
        "status": "healthy",
        "service": "authentication"
    }