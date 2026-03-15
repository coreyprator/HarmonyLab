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
import uuid

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
    # Use flats for "black key" pitch classes (conventional jazz spelling):
    # Db(1), Eb(3), Gb(6), Ab(8), Bb(10) — never D#, G#, etc.
    use_flats = new_pc in (1, 3, 6, 8, 10)
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

    # HL-006E: Fallback to MelodyNotes
    if not notes_per_measure:
        try:
            legacy_rows = db.execute_query("""
                SELECT midi_note, measure_number FROM MelodyNotes
                WHERE song_id = ?
                ORDER BY measure_number, beat_position
            """, (song_id,))
            if legacy_rows:
                transposed_midi = [r['midi_note'] + semitones for r in legacy_rows]
                for r in legacy_rows:
                    m = r['measure_number']
                    notes_per_measure[m] = notes_per_measure.get(m, 0) + 1
        except Exception:
            pass

    # Re-analyze with transposed chords and shifted notes
    # Pass transposed notes for key detection (no key override — let algorithm detect)
    result = analyze_song(transposed_symbols, key_override=None, midi_notes=transposed_midi)

    # HL-TRANSPOSE-001: Convert sharp roman numerals to flat equivalents
    # music21 produces #III, #IV etc. for chromatic chords — jazz convention uses bIV, bV
    # Handles both uppercase (major) and lowercase (minor) roman numerals
    _SHARP_TO_FLAT_RE = re.compile(
        r'^#(VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)(.*)'
    )
    _DEGREE_NEXT = {
        'I': 'II', 'II': 'III', 'III': 'IV', 'IV': 'V', 'V': 'VI', 'VI': 'VII', 'VII': 'I',
        'i': 'ii', 'ii': 'iii', 'iii': 'iv', 'iv': 'v', 'v': 'vi', 'vi': 'vii', 'vii': 'i',
    }
    for ch in result.get('chords', []):
        roman = ch.get('roman', '')
        m = _SHARP_TO_FLAT_RE.match(roman)
        if m:
            degree, suffix = m.group(1), m.group(2)
            flat_degree = _DEGREE_NEXT.get(degree, degree)
            ch['roman'] = 'b' + flat_degree + suffix

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
            # HL-MEGA-003: Enrich with live note counts (may have changed since cache)
            result = _enrich_note_counts(result, song_id, db)
            # HL-006: Apply secondary dominant flags (cache predates this detection)
            result = _enrich_secondary_dominants(result)
            return _apply_overrides(result, song_id, db)

    # Verify song exists
    songs = db.execute_query("SELECT id, original_key, source_file_type FROM Songs WHERE id = ?", (song_id,))
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
    note_measures = None
    notes_per_measure = {}
    try:
        note_rows = db.execute_query("""
            SELECT midi_pitch, measure_num FROM song_notes
            WHERE song_id = ? AND is_rest = 0
            ORDER BY measure_num, beat
        """, (song_id,))
        if note_rows:
            midi_notes = [r['midi_pitch'] for r in note_rows]
            note_measures = [r['measure_num'] for r in note_rows]
            for r in note_rows:
                m = r['measure_num']
                notes_per_measure[m] = notes_per_measure.get(m, 0) + 1
    except Exception:
        pass

    # HL-006E: Fallback to MelodyNotes if song_notes is empty
    if not notes_per_measure:
        try:
            legacy_rows = db.execute_query("""
                SELECT midi_note, measure_number FROM MelodyNotes
                WHERE song_id = ?
                ORDER BY measure_number, beat_position
            """, (song_id,))
            if legacy_rows:
                midi_notes = [r['midi_note'] for r in legacy_rows]
                note_measures = [r['measure_number'] for r in legacy_rows]
                for r in legacy_rows:
                    m = r['measure_number']
                    notes_per_measure[m] = notes_per_measure.get(m, 0) + 1
        except Exception:
            pass

    # Run analysis (HL-006A: pass measure data for cadence weighting)
    max_chord_measure = max((c['measure_number'] for c in chords), default=0)
    result = analyze_song(chord_symbols, key_override, midi_notes,
                          note_measures, max_chord_measure)
    result['has_note_data'] = midi_notes is not None

    # HL-006B: Determine chord provenance from source file type
    source_type = songs[0].get('source_file_type', '')
    if source_type == 'MIDI':
        chord_source = 'algorithm'
    elif source_type in ('MuseScore', 'MusicXML'):
        chord_source = 'score'
    else:
        chord_source = 'algorithm'
    result['chord_source'] = chord_source

    # HL-006D: Build per-measure pitch class sets for rootless detection
    measure_pitch_classes = {}
    if chord_source == 'algorithm' and midi_notes and note_measures:
        for pitch, meas in zip(midi_notes, note_measures):
            if meas not in measure_pitch_classes:
                measure_pitch_classes[meas] = set()
            measure_pitch_classes[meas].add(pitch % 12)

    # Map note names to pitch classes for root detection
    _ROOT_PC = {'C': 0, 'C#': 1, 'D-': 1, 'Db': 1, 'D': 2, 'D#': 3,
                'E-': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G-': 6,
                'Gb': 6, 'G': 7, 'G#': 8, 'A-': 8, 'Ab': 8, 'A': 9,
                'A#': 10, 'B-': 10, 'Bb': 10, 'B': 11}

    # Enrich with measure/beat positions, note counts, and provenance
    for i, ch in enumerate(result.get('chords', [])):
        if i < len(chord_positions):
            ch['measure'] = chord_positions[i]['measure']
            ch['beat'] = chord_positions[i]['beat']
            ch['note_count'] = notes_per_measure.get(chord_positions[i]['measure'], 0)
            ch['chord_source'] = chord_source  # HL-006B

            # HL-006D: Detect rootless voicing for MIDI algorithm chords
            ch['is_rootless'] = False
            if chord_source == 'algorithm' and measure_pitch_classes:
                symbol = ch.get('symbol', '')
                root_match = re.match(r'^([A-G][#b]?)', symbol)
                if root_match:
                    root_name = root_match.group(1)
                    root_pc = _ROOT_PC.get(root_name)
                    meas = chord_positions[i]['measure']
                    pcs = measure_pitch_classes.get(meas, set())
                    # Rootless: root pitch class absent from measure notes,
                    # and chord has extension (7th/9th/etc.)
                    if root_pc is not None and pcs and root_pc not in pcs:
                        quality = symbol[len(root_name):]
                        has_extension = any(x in quality for x in ('7', '9', '11', '13'))
                        if has_extension:
                            ch['is_rootless'] = True

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


@router.get("/songs/{song_id}/rlhf/status")
async def get_rlhf_status(
    song_id: int,
    db: DatabaseConnection = Depends(get_db),
):
    """Check RLHF status for a song."""
    try:
        session = db.execute_query(
            "SELECT id, overrides_applied, algorithm_version, status, activated_at "
            "FROM rlhf_sessions WHERE song_id = ? AND status = 'active' "
            "ORDER BY activated_at DESC",
            (song_id,)
        )
        if session:
            return {
                "active": True,
                "session_id": session[0]['id'],
                "overrides_applied": session[0]['overrides_applied'],
                "algorithm_version": session[0]['algorithm_version'],
            }
    except Exception:
        pass
    return {"active": False, "session_id": None, "overrides_applied": 0}


@router.post("/songs/{song_id}/rlhf/activate")
async def activate_rlhf(
    song_id: int,
    db: DatabaseConnection = Depends(get_db),
):
    """Activate RLHF corrections for a song.

    Cross-song learning: finds overrides across all songs where the same
    chord symbol + key context was corrected, then applies evidence-based
    corrections to unoverridden chords in the current song.
    """
    # Check for already-active session
    existing = db.execute_query(
        "SELECT id FROM rlhf_sessions WHERE song_id = ? AND status = 'active'",
        (song_id,)
    )
    if existing:
        raise HTTPException(status_code=409, detail="RLHF already active for this song")

    # Get current algorithm analysis (baseline)
    cached = db.execute_query(
        "SELECT analysis_json FROM SongAnalysis WHERE song_id = ?", (song_id,)
    )
    if not cached or not cached[0].get('analysis_json'):
        raise HTTPException(status_code=404, detail="No analysis found — run analysis first")

    algorithm_result = json.loads(cached[0]['analysis_json'])

    # Get this song's existing overrides (already applied separately)
    song_overrides = db.execute_query(
        "SELECT chord_index FROM ChordAnalysisOverrides WHERE song_id = ?",
        (song_id,)
    )
    song_override_indices = {o['chord_index'] for o in song_overrides}

    # Build cross-song evidence: chord_symbol + key_context → {roman: count}
    # Query all overrides across all songs (excluding current song)
    all_overrides = db.execute_query("""
        SELECT o.song_id, o.chord_index, o.roman_override, o.function_override,
               sa.analysis_json
        FROM ChordAnalysisOverrides o
        JOIN SongAnalysis sa ON o.song_id = sa.song_id
        WHERE o.song_id != ? AND o.roman_override IS NOT NULL
    """, (song_id,))

    # Build evidence map: (chord_symbol, key_context) → {roman: count}
    evidence = {}
    for ov in all_overrides:
        try:
            ov_analysis = json.loads(ov['analysis_json'])
            ov_chords = ov_analysis.get('chords', [])
            for ch in ov_chords:
                if ch.get('index') == ov['chord_index']:
                    key = (ch.get('symbol', ''), ch.get('key_context', ''))
                    if key not in evidence:
                        evidence[key] = {}
                    roman = ov['roman_override']
                    evidence[key][roman] = evidence[key].get(roman, 0) + 1
                    break
        except Exception:
            continue

    # Apply RLHF evidence to current song's chords
    influenced_count = 0
    chords = algorithm_result.get('chords', [])
    for ch in chords:
        idx = ch.get('index')
        if idx in song_override_indices:
            continue  # Already has a direct override

        key = (ch.get('symbol', ''), ch.get('key_context', ''))
        if key not in evidence:
            continue

        corrections = evidence[key]
        total = sum(corrections.values())
        if total == 0:
            continue

        # Find best correction
        best_roman, best_count = max(corrections.items(), key=lambda x: x[1])
        rlhf_score = best_count / total

        # Only apply if strong enough evidence (> 0.5 rlhf_score)
        # Blend: 0.7 * algo + 0.3 * rlhf — since algo is "current" and rlhf is
        # "suggested", we apply when 0.3 * rlhf_score tips the balance
        if rlhf_score >= 0.5 and best_roman != ch.get('roman'):
            ch['algorithm_result'] = ch.get('roman', '')
            ch['roman'] = best_roman
            ch['rlhf_influenced'] = True
            ch['chord_source'] = 'override'
            influenced_count += 1

    # Store session with algorithm snapshot (for revert)
    session_id = str(uuid.uuid4())
    algorithm_snapshot = cached[0]['analysis_json']  # Pre-RLHF state

    db.execute_non_query("""
        INSERT INTO rlhf_sessions
            (id, song_id, overrides_applied, algorithm_version, status, algorithm_snapshot)
        VALUES (?, ?, ?, '1.1', 'active', ?)
    """, (session_id, song_id, influenced_count, algorithm_snapshot))

    # Update cached analysis with RLHF-modified result
    rlhf_json = json.dumps(algorithm_result)
    db.execute_non_query("""
        UPDATE SongAnalysis SET analysis_json = ?, updated_at = GETDATE()
        WHERE song_id = ?
    """, (rlhf_json, song_id))

    # Apply direct overrides on top and return
    result = _apply_overrides(algorithm_result, song_id, db)

    return {
        "status": "activated",
        "session_id": session_id,
        "overrides_applied": influenced_count,
        "algorithm_version": "1.1",
        "rlhf_version": "1.0",
        "analysis": result,
    }


@router.post("/songs/{song_id}/rlhf/revert")
async def revert_rlhf(
    song_id: int,
    db: DatabaseConnection = Depends(get_db),
):
    """Revert RLHF corrections, restoring pure algorithm results."""
    # Find active session
    sessions = db.execute_query(
        "SELECT id, algorithm_snapshot FROM rlhf_sessions "
        "WHERE song_id = ? AND status = 'active' ORDER BY activated_at DESC",
        (song_id,)
    )
    if not sessions:
        raise HTTPException(status_code=404, detail="No active RLHF session to revert")

    session = sessions[0]
    snapshot = session.get('algorithm_snapshot')

    if snapshot:
        # Restore the pre-RLHF algorithm analysis
        db.execute_non_query("""
            UPDATE SongAnalysis SET analysis_json = ?, updated_at = GETDATE()
            WHERE song_id = ?
        """, (snapshot, song_id))

    # Mark session as reverted
    db.execute_non_query("""
        UPDATE rlhf_sessions SET status = 'reverted', reverted_at = GETDATE()
        WHERE id = ?
    """, (session['id'],))

    # Return the restored analysis
    result = json.loads(snapshot) if snapshot else {}
    result = _apply_overrides(result, song_id, db)

    return {
        "status": "reverted",
        "message": "Reverted to algorithm analysis.",
        "analysis": result,
    }


def _enrich_note_counts(result: dict, song_id: int, db: DatabaseConnection) -> dict:
    """HL-MEGA-003: Refresh note counts from live DB (song_notes → MelodyNotes fallback)."""
    notes_per_measure = {}
    try:
        rows = db.execute_query("""
            SELECT measure_num, COUNT(*) as cnt FROM song_notes
            WHERE song_id = ? AND is_rest = 0
            GROUP BY measure_num
        """, (song_id,))
        for r in rows:
            notes_per_measure[r['measure_num']] = r['cnt']
    except Exception:
        pass
    if not notes_per_measure:
        try:
            rows = db.execute_query("""
                SELECT measure_number, COUNT(*) as cnt FROM MelodyNotes
                WHERE song_id = ?
                GROUP BY measure_number
            """, (song_id,))
            for r in rows:
                notes_per_measure[r['measure_number']] = r['cnt']
        except Exception:
            pass
    if notes_per_measure:
        result['has_note_data'] = True
        for ch in result.get('chords', []):
            m = ch.get('measure')
            if m is not None:
                ch['note_count'] = notes_per_measure.get(m, 0)
    return result


def _enrich_secondary_dominants(result: dict) -> dict:
    """HL-006: Flag dom7 chords as secondary dominant candidates on cached results.
    Replicates HarmonicAnalyzer._detect_secondary_dominants() for stale cache entries."""
    import re
    _NOTE_SEMI = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4,
        'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9,
        'A#': 10, 'Bb': 10, 'B': 11,
    }

    def get_root_semitone(symbol):
        m = re.match(r'^([A-G][#b]?)', symbol or '')
        if not m:
            return None
        return _NOTE_SEMI.get(m.group(1))

    def is_dom7_quality(symbol):
        if not symbol:
            return False
        quality = re.sub(r'^[A-G][#b]?', '', symbol)
        return bool(re.match(r'^(7|7b9|7#9|7#11|9|13|7alt|7sus4|9sus4)', quality))

    chords = result.get('chords', [])
    for i, ch in enumerate(chords):
        sym = ch.get('symbol', '')
        if not is_dom7_quality(sym):
            continue
        ch['secondary_dominant_candidate'] = True
        if i < len(chords) - 1:
            nxt_sym = chords[i + 1].get('symbol', '')
            root = get_root_semitone(sym)
            nxt_root = get_root_semitone(nxt_sym)
            if root is not None and nxt_root is not None:
                if (root - nxt_root) % 12 == 7:
                    ch['secondary_dominant_target'] = nxt_sym
    return result


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
                chord['chord_source'] = 'override'  # HL-006B
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
