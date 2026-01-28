"""
Harmony Lab FastAPI Application

Main entry point for the Harmony Lab API server.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings

# Import routes
from app.api.routes import songs, sections, vocabulary, measures, chords, progress, quiz, imports


app = FastAPI(
    title="Harmony Lab API",
    description="Harmonic progression training system for musicians",
    version="1.2.1",
    debug=settings.debug,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Harmony Lab API",
        "version": "1.1.0",
        "build": "2026-01-28-chord-editing",
        "status": "healthy",
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
        "version": "1.2.1",
        "build": "2026-01-28-keyerror-fix"
    }



# Include routers
app.include_router(songs.router, prefix="/api/songs", tags=["songs"])
app.include_router(sections.router, tags=["sections"])
app.include_router(vocabulary.router, tags=["vocabulary"])
app.include_router(measures.router, tags=["measures"])
app.include_router(chords.router, tags=["chords"])
app.include_router(progress.router, tags=["progress"])
app.include_router(quiz.router, tags=["quiz"])
app.include_router(imports.router, tags=["imports"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
