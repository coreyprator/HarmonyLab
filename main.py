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
    version="1.0.0",
    debug=settings.debug,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Harmony Lab API",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.environment,
    }


@app.get("/health")
async def health_check():
    """Detailed health check including database connectivity."""
    # TODO: Add database connection check
    return {
        "status": "healthy",
        "database": "not_checked",
        "environment": settings.environment,
    }


# Include routers
app.include_router(songs.router, tags=["songs"])
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
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
