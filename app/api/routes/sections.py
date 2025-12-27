"""
Sections API Routes

Operations for song sections.
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from app.models import Section, SectionCreate
from app.db.connection import DatabaseConnection, get_db


router = APIRouter()


@router.get("/{song_id}/sections", response_model=List[Section])
async def get_song_sections(song_id: int, db: DatabaseConnection = Depends(get_db)):
    """Get all sections for a specific song."""
    query = """
    SELECT * FROM Sections 
    WHERE song_id = ? 
    ORDER BY section_order
    """
    return db.execute_query(query, (song_id,))


@router.post("/{song_id}/sections", response_model=Section, status_code=201)
async def create_section(
    song_id: int,
    section: SectionCreate,
    db: DatabaseConnection = Depends(get_db)
):
    """Create a new section for a song."""
    # Verify song exists
    song_exists = db.execute_scalar("SELECT COUNT(*) FROM Songs WHERE id = ?", (song_id,))
    if not song_exists:
        raise HTTPException(status_code=404, detail="Song not found")
    
    query = """
    INSERT INTO Sections (song_id, name, section_order, repeat_count, notes)
    OUTPUT INSERTED.id
    VALUES (?, ?, ?, ?, ?)
    """
    
    section_id = db.execute_scalar(
        query,
        (song_id, section.name, section.section_order, section.repeat_count, section.notes)
    )
    
    if not section_id:
        raise HTTPException(status_code=500, detail="Failed to create section")
    
    # Return created section
    result = db.execute_query("SELECT * FROM Sections WHERE id = ?", (section_id,))
    return result[0]


@router.delete("/{section_id}", status_code=204)
async def delete_section(section_id: int, db: DatabaseConnection = Depends(get_db)):
    """Delete a section (cascades to measures and chords)."""
    result = db.execute_non_query("DELETE FROM Sections WHERE id = ?", (section_id,))
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Section not found")
    
    return None
