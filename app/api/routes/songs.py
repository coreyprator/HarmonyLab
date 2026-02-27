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


@router.delete("/{song_id}", status_code=204)
async def delete_song(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """Delete a song (cascades to sections, measures, chords)."""
    result = db.execute_non_query("DELETE FROM Songs WHERE id = ?", (song_id,))

    if result == 0:
        raise HTTPException(status_code=404, detail="Song not found")

    return None


@router.get("/{song_id}/notes")
async def get_song_notes(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """Get individual notes (MelodyNotes) for a song, grouped by measure."""
    # Verify song exists
    songs = db.execute_query("SELECT id FROM Songs WHERE id = ?", (song_id,))
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")

    notes = db.execute_query("""
        SELECT measure_number, beat_position, midi_note, duration, velocity
        FROM MelodyNotes
        WHERE song_id = ?
        ORDER BY measure_number, beat_position
    """, (song_id,))

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
