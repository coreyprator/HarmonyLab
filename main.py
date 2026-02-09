"""
Harmony Lab FastAPI Application

Main entry point for the Harmony Lab API server.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from config.settings import settings

# Import routes
from app.api.routes import songs, sections, vocabulary, measures, chords, progress, quiz, imports, analysis, auth

logger = logging.getLogger(__name__)

VERSION = "1.5.4"

app = FastAPI(
    title="Harmony Lab API",
    description="Harmonic progression training system for musicians",
    version=VERSION,
    debug=settings.debug,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (required for OAuth state storage)
# same_site="none" required for OAuth redirect flow from Google
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret_key,
    same_site="none",
    https_only=True,
)


@app.on_event("startup")
async def startup_event():
    """Run migrations on startup."""
    try:
        from app.migrations import run_migrations
        run_migrations()
    except Exception as e:
        logger.warning(f"Migration warning (non-fatal): {e}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Harmony Lab API",
        "version": VERSION,
        "status": "healthy",
        "environment": settings.environment,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    from app.db.connection import db

    try:
        db_ok = db.test_connection()
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "service": "harmonylab",
        "version": VERSION
    }


# Include routers
app.include_router(auth.router)  # Auth first for login/logout
app.include_router(songs.router)
app.include_router(sections.router)
app.include_router(vocabulary.router)
app.include_router(measures.router)
app.include_router(chords.router)
app.include_router(progress.router)
app.include_router(quiz.router)
app.include_router(imports.router)
app.include_router(analysis.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
