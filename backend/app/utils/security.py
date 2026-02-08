"""
Security Utilities
------------------
Password hashing and JWT token management.

EXPLANATION FOR BEGINNERS:
- Password Hashing: One-way encryption. You can't reverse it.
  "mypassword" → "$2b$12$abc...xyz" (60 characters)
  Even if someone steals your database, they can't get passwords.

- JWT Tokens: Signed JSON data that proves identity.
  Structure: header.payload.signature
  Example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# =============================================================================
# PASSWORD HASHING SETUP
# =============================================================================
# bcrypt is a secure hashing algorithm specifically designed for passwords
# It's SLOW on purpose to prevent brute-force attacks
# truncate_error=False allows passwords longer than 72 bytes (they get truncated)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False  # Allow truncation without error
)


def hash_password(password: str) -> str:
    """
    Hash a plain text password.
    
    WHAT THIS DOES:
    "mypassword123" → "$2b$12$KIXxKj8N.jJc5U7p3RQNxOP8p8YhqV..."
    
    WHY IT'S SECURE:
    - Uses bcrypt algorithm (slow by design)
    - Automatically adds "salt" (random data)
    - Same password creates different hashes each time
    
    BCRYPT LIMITATION:
    - Max password length is 72 bytes
    - Passlib automatically truncates longer passwords
    
    USAGE:
    hashed = hash_password("user_input_password")
    user.hashed_password = hashed
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash.
    
    WHAT THIS DOES:
    verify_password("mypassword123", "$2b$12$KIX...") → True
    verify_password("wrongpassword", "$2b$12$KIX...") → False
    
    USAGE (Login):
    user = get_user_by_email(email)
    if verify_password(input_password, user.hashed_password):
        # Password correct, log them in
    """
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT TOKEN GENERATION
# =============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    WHAT THIS DOES:
    Takes user data (like user_id) and creates a signed token.
    
    TOKEN STRUCTURE:
    {
        "sub": "123",  # User ID (subject)
        "email": "user@example.com",
        "exp": 1234567890  # Expiration timestamp
    }
    
    ARGS:
    - data: Dictionary of data to include in token (usually {"sub": user_id})
    - expires_delta: How long until token expires (default: 30 minutes)
    
    RETURNS:
    A string token like: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    USAGE:
    token = create_access_token({"sub": str(user.id), "email": user.email})
    # Send this token to the user
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Create and sign the token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token (longer-lived).
    
    PURPOSE:
    - Access tokens expire quickly (30 min)
    - Refresh tokens last longer (7 days)
    - User can get a new access token without logging in again
    
    WORKFLOW:
    1. Login → Get access_token + refresh_token
    2. Access token expires after 30 min
    3. Send refresh_token to /auth/refresh
    4. Get new access_token
    
    USAGE:
    refresh = create_refresh_token({"sub": str(user.id)})
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    
    WHAT THIS DOES:
    Takes a token string and extracts the data inside.
    Also verifies:
    - Token signature is valid (not tampered with)
    - Token hasn't expired
    
    RETURNS:
    - Dictionary of token data if valid
    - None if invalid or expired
    
    USAGE:
    payload = decode_token(token)
    if payload:
        user_id = payload.get("sub")
        # Token is valid, use user_id
    else:
        # Token invalid, deny access
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# =============================================================================
# TOKEN VALIDATION
# =============================================================================

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify an access token and return its payload.
    
    This is a wrapper around decode_token with additional checks.
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # Check if it's an access token (not refresh)
    if payload.get("type") == "refresh":
        return None  # Refresh tokens can't be used for access
    
    return payload


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a refresh token and return its payload.
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # Check if it's a refresh token
    if payload.get("type") != "refresh":
        return None  # Access tokens can't be used to refresh
    
    return payload


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Check if password meets security requirements.
    
    REQUIREMENTS:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - Max 72 characters (bcrypt limitation)
    
    RETURNS:
    (is_valid, error_message)
    
    USAGE:
    valid, error = validate_password_strength("abc123")
    if not valid:
        return {"error": error}
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 72:
        return False, "Password must be at most 72 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    return True, ""


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    # Example: Hash a password
    plain_password = "MySecurePassword123"
    hashed = hash_password(plain_password)
    print(f"Original: {plain_password}")
    print(f"Hashed:   {hashed}")
    
    # Example: Verify password
    is_correct = verify_password(plain_password, hashed)
    print(f"Verification: {is_correct}")
    
    # Example: Create token
    token_data = {"sub": "123", "email": "test@example.com"}
    access_token = create_access_token(token_data)
    print(f"\nAccess Token: {access_token[:50]}...")
    
    # Example: Decode token
    payload = decode_token(access_token)
    print(f"Decoded: {payload}")
    
    # Example: Validate password
    valid, error = validate_password_strength("weak")
    print(f"\nPassword validation: {valid}, Error: {error}")