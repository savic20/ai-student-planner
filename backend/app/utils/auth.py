"""
Authentication Dependencies
---------------------------
FastAPI dependencies for protecting routes with authentication.

EXPLANATION:
In FastAPI, a "dependency" is a function that runs before your route.
It can validate tokens, get the current user, etc.

USAGE IN ROUTES:
@app.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.email}"}

If token is invalid, FastAPI automatically returns 401 Unauthorized.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.db.models import User
from app.utils.security import verify_access_token, decode_token
from app.models.user import TokenData

# =============================================================================
# HTTP BEARER TOKEN SCHEME
# =============================================================================
# This tells FastAPI to look for: Authorization: Bearer <token>
security = HTTPBearer()


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

inactive_user_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="User account is inactive",
)


# =============================================================================
# DEPENDENCY: GET CURRENT USER FROM TOKEN
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Verify JWT token and return the current user.
    
    HOW THIS WORKS:
    1. FastAPI extracts token from: Authorization: Bearer <token>
    2. We decode and verify the token
    3. We get the user_id from the token
    4. We fetch the user from the database
    5. We return the user to the route
    
    IF ANY STEP FAILS:
    - Raises 401 Unauthorized
    - Route is never called
    
    USAGE:
    @app.get("/me")
    def get_me(user: User = Depends(get_current_user)):
        return {"email": user.email}
    """
    token = credentials.credentials
    
    # Verify token and extract payload
    payload = verify_access_token(token)
    if payload is None:
        raise credentials_exception
    
    # Get user_id from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Fetch user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify user is active (not banned/deactivated).
    
    USAGE:
    @app.get("/active-only")
    def route(user: User = Depends(get_current_active_user)):
        # Only active users can access this
    """
    if not current_user.is_active:
        raise inactive_user_exception
    
    return current_user


# =============================================================================
# DEPENDENCY: OPTIONAL AUTHENTICATION
# =============================================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    
    USE CASE:
    Routes that work for both logged-in and guest users.
    
    EXAMPLE:
    @app.get("/public-content")
    def route(user: Optional[User] = Depends(get_current_user_optional)):
        if user:
            return {"message": f"Hello {user.email}"}
        else:
            return {"message": "Hello guest"}
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = verify_access_token(token)
    
    if payload is None:
        return None
    
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    return user


# =============================================================================
# DEPENDENCY: ADMIN ONLY (Future Use)
# =============================================================================

async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user to be an admin.
    
    NOTE: We don't have an is_admin field yet.
    This is a placeholder for future admin functionality.
    
    USAGE:
    @app.delete("/users/{user_id}")
    def delete_user(admin: User = Depends(require_admin)):
        # Only admins can delete users
    """
    # TODO: Add is_admin field to User model
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    return current_user


# =============================================================================
# UTILITY: VERIFY REFRESH TOKEN
# =============================================================================

def verify_refresh_token_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Verify a refresh token and extract data.
    
    USAGE:
    @app.post("/auth/refresh")
    def refresh(token_data: TokenData = Depends(verify_refresh_token_dependency)):
        # Create new access token
    """
    from app.utils.security import verify_refresh_token
    
    token = credentials.credentials
    payload = verify_refresh_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    email = payload.get("email")
    
    return TokenData(user_id=int(user_id) if user_id else None, email=email)


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    print("""
    USAGE EXAMPLES:
    
    1. Protected Route (requires authentication):
    
        @app.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            return {"email": user.email}
    
    2. Active Users Only:
    
        @app.get("/active-only")
        def route(user: User = Depends(get_current_active_user)):
            return {"message": "You are active"}
    
    3. Optional Authentication:
    
        @app.get("/public")
        def route(user: Optional[User] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello guest"}
    
    4. Admin Only:
    
        @app.delete("/admin/delete")
        def delete(admin: User = Depends(require_admin)):
            return {"message": "Admin action"}
    """)