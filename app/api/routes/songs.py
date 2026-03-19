"""
Songs API Routes

CRUD operations for songs.
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from app.models import Song, SongCreate, SongUpdate
from app.db.connection import DatabaseConnection, get_db


router = APIRouter(prefix="/api/v1/songs", tags=["songs"])


@router.get("/", response_model=List[Song])
async def list_songs(
    skip: int = 0,
    limit: int = 100,
    genre: str = None,
    db: DatabaseConnection = Depends(get_db)
):
    """
    List all songs with optional filtering.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **genre**: Filter by genre (optional)
    """
    query = "SELECT * FROM Songs"
    params = []
    
    if genre:
        query += " WHERE genre = ?"
        params.append(genre)
    
    query += " ORDER BY title OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    params.extend([skip, limit])
    
    songs = db.execute_query(query, tuple(params))
    return songs


@router.get("/{song_id}", response_model=Song)
async def get_song(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """Get a specific song by ID."""
    query = "SELECT * FROM Songs WHERE id = ?"
    songs = db.execute_query(query, (song_id,))
    
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")
    
    return songs[0]


@router.post("/", response_model=Song, status_code=201)
async def create_song(song: SongCreate, db: DatabaseConnection = Depends(get_db)):
    """Create a new song."""
    query = """
    INSERT INTO Songs (
        title, composer, arranger, original_key, tempo_marking, 
        genre, time_signature, year_composed, notes,
        source_file_name, source_file_type
    )
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    params = (
        song.title, song.composer, song.arranger, song.original_key,
        song.tempo_marking, song.genre, song.time_signature,
        song.year_composed, song.notes, song.source_file_name,
        song.source_file_type
    )
    
    song_id = db.execute_scalar(query, params)
    
    if not song_id:
        raise HTTPException(status_code=500, detail="Failed to create song")
    
    return await get_song(song_id, db)


@router.put("/{song_id}", response_model=Song)
async def update_song(
    song_id: int,
    song_update: SongUpdate,
    db: DatabaseConnection = Depends(get_db)
):
    """Update an existing song."""
    # Check if song exists
    existing = db.execute_query("SELECT id FROM Songs WHERE id = ?", (song_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Song not found")
    
    # Build dynamic UPDATE query for non-None fields
    update_fields = []
    params = []
    
    for field, value in song_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        params.append(value)
    
    if not update_fields:
        return await get_song(song_id, db)
    
    # Add updated_at timestamp
    update_fields.append("updated_at = GETDATE()")
    params.append(song_id)
    
    query = f"UPDATE Songs SET {', '.join(update_fields)} WHERE id = ?"
    db.execute_non_query(query, tuple(params))
    
    return await get_song(song_id, db)


@router.delete("/bulk/delete")
async def bulk_delete_songs(
    song_ids: List[int],
    db: DatabaseConnection = Depends(get_db)
):
    """Delete multiple songs at once. Returns count of deleted songs."""
    if not song_ids:
        raise HTTPException(status_code=400, detail="No song IDs provided")
    if len(song_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 songs per bulk delete")

    deleted = 0
    cleanup_tables = [
        "rlhf_sessions", "ChordAnalysisOverrides", "SongAnalysis",
        "QuizAttempts", "UserSongProgress",
        "song_notes", "song_lyrics", "song_dynamics", "song_tempos",
        "song_time_signatures", "song_key_signatures", "song_text_marks",
        "song_imports", "MelodyNotes",
    ]
    for sid in song_ids:
        try:
            for table in cleanup_tables:
                try:
                    db.execute_non_query(f"DELETE FROM {table} WHERE song_id = ?", (sid,))
                except Exception:
                    pass
            try:
                db.execute_non_query("""
                    DELETE c FROM Chords c
                    INNER JOIN Measures m ON c.measure_id = m.id
                    INNER JOIN Sections s ON m.section_id = s.id
                    WHERE s.song_id = ?
                """, (sid,))
            except Exception:
                pass
            try:
                db.execute_non_query("""
                    DELETE m FROM Measures m
                    INNER JOIN Sections s ON m.section_id = s.id
                    WHERE s.song_id = ?
                """, (sid,))
            except Exception:
                pass
            try:
                db.execute_non_query("DELETE FROM Sections WHERE song_id = ?", (sid,))
            except Exception:
                pass
            result = db.execute_non_query("DELETE FROM Songs WHERE id = ?", (sid,))
            if result and result > 0:
                deleted += 1
        except Exception:
            pass

    return {"deleted": deleted, "requested": len(song_ids)}


@router.delete("/{song_id}", status_code=204)
async def delete_song(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """Delete a song with full cascade cleanup for legacy and modern schemas.
    Deletes child records in dependency order before removing the song row."""
    existing = db.execute_query("SELECT id FROM Songs WHERE id = ?", (song_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Song not found")

    # Delete child records in dependency order (deepest FK refs first)
    cleanup_tables = [
        "rlhf_sessions", "ChordAnalysisOverrides", "SongAnalysis",
        "QuizAttempts", "UserSongProgress",
        "song_notes", "song_lyrics", "song_dynamics", "song_tempos",
        "song_time_signatures", "song_key_signatures", "song_text_marks",
        "song_imports", "MelodyNotes",
    ]
    for table in cleanup_tables:
        try:
            db.execute_non_query(f"DELETE FROM {table} WHERE song_id = ?", (song_id,))
        except Exception:
            pass

    # Chords → Measures → Sections (explicit cascade for legacy songs)
    try:
        db.execute_non_query("""
            DELETE c FROM Chords c
            INNER JOIN Measures m ON c.measure_id = m.id
            INNER JOIN Sections s ON m.section_id = s.id
            WHERE s.song_id = ?
        """, (song_id,))
    except Exception:
        pass
    try:
        db.execute_non_query("""
            DELETE m FROM Measures m
            INNER JOIN Sections s ON m.section_id = s.id
            WHERE s.song_id = ?
        """, (song_id,))
    except Exception:
        pass
    try:
        db.execute_non_query("DELETE FROM Sections WHERE song_id = ?", (song_id,))
    except Exception:
        pass

    db.execute_non_query("DELETE FROM Songs WHERE id = ?", (song_id,))
    return None


@router.get("/{song_id}/audit")
async def get_song_audit(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """Get full import audit data for a song, grouped by measure."""
    songs = db.execute_query("SELECT * FROM Songs WHERE id = ?", (song_id,))
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")
    song = songs[0]

    # Load all rich note data
    try:
        notes = db.execute_query("""
            SELECT * FROM song_notes
            WHERE song_id = ? ORDER BY measure_num, beat, track_num, midi_pitch DESC
        """, (song_id,))
    except Exception:
        notes = []

    try:
        lyrics = db.execute_query("""
            SELECT * FROM song_lyrics
            WHERE song_id = ? ORDER BY measure_num, beat, verse_num
        """, (song_id,))
    except Exception:
        lyrics = []

    try:
        dynamics = db.execute_query("""
            SELECT * FROM song_dynamics
            WHERE song_id = ? ORDER BY measure_num, beat
        """, (song_id,))
    except Exception:
        dynamics = []

    try:
        tempos = db.execute_query("""
            SELECT * FROM song_tempos
            WHERE song_id = ? ORDER BY measure_num, beat
        """, (song_id,))
    except Exception:
        tempos = []

    try:
        time_sigs = db.execute_query("""
            SELECT * FROM song_time_signatures
            WHERE song_id = ? ORDER BY measure_num
        """, (song_id,))
    except Exception:
        time_sigs = []

    try:
        key_sigs = db.execute_query("""
            SELECT * FROM song_key_signatures
            WHERE song_id = ? ORDER BY measure_num
        """, (song_id,))
    except Exception:
        key_sigs = []

    try:
        text_marks = db.execute_query("""
            SELECT * FROM song_text_marks
            WHERE song_id = ? ORDER BY measure_num, beat
        """, (song_id,))
    except Exception:
        text_marks = []

    # Group by measure
    measures = {}
    for n in notes:
        m = n['measure_num']
        measures.setdefault(m, {'notes': [], 'lyrics': [], 'dynamics': [],
                                'tempos': [], 'time_signatures': [], 'key_signatures': [],
                                'text_marks': []})
        measures[m]['notes'].append(dict(n))

    for lyr in lyrics:
        m = lyr['measure_num']
        measures.setdefault(m, {'notes': [], 'lyrics': [], 'dynamics': [],
                                'tempos': [], 'time_signatures': [], 'key_signatures': [],
                                'text_marks': []})
        measures[m]['lyrics'].append(dict(lyr))

    for d in dynamics:
        m = d['measure_num']
        if m in measures:
            measures[m]['dynamics'].append(dict(d))

    for t in tempos:
        m = t['measure_num']
        if m in measures:
            measures[m]['tempos'].append(dict(t))

    for ts in time_sigs:
        m = ts['measure_num']
        if m in measures:
            measures[m]['time_signatures'].append(dict(ts))

    for ks in key_sigs:
        m = ks['measure_num']
        if m in measures:
            measures[m]['key_signatures'].append(dict(ks))

    for tm in text_marks:
        m = tm['measure_num']
        if m in measures:
            measures[m]['text_marks'].append(dict(tm))

    # Statistics
    actual_notes = [n for n in notes if not n.get('is_rest')]
    pitches = [n['midi_pitch'] for n in actual_notes] if actual_notes else []

    return {
        'song_id': song_id,
        'title': song.get('title'),
        'import_format': song.get('import_format'),
        'total_notes': song.get('total_notes', len(actual_notes)),
        'has_lyrics': bool(song.get('has_lyrics')),
        'has_note_data': bool(song.get('has_note_data')),
        'track_count': song.get('track_count'),
        'measure_count': song.get('measure_count'),
        'statistics': {
            'note_count': len(actual_notes),
            'rest_count': len(notes) - len(actual_notes),
            'lyric_count': len(lyrics),
            'unique_pitches': len(set(pitches)),
            'lowest_note': min(pitches) if pitches else None,
            'highest_note': max(pitches) if pitches else None,
            'avg_velocity': round(sum(n.get('velocity', 64) for n in actual_notes) / len(actual_notes), 1) if actual_notes else None,
        },
        'measures': [
            {'measure_num': m, **data}
            for m, data in sorted(measures.items())
        ],
    }


@router.get("/{song_id}/imports")
async def get_song_imports(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """Get all import records for a song, newest first."""
    songs = db.execute_query("SELECT id, title FROM Songs WHERE id = ?", (song_id,))
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")

    try:
        imports = db.execute_query("""
            SELECT * FROM song_imports
            WHERE song_id = ? ORDER BY uploaded_at DESC
        """, (song_id,))
    except Exception:
        imports = []

    return {
        'song_id': song_id,
        'import_count': len(imports),
        'imports': [dict(i) for i in imports],
    }


@router.get("/{song_id}/notes")
async def get_song_notes(
    song_id: int,
    measure: int = None,
    db: DatabaseConnection = Depends(get_db),
):
    """Get individual notes for a song. Queries song_notes (rich import) first,
    falls back to MelodyNotes (legacy). Optional measure filter."""
    songs = db.execute_query("SELECT id FROM Songs WHERE id = ?", (song_id,))
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")

    # Try song_notes table first (rich import data)
    notes = []
    try:
        if measure is not None:
            notes = db.execute_query("""
                SELECT measure_num, beat, midi_pitch, note_name,
                       duration_quarters, velocity, is_rest
                FROM song_notes
                WHERE song_id = ? AND is_rest = 0 AND measure_num = ?
                ORDER BY beat
            """, (song_id, measure))
        else:
            notes = db.execute_query("""
                SELECT measure_num, beat, midi_pitch, note_name,
                       duration_quarters, velocity, is_rest
                FROM song_notes
                WHERE song_id = ? AND is_rest = 0
                ORDER BY measure_num, beat
            """, (song_id,))
    except Exception:
        pass

    if notes:
        return {
            "song_id": song_id,
            "notes": [
                {
                    "measure_number": n['measure_num'],
                    "beat_position": float(n.get('beat') or 1.0),
                    "midi_note": n['midi_pitch'],
                    "note_name": n.get('note_name'),
                    "duration": float(n['duration_quarters']) if n.get('duration_quarters') is not None else 1.0,
                    "velocity": n.get('velocity'),
                }
                for n in notes
            ],
            "total_notes": len(notes),
        }

    # Fallback to legacy MelodyNotes table
    try:
        notes = db.execute_query("""
            SELECT measure_number, beat_position, midi_note, duration, velocity
            FROM MelodyNotes
            WHERE song_id = ?
            ORDER BY measure_number, beat_position
        """, (song_id,))
    except Exception:
        notes = []

    if not notes:
        raise HTTPException(status_code=404, detail="No note data for this song")

    return {
        "song_id": song_id,
        "notes": [
            {
                "measure_number": n['measure_number'],
                "beat_position": float(n.get('beat_position') or 1.0),
                "midi_note": n['midi_note'],
                "duration": float(n['duration']) if n.get('duration') is not None else 1.0,
                "velocity": n.get('velocity'),
            }
            for n in notes
        ],
        "total_notes": len(notes),
    }


@router.get("/{song_id}/chords")
async def get_song_chords(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """HL-036: Get all chords for a song with measure and beat_position fields for playback.
    Primary source: Chords table (joined via Measures).
    Fallback: SongAnalysis JSON blob (algorithm-analyzed songs without DB chord rows).
    """
    import json as _json
    songs = db.execute_query("SELECT id FROM Songs WHERE id = ?", (song_id,))
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")

    # Primary: Chords table
    chords = []
    try:
        chords = db.execute_query("""
            SELECT c.id, c.beat_position, c.chord_symbol, c.roman_numeral,
                   m.measure_number
            FROM Chords c
            JOIN Measures m ON c.measure_id = m.id
            WHERE m.song_id = ?
            ORDER BY m.measure_number, c.beat_position
        """, (song_id,))
    except Exception:
        chords = []

    if chords:
        return {
            "song_id": song_id,
            "source": "db",
            "chords": [
                {
                    "id": c["id"],
                    "measure": c["measure_number"],
                    "beat_position": float(c.get("beat_position") or 1.0),
                    "symbol": c["chord_symbol"],
                    "roman": c.get("roman_numeral"),
                }
                for c in chords
            ],
            "total": len(chords),
        }

    # Fallback: SongAnalysis JSON blob
    try:
        cached = db.execute_query(
            "SELECT analysis_json FROM SongAnalysis WHERE song_id = ?", (song_id,)
        )
        if cached and cached[0].get("analysis_json"):
            analysis = _json.loads(cached[0]["analysis_json"])
            analysis_chords = analysis.get("chords", [])
            if analysis_chords:
                return {
                    "song_id": song_id,
                    "source": "analysis_cache",
                    "chords": [
                        {
                            "id": None,
                            "measure": c.get("measure", 1),
                            "beat_position": float(c.get("beat") or 1.0),
                            "symbol": c.get("symbol"),
                            "roman": c.get("roman"),
                        }
                        for c in analysis_chords
                    ],
                    "total": len(analysis_chords),
                }
    except Exception:
        pass

    return {"song_id": song_id, "source": "none", "chords": [], "total": 0}
