"""
FastAPI Application Entry Point
--------------------------------
This is the heart of the backend API.

WHAT THIS FILE DOES:
1. Creates the FastAPI app instance
2. Sets up middleware (CORS, logging, etc.)
3. Registers all API routes
4. Provides health check endpoint

EXPLANATION FOR BEGINNERS:
- FastAPI is like a smart router that receives HTTP requests
- Middleware = code that runs before/after every request
- CORS = allows frontend (different port) to talk to backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings

# Import API routes
from app.api import auth, syllabus, plans, feedback
from app.db.database import engine, Base, check_db_connection


# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# LIFESPAN EVENTS (Startup / Shutdown)
# ============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code that runs when the app starts and stops.
    
    WHAT THIS DOES:
    - Startup: Initialize database, check LLM connections
    - Shutdown: Close connections gracefully
    """
    # STARTUP
    logger.info("🚀 Starting Student Planner API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1]}")  # Hide password
    
    # Check database connection
    if not check_db_connection():
        logger.error("❌ Failed to connect to database!")
        raise Exception("Database connection failed")
    
    logger.info("✅ Application started successfully")
    
    yield  # Application runs here
    
    # SHUTDOWN
    logger.info("👋 Shutting down Student Planner API...")
    # TODO: Close database connections
    logger.info("✅ Shutdown complete")


# ============================================================================
# CREATE FASTAPI APP
# ============================================================================
app = FastAPI(
    title="Student Planner API",
    description="Multi-agent AI study planning system",
    version="0.1.0",
    docs_url="/docs",          # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",        # ReDoc at http://localhost:8000/redoc
    lifespan=lifespan
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Middleware (allows frontend to call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# TODO: Add request logging middleware
# TODO: Add rate limiting middleware


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring.
    
    WHAT THIS DOES:
    - Docker uses this to check if the app is running
    - Load balancers use this to know if the server is healthy
    - You can call this to test if the API is up
    
    TEST IT:
    curl http://localhost:8000/health
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": "0.1.0"
        }
    )


# ============================================================================
# ROOT ENDPOINT
# ============================================================================
@app.get("/", tags=["Root"])
async def root():
    """
    API root endpoint with welcome message.
    """
    return {
        "message": "Welcome to Student Planner API",
        "docs": "/docs",
        "health": "/health",
        "version": "0.1.0"
    }


# ============================================================================
# REGISTER ROUTES
# ============================================================================
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(syllabus.router, prefix="/syllabus", tags=["Syllabus"])
app.include_router(plans.router, prefix="/plans", tags=["Plans"])
app.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
# app.include_router(chat.router, prefix="/chat", tags=["Chat"])
# app.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])


# ============================================================================
# ERROR HANDLERS
# ============================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Catch all unhandled exceptions.
    
    WHY THIS IS IMPORTANT:
    - Prevents the app from crashing
    - Returns a user-friendly error message
    - Logs the error for debugging
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Something went wrong. Please try again later.",
            # In production, DON'T expose error details to users
            "detail": str(exc) if not settings.is_production else None
        }
    )


# ============================================================================
# RUN APPLICATION (for development)
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.BACKEND_RELOAD,  # Auto-reload on code changes
        log_level=settings.LOG_LEVEL.lower()
    )