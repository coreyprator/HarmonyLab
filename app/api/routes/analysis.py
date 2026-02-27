"""
Analysis API Routes
Harmonic analysis, chord overrides, and key region management.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
from app.services.analysis_service import analyze_song, HarmonicAnalyzer
from app.db.connection import DatabaseConnection, get_db
import json
import logging

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)


class AnalysisRequest(BaseModel):
    key_override: Optional[str] = None


class ChordOverrideRequest(BaseModel):
    roman: Optional[str] = None
    function: Optional[str] = None
    key_context: Optional[str] = None
    is_pivot: bool = False
    pivot_to_key: Optional[str] = None
    notes: Optional[str] = None


@router.get("/songs/{song_id}")
async def get_analysis(
    song_id: int,
    refresh: bool = False,
    db: DatabaseConnection = Depends(get_db)
):
    """Get harmonic analysis for a song."""

    # Check cache unless refresh requested
    if not refresh:
        cached = db.execute_query(
            "SELECT analysis_json, manual_key_override FROM SongAnalysis WHERE song_id = ?",
            (song_id,)
        )
        if cached and cached[0].get('analysis_json'):
            result = json.loads(cached[0]['analysis_json'])
            return _apply_overrides(result, song_id, db)

    # Verify song exists
    songs = db.execute_query("SELECT id, original_key FROM Songs WHERE id = ?", (song_id,))
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")

    # Get all chords for this song ordered by section/measure/position
    # Include measure_number and beat_position for granularity context
    chords = db.execute_query("""
        SELECT c.chord_symbol, m.measure_number, c.beat_position, c.chord_order,
               s.name as section_name
        FROM Chords c
        JOIN Measures m ON c.measure_id = m.id
        JOIN Sections s ON m.section_id = s.id
        WHERE s.song_id = ?
        ORDER BY s.section_order, m.measure_number, c.chord_order
    """, (song_id,))

    if not chords:
        raise HTTPException(status_code=404, detail="No chords found for this song")

    chord_symbols = [c['chord_symbol'] for c in chords]
    # Build measure context for each chord
    chord_positions = [
        {"measure": c['measure_number'], "beat": c.get('beat_position', 1.0)}
        for c in chords
    ]

    # Check for manual key override
    key_override = None
    existing = db.execute_query(
        "SELECT manual_key_override FROM SongAnalysis WHERE song_id = ?",
        (song_id,)
    )
    if existing and existing[0].get('manual_key_override'):
        key_override = existing[0]['manual_key_override']

    # Run analysis
    result = analyze_song(chord_symbols, key_override)

    # Enrich with measure/beat positions
    for i, ch in enumerate(result.get('chords', [])):
        if i < len(chord_positions):
            ch['measure'] = chord_positions[i]['measure']
            ch['beat'] = chord_positions[i]['beat']

    # Add total measures count
    measure_count = db.execute_scalar("""
        SELECT COUNT(DISTINCT m.measure_number)
        FROM Measures m
        JOIN Sections s ON m.section_id = s.id
        WHERE s.song_id = ?
    """, (song_id,))
    result['total_measures'] = measure_count or 0

    # Cache result using MERGE (upsert)
    analysis_json = json.dumps(result)
    detected_key = result['detected_key']
    confidence = result['confidence']

    # Check if record exists
    exists = db.execute_scalar(
        "SELECT COUNT(*) FROM SongAnalysis WHERE song_id = ?", (song_id,)
    )

    if exists > 0:
        db.execute_non_query("""
            UPDATE SongAnalysis
            SET analysis_json = ?, detected_key = ?, confidence = ?, updated_at = GETDATE()
            WHERE song_id = ?
        """, (analysis_json, detected_key, confidence, song_id))
    else:
        db.execute_non_query("""
            INSERT INTO SongAnalysis (song_id, analysis_json, detected_key, confidence)
            VALUES (?, ?, ?, ?)
        """, (song_id, analysis_json, detected_key, confidence))

    return _apply_overrides(result, song_id, db)


@router.post("/songs/{song_id}")
async def update_analysis_key(
    song_id: int,
    request: AnalysisRequest,
    db: DatabaseConnection = Depends(get_db)
):
    """Re-analyze with manual key override."""

    # Save key override
    exists = db.execute_scalar(
        "SELECT COUNT(*) FROM SongAnalysis WHERE song_id = ?", (song_id,)
    )

    if exists > 0:
        db.execute_non_query("""
            UPDATE SongAnalysis
            SET manual_key_override = ?, updated_at = GETDATE()
            WHERE song_id = ?
        """, (request.key_override, song_id))
    else:
        db.execute_non_query("""
            INSERT INTO SongAnalysis (song_id, manual_key_override)
            VALUES (?, ?)
        """, (song_id, request.key_override))

    # Refresh analysis
    return await get_analysis(song_id, refresh=True, db=db)


@router.put("/songs/{song_id}/chord/{chord_index}")
async def override_chord(
    song_id: int,
    chord_index: int,
    override: ChordOverrideRequest,
    db: DatabaseConnection = Depends(get_db)
):
    """Override analysis for a specific chord."""

    exists = db.execute_scalar(
        "SELECT COUNT(*) FROM ChordAnalysisOverrides WHERE song_id = ? AND chord_index = ?",
        (song_id, chord_index)
    )

    if exists > 0:
        db.execute_non_query("""
            UPDATE ChordAnalysisOverrides
            SET roman_override = ?, function_override = ?, key_context_override = ?,
                is_pivot_chord = ?, pivot_to_key = ?, notes = ?, updated_at = GETDATE()
            WHERE song_id = ? AND chord_index = ?
        """, (
            override.roman, override.function, override.key_context,
            override.is_pivot, override.pivot_to_key, override.notes,
            song_id, chord_index
        ))
    else:
        db.execute_non_query("""
            INSERT INTO ChordAnalysisOverrides
                (song_id, chord_index, roman_override, function_override,
                 key_context_override, is_pivot_chord, pivot_to_key, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            song_id, chord_index, override.roman, override.function,
            override.key_context, override.is_pivot, override.pivot_to_key,
            override.notes
        ))

    return {"status": "updated", "chord_index": chord_index}


@router.delete("/songs/{song_id}/chord/{chord_index}")
async def delete_chord_override(
    song_id: int,
    chord_index: int,
    db: DatabaseConnection = Depends(get_db)
):
    """Remove override, revert to auto-analysis."""
    db.execute_non_query(
        "DELETE FROM ChordAnalysisOverrides WHERE song_id = ? AND chord_index = ?",
        (song_id, chord_index)
    )
    return {"status": "deleted", "chord_index": chord_index}


@router.get("/songs/{song_id}/overrides")
async def list_overrides(
    song_id: int,
    db: DatabaseConnection = Depends(get_db)
):
    """List all chord overrides for a song."""
    overrides = db.execute_query(
        "SELECT * FROM ChordAnalysisOverrides WHERE song_id = ? ORDER BY chord_index",
        (song_id,)
    )
    return {"overrides": overrides}


def _apply_overrides(result: dict, song_id: int, db: DatabaseConnection) -> dict:
    """Apply user overrides to analysis result."""
    overrides = db.execute_query(
        "SELECT * FROM ChordAnalysisOverrides WHERE song_id = ?",
        (song_id,)
    )

    override_map = {o['chord_index']: o for o in overrides}

    for chord in result.get('chords', []):
        idx = chord['index']
        if idx in override_map:
            o = override_map[idx]
            if o.get('roman_override'):
                chord['roman'] = o['roman_override']
                chord['is_override'] = True
            if o.get('function_override'):
                chord['function'] = o['function_override']
                chord['color'] = HarmonicAnalyzer.FUNCTION_COLORS.get(
                    o['function_override'],
                    HarmonicAnalyzer.FUNCTION_COLORS['unknown']
                )
            if o.get('key_context_override'):
                chord['key_context'] = o['key_context_override']
            if o.get('is_pivot_chord'):
                chord['is_pivot'] = True
                chord['pivot_to_key'] = o.get('pivot_to_key')
            if o.get('notes'):
                chord['notes'] = o['notes']

    return result
