"""
Analysis API Routes
Harmonic analysis, chord overrides, and key region management.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel
from app.services.analysis_service import analyze_song, HarmonicAnalyzer
from app.db.connection import DatabaseConnection, get_db
import json
import re
import logging

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)

NOTE_NAMES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_NAMES_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

def transpose_chord_symbol(symbol: str, semitones: int) -> str:
    """Transpose a chord symbol by N semitones."""
    if not symbol or symbol == 'N.C.':
        return symbol
    match = re.match(r'^([A-G])([#b]?)(.*)', symbol)
    if not match:
        return symbol
    root_letter = match.group(1)
    accidental = match.group(2)
    quality = match.group(3)

    # Handle slash chords (e.g., Dm7/G)
    bass_part = ''
    if '/' in quality:
        slash_idx = quality.index('/')
        bass_note = quality[slash_idx + 1:]
        quality = quality[:slash_idx]
        # Transpose bass note too
        bass_part = '/' + transpose_chord_symbol(bass_note, semitones)

    root_str = root_letter + accidental
    # Find current pitch class
    lookup = {n: i for i, n in enumerate(NOTE_NAMES_SHARP)}
    lookup.update({n: i for i, n in enumerate(NOTE_NAMES_FLAT)})
    pc = lookup.get(root_str)
    if pc is None:
        return symbol
    new_pc = (pc + semitones) % 12
    # Use flats for flat keys, sharps otherwise
    use_flats = accidental == 'b' or semitones < 0
    new_root = NOTE_NAMES_FLAT[new_pc] if use_flats else NOTE_NAMES_SHARP[new_pc]
    return new_root + quality + bass_part


class AnalysisRequest(BaseModel):
    key_override: Optional[str] = None


class ChordOverrideRequest(BaseModel):
    roman: Optional[str] = None
    function: Optional[str] = None
    key_context: Optional[str] = None
    is_pivot: bool = False
    pivot_to_key: Optional[str] = None
    notes: Optional[str] = None


@router.get("/roman")
async def get_roman_numeral(
    symbol: str,
    key: str = "C",
):
    """Calculate Roman numeral for a chord symbol in a given key context.
    Used by the Edit Chord Analysis modal for real-time preview.
    """
    if not symbol:
        return {"roman": "?", "function": "unknown", "color": None}

    try:
        analyzer = HarmonicAnalyzer()
        from music21 import key as m21key
        analyzer.current_key = m21key.Key(key)
        analysis = analyzer._analyze_chord(symbol, 0)
        return {
            "roman": analysis.get("roman", "?"),
            "function": analysis.get("function", "unknown"),
            "color": analysis.get("color"),
        }
    except Exception as e:
        logger.warning("Roman numeral calculation failed for %s in key %s: %s", symbol, key, e)
        return {"roman": "?", "function": "unknown", "color": None}


@router.get("/songs/{song_id}/key-centers")
async def get_key_centers(
    song_id: int,
    db: DatabaseConnection = Depends(get_db),
):
    """Get key center regions for a song."""
    from app.services.key_center_service import detect_key_centers, detect_ii_v_i_patterns

    # Get analysis data first
    analysis = await get_analysis(song_id, db=db)
    chords = analysis.get('chords', [])
    detected_key = analysis.get('detected_key', 'C')

    regions = detect_key_centers(chords, detected_key)
    patterns = detect_ii_v_i_patterns(chords)

    return {
        'song_id': song_id,
        'detected_key': detected_key,
        'regions': regions,
        'patterns': patterns,
    }


@router.get("/songs/{song_id}/patterns")
async def get_patterns(
    song_id: int,
    db: DatabaseConnection = Depends(get_db),
):
    """Get detected harmonic patterns for a song."""
    from app.services.key_center_service import detect_ii_v_i_patterns

    analysis = await get_analysis(song_id, db=db)
    chords = analysis.get('chords', [])

    patterns = detect_ii_v_i_patterns(chords)

    return {
        'song_id': song_id,
        'patterns': patterns,
    }


class TransposeRequest(BaseModel):
    semitones: int


@router.post("/songs/{song_id}/transpose")
async def transpose_song(
    song_id: int,
    request: TransposeRequest,
    db: DatabaseConnection = Depends(get_db),
):
    """Transpose a song's analysis by N semitones. Session-only, not persisted."""
    semitones = max(-11, min(11, request.semitones))

    # Get chords for this song
    chords = db.execute_query("""
        SELECT c.chord_symbol, m.measure_number, c.beat_position, c.chord_order
        FROM Chords c
        JOIN Measures m ON c.measure_id = m.id
        JOIN Sections s ON m.section_id = s.id
        WHERE s.song_id = ?
        ORDER BY s.section_order, m.measure_number, c.chord_order
    """, (song_id,))

    if not chords:
        raise HTTPException(status_code=404, detail="No chords found for this song")

    # Transpose each chord symbol
    transposed_symbols = [transpose_chord_symbol(c['chord_symbol'], semitones) for c in chords]

    # Fetch and transpose MIDI notes for note-based key detection
    transposed_midi = None
    notes_per_measure = {}
    try:
        note_rows = db.execute_query("""
            SELECT midi_pitch, measure_num FROM song_notes
            WHERE song_id = ? AND is_rest = 0
            ORDER BY measure_num, beat
        """, (song_id,))
        if note_rows:
            transposed_midi = [r['midi_pitch'] + semitones for r in note_rows]
            for r in note_rows:
                m = r['measure_num']
                notes_per_measure[m] = notes_per_measure.get(m, 0) + 1
    except Exception:
        pass

    # Re-analyze with transposed chords and shifted notes
    # Pass transposed notes for key detection (no key override — let algorithm detect)
    result = analyze_song(transposed_symbols, key_override=None, midi_notes=transposed_midi)

    # Enrich with measure/beat positions and note counts
    chord_positions = [
        {"measure": c['measure_number'], "beat": float(c.get('beat_position') or 1.0)}
        for c in chords
    ]
    for i, ch in enumerate(result.get('chords', [])):
        if i < len(chord_positions):
            ch['measure'] = chord_positions[i]['measure']
            ch['beat'] = chord_positions[i]['beat']
            ch['note_count'] = notes_per_measure.get(chord_positions[i]['measure'], 0)

    # Report original key from Songs table
    songs = db.execute_query("SELECT original_key FROM Songs WHERE id = ?", (song_id,))
    original_key = (songs[0].get('original_key') or 'C') if songs else 'C'

    result['transposed_semitones'] = semitones
    result['original_key'] = original_key

    return result


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
        # Return empty analysis instead of 404 so the page still loads
        empty_result = {
            "detected_key": songs[0].get('original_key') or "C",
            "confidence": 0.0,
            "chords": [],
            "patterns": [],
            "total_measures": 0,
            "message": "No chord symbols found for this song. Try re-importing the score file, or check for duplicate entries.",
        }
        return empty_result

    chord_symbols = [c['chord_symbol'] for c in chords]
    # Build measure context for each chord (cast Decimal to float for JSON)
    chord_positions = [
        {"measure": c['measure_number'], "beat": float(c.get('beat_position') or 1.0)}
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

    # Fetch MIDI notes for note-based key detection (more accurate than chord-only)
    midi_notes = None
    notes_per_measure = {}
    try:
        note_rows = db.execute_query("""
            SELECT midi_pitch, measure_num FROM song_notes
            WHERE song_id = ? AND is_rest = 0
            ORDER BY measure_num, beat
        """, (song_id,))
        if note_rows:
            midi_notes = [r['midi_pitch'] for r in note_rows]
            for r in note_rows:
                m = r['measure_num']
                notes_per_measure[m] = notes_per_measure.get(m, 0) + 1
    except Exception:
        pass

    # Run analysis
    result = analyze_song(chord_symbols, key_override, midi_notes)
    result['has_note_data'] = midi_notes is not None

    # Enrich with measure/beat positions and note counts
    for i, ch in enumerate(result.get('chords', [])):
        if i < len(chord_positions):
            ch['measure'] = chord_positions[i]['measure']
            ch['beat'] = chord_positions[i]['beat']
            ch['note_count'] = notes_per_measure.get(chord_positions[i]['measure'], 0)

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
