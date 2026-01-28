"""
Songs API Routes

CRUD operations for songs.
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from app.models import Song, SongCreate, SongUpdate
from app.db.connection import get_db_connection, db_legacy as db


router = APIRouter()


@router.get("/", response_model=List[Song])
async def list_songs(
    skip: int = 0,
    limit: int = 100,
    genre: str = None,
    
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
async def get_song(song_id: int, ):
    """Get a specific song by ID."""
    query = "SELECT * FROM Songs WHERE id = ?"
    songs = db.execute_query(query, (song_id,))
    
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")
    
    return songs[0]


@router.post("/", response_model=Song, status_code=201)
async def create_song(song: SongCreate, ):
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
    
    return await get_song(song_id)


@router.put("/{song_id}", response_model=Song)
async def update_song(
    song_id: int,
    song_update: SongUpdate,
    
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
async def delete_song(song_id: int, ):
    """Delete a song (cascades to sections, measures, chords)."""
    result = db.execute_non_query("DELETE FROM Songs WHERE id = ?", (song_id,))
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Song not found")
    
    return None


@router.get("/{song_id}/progression")
async def get_song_progression(song_id: int, ):
    """Get the complete chord progression for a song with all sections, measures, and chords."""
    # Get sections
    sections_query = """
    SELECT id, song_id, name as section_name, section_order, repeat_count 
    FROM Sections 
    WHERE song_id = ? 
    ORDER BY section_order
    """
    sections = db.execute_query(sections_query, (song_id,))
    
    if not sections:
        return {"sections": []}
    
    # For each section, get measures and chords
    for section in sections:
        section['section_id'] = section['id']
        
        # Get measures for this section
        measures_query = """
        SELECT id, measure_number 
        FROM Measures 
        WHERE section_id = ? 
        ORDER BY measure_number
        """
        measures = db.execute_query(measures_query, (section['id'],))
        
        # For each measure, get chords
        for measure in measures:
            measure['measure_id'] = measure['id']
            
            chords_query = """
            SELECT id, chord_symbol, beat_position, chord_order, midi_notes,
                   chord_symbol_override, inversion, playback_octave, 
                   is_manual_edit, confidence, measure_id
            FROM Chords 
            WHERE measure_id = ? 
            ORDER BY chord_order
            """
            measure['chords'] = db.execute_query(chords_query, (measure['id'],))
        
        section['measures'] = measures
    
    return {"sections": sections}
