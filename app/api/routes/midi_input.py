"""
API routes for MIDI keyboard input and rhythm analysis.
HL-017: Real-time chord identification from MIDI input + rhythm analysis.
"""
import os
import tempfile
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from pydantic import BaseModel
from app.services.midi_parser import identify_chord, NOTE_NAMES
from app.services.analysis_service import HarmonicAnalyzer
from app.services.rhythm_analyzer import analyze_rhythm_from_midi
from app.db.connection import DatabaseConnection, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/midi", tags=["midi"])


class MidiNotesInput(BaseModel):
    """Input model for real-time MIDI chord identification."""
    notes: List[int]  # MIDI note numbers (0-127)
    key_context: Optional[str] = None  # Optional key for Roman numeral analysis


class ChordIdentificationResult(BaseModel):
    """Result of chord identification."""
    chord_symbol: str
    root: str
    quality: str
    midi_notes: List[int]
    note_names: List[str]
    roman_numeral: Optional[str] = None
    function: Optional[str] = None
    function_color: Optional[str] = None


@router.post("/identify")
async def identify_chord_from_notes(input: MidiNotesInput) -> ChordIdentificationResult:
    """Identify a chord from MIDI note numbers.

    Accepts an array of MIDI note numbers (e.g., from a MIDI keyboard via
    Web MIDI API) and returns the chord symbol, root, quality, and optionally
    the Roman numeral analysis in the given key context.

    Example: notes=[60, 64, 67] → C major triad
    """
    if not input.notes:
        raise HTTPException(status_code=400, detail="No notes provided")
    if len(input.notes) < 2:
        raise HTTPException(status_code=400, detail="At least 2 notes required for chord identification")

    # Use existing chord identification
    root_name, chord_type = identify_chord(input.notes)

    if not root_name:
        raise HTTPException(status_code=422, detail="Could not identify chord from provided notes")

    chord_symbol = f"{root_name}{chord_type}"
    note_names = [NOTE_NAMES[n % 12] for n in sorted(input.notes)]

    result = ChordIdentificationResult(
        chord_symbol=chord_symbol,
        root=root_name,
        quality=chord_type,
        midi_notes=sorted(input.notes),
        note_names=note_names,
    )

    # Optional Roman numeral analysis
    if input.key_context:
        try:
            analyzer = HarmonicAnalyzer()
            from music21 import key
            analyzer.current_key = key.Key(input.key_context)
            analysis = analyzer._analyze_chord(chord_symbol, 0)
            result.roman_numeral = analysis.get('roman')
            result.function = analysis.get('function')
            result.function_color = analysis.get('color')
        except Exception as e:
            logger.warning("Roman numeral analysis failed: %s", e)

    return result


@router.post("/rhythm/analyze")
async def analyze_midi_rhythm(
    file: UploadFile = File(...),
):
    """Analyze rhythmic patterns from a MIDI file.

    Returns swing/straight feel detection, syncopation score,
    subdivision breakdown, and per-track analysis.
    """
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ('.mid', '.midi'):
        raise HTTPException(status_code=400, detail="File must be .mid or .midi")

    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = analyze_rhythm_from_midi(tmp_path)
        return result
    except Exception as e:
        logger.exception("Rhythm analysis failed for %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Rhythm analysis failed: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/rhythm/song/{song_id}")
async def analyze_song_rhythm(
    song_id: int,
    db: DatabaseConnection = Depends(get_db),
):
    """Analyze rhythmic patterns for a song using stored MIDI note data.

    Uses MelodyNotes table if populated, otherwise returns basic
    rhythm info derived from chord positions.
    """
    # Check song exists
    songs = db.execute_query("SELECT id, title, time_signature FROM Songs WHERE id = ?", (song_id,))
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")

    song = songs[0]
    time_sig = song.get('time_signature') or '4/4'
    ts_parts = time_sig.split('/')
    ts_n = int(ts_parts[0]) if len(ts_parts) > 0 else 4

    # Try MelodyNotes first
    melody_notes = db.execute_query("""
        SELECT measure_number, beat_position, midi_note, duration, velocity
        FROM MelodyNotes WHERE song_id = ?
        ORDER BY measure_number, beat_position
    """, (song_id,))

    if melody_notes:
        # Convert to onset ticks (approximate: 480 tpb)
        tpb = 480
        onsets = []
        for note in melody_notes:
            m = note['measure_number']
            b = float(note.get('beat_position') or 1.0)
            tick = ((m - 1) * ts_n + (b - 1)) * tpb
            onsets.append(tick)

        from app.services.rhythm_analyzer import analyze_rhythm
        result = analyze_rhythm(onsets, tpb, int(ts_parts[0]), int(ts_parts[1]) if len(ts_parts) > 1 else 4)
        result['source'] = 'melody_notes'
        return result

    # Fall back to chord positions for basic rhythm analysis
    chords = db.execute_query("""
        SELECT m.measure_number, c.beat_position
        FROM Chords c
        JOIN Measures m ON c.measure_id = m.id
        JOIN Sections s ON m.section_id = s.id
        WHERE s.song_id = ?
        ORDER BY s.section_order, m.measure_number, c.chord_order
    """, (song_id,))

    if not chords:
        raise HTTPException(status_code=404, detail="No chord or melody data for rhythm analysis")

    # Derive basic rhythm from chord changes
    tpb = 480
    onsets = []
    for ch in chords:
        m = ch['measure_number']
        b = float(ch.get('beat_position') or 1.0)
        tick = ((m - 1) * ts_n + (b - 1)) * tpb
        onsets.append(tick)

    from app.services.rhythm_analyzer import analyze_rhythm
    result = analyze_rhythm(onsets, tpb, int(ts_parts[0]), int(ts_parts[1]) if len(ts_parts) > 1 else 4)
    result['source'] = 'chord_positions'
    result['details'] = (result.get('details', '') +
                         '. Note: Based on chord change positions only, not actual note data.')
    return result


@router.get("/webmidi-check")
async def check_webmidi_support():
    """Return info about Web MIDI API support for the frontend.

    The frontend should use navigator.requestMIDIAccess() to connect
    to a MIDI keyboard. This endpoint returns the recommended setup.
    """
    return {
        "web_midi_api": "navigator.requestMIDIAccess()",
        "supported_browsers": ["Chrome", "Edge", "Opera"],
        "not_supported": ["Firefox", "Safari (requires flag)"],
        "usage": {
            "connect": "const midi = await navigator.requestMIDIAccess()",
            "listen": "midi.inputs.forEach(input => input.onmidimessage = handler)",
            "identify": "POST /api/v1/midi/identify with {notes: [60, 64, 67]}",
        },
        "note": "MIDI keyboard input requires HTTPS (secure context) for Web MIDI API",
    }
