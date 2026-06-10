"""
Harmony Lab FastAPI Application

Main entry point for the Harmony Lab API server.
"""
import logging
import os
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from config.settings import settings

# Import routes
from app.api.routes import songs, sections, vocabulary, measures, chords, progress, quiz, imports, analysis, exports, midi_input, riffs, improvisation, rules, preferences
from app.api.routes.sections import sections_router

logger = logging.getLogger(__name__)

VERSION = "2.49.0"  # HM44 Phase B: single-service convergence, redesign UI served from FastAPI

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
        "https://harmonylab-redesign-57478301787.us-central1.run.app",
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


# HM44 Phase B (B2): Serve the redesign React app at /
# API routes registered below take precedence via FastAPI route ordering.
@app.get("/")
async def serve_app_root():
    """Serve redesign prototype (new UI) at root — single-service, no nginx proxy."""
    return FileResponse("frontend-redesign/prototype.html")


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
        "version": VERSION,
        "canary": "PINEAPPLE-HM44"
    }


# Include routers
app.include_router(songs.router)
app.include_router(sections.router)
app.include_router(sections_router)   # HM44 A7: DELETE /api/v1/sections/{id}
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
app.include_router(rules.router)
app.include_router(preferences.router)

# HM43 Phase 2: Serve redesign prototype at root / (redesign/hm44 branch only)
app.mount("/", StaticFiles(directory="frontend-redesign", html=True), name="redesign")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
