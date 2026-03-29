"""
Harmony Lab FastAPI Application

Main entry point for the Harmony Lab API server.
"""
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from config.settings import settings

# Import routes
from app.api.routes import songs, sections, vocabulary, measures, chords, progress, quiz, imports, analysis, auth, exports, midi_input, riffs, improvisation

logger = logging.getLogger(__name__)

VERSION = "2.28.0"  # HM22: Fix exchange persistence + key center update + manual key edit

app = FastAPI(
    title="Harmony Lab API",
    description="Harmonic progression training system for musicians",
    version=VERSION,
    debug=settings.debug,
)

# Standard C: Global exception handler — catches unhandled exceptions, returns structured JSON
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_detail = str(exc)
    traceback_str = traceback.format_exc()
    logger.error(f"Unhandled exception on {request.method} {request.url}: {error_detail}\n{traceback_str}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": error_detail,
            "path": str(request.url.path)
        }
    )

# Proxy headers middleware — trust X-Forwarded-Proto from Cloud Run load balancer
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# CORS middleware
# Note: allow_origins=["*"] is INVALID with allow_credentials=True (browsers reject it).
# Must list explicit origins when credentials are enabled.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://harmonylab.rentyourcio.com",
        "https://harmonylab-frontend-wmrla7fhwa-uc.a.run.app",
        "http://localhost:8080",
        "http://localhost:3000",
    ],
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
        "component": "backend",
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
app.include_router(exports.router)
app.include_router(midi_input.router)
app.include_router(riffs.router)
app.include_router(improvisation.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
