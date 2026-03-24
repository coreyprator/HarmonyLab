"""
Improvisation API Routes (HL-IMPROV-001)
AI jazz improvisation generation with RLHF feedback loop.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.db.connection import DatabaseConnection, get_db
from app.services.improvisation_service import ImprovisationService
import logging

router = APIRouter(prefix="/api/v1/songs", tags=["improvisation"])
logger = logging.getLogger(__name__)


class RateRiffRequest(BaseModel):
    rating: int  # -1, 0, or 1


@router.post("/{song_id}/improvise")
async def generate_improvisation(song_id: int, iteration: Optional[int] = 1, db: DatabaseConnection = Depends(get_db)):
    """Generate AI jazz improvisation over a song's chord progression."""
    try:
        service = ImprovisationService(db)
        session = service.generate_improvisation(song_id, iteration)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Improvisation generation failed for song {song_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Improvisation generation failed: {str(e)}")


@router.get("/{song_id}/improvisations")
async def get_improvisations(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """Get all improvisation sessions for a song."""
    service = ImprovisationService(db)
    return service.get_sessions_for_song(song_id)


@router.get("/{song_id}/improvisations/{session_id}")
async def get_improvisation_session(song_id: int, session_id: int, db: DatabaseConnection = Depends(get_db)):
    """Get a specific improvisation session."""
    try:
        service = ImprovisationService(db)
        session = service.get_session(session_id)
        if session["song_id"] != song_id:
            raise HTTPException(status_code=404, detail="Session not found for this song")
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/improvisations/riffs/{riff_id}/rate")
async def rate_riff(riff_id: int, body: RateRiffRequest, db: DatabaseConnection = Depends(get_db)):
    """Rate an improvisation riff: -1 (dislike), 0 (neutral), 1 (like)."""
    try:
        service = ImprovisationService(db)
        result = service.rate_riff(riff_id, body.rating)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
