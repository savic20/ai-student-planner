"""
Database Connection & Session Management
-----------------------------------------
Sets up SQLAlchemy engine, session, and base class for all models.

EXPLANATION FOR BEGINNERS:
- Engine = the "connection pool" to PostgreSQL
- SessionLocal = a "conversation" with the database
- Base = parent class for all database tables
- get_db() = FastAPI dependency that gives you a database session

IMPORTANT CONCEPTS:
1. Sessions are like transactions - they track changes
2. Always close sessions when done (we use context managers)
3. Base.metadata contains info about all your tables
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# DATABASE ENGINE
# =============================================================================
# This is the "connection pool" to PostgreSQL
# pool_pre_ping=True checks if connection is alive before using it
# echo=True shows SQL queries in logs (turn off in production)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Check connections before using
    echo=False,  # Set to True to see SQL queries in logs
    pool_size=5,  # Number of connections to keep open
    max_overflow=10,  # Additional connections if pool is full
)

# =============================================================================
# SESSION FACTORY
# =============================================================================
# This creates new database sessions (conversations with DB)
# autocommit=False: Changes aren't saved until you call commit()
# autoflush=False: Changes aren't sent to DB until you commit()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =============================================================================
# BASE CLASS FOR MODELS
# =============================================================================
# All database models inherit from this
# It tracks metadata about tables (columns, relationships, etc.)

Base = declarative_base()


# =============================================================================
# DEPENDENCY FOR FASTAPI ROUTES
# =============================================================================
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    
    HOW THIS WORKS:
    1. Creates a new session
    2. Yields it to the route (gives it to you)
    3. Automatically closes it when done (even if there's an error)
    
    USAGE IN ROUTES:
    @app.get("/users")
    def get_users(db: Session = Depends(get_db)):
        users = db.query(User).all()
        return users
    """
    db = SessionLocal()
    try:
        yield db  # This is where your route uses the session
    finally:
        db.close()  # Always close, even if there's an error


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================
def init_db():
    """
    Create all tables in the database.
    
    WHEN TO USE:
    - First time setup
    - Testing (create fresh tables)
    
    PRODUCTION NOTE:
    In production, use Alembic migrations instead of this.
    This is mainly for development.
    """
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def drop_db():
    """
    Drop all tables (DELETE EVERYTHING!).
    
    WARNING: This deletes ALL data!
    Only use in development for testing.
    """
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Database tables dropped")


# =============================================================================
# DATABASE HEALTH CHECK
# =============================================================================
def check_db_connection() -> bool:
    """
    Test if database connection is working.
    
    RETURNS:
    True if connection successful, False otherwise
    """
    try:
        # Try to execute a simple query
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    if check_db_connection():
        print("Connected to database!")
    else:
        print("Failed to connect to database")
    
    # Example: Create a session manually
    db = SessionLocal()
    try:
        result = db.execute("SELECT version();")
        version = result.fetchone()[0]
        print(f"PostgreSQL version: {version}")
    finally:
        db.close()