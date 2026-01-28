"""
API routes for chord management.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from pydantic import BaseModel
from app.models import Chord, ChordCreate, ChordUpdate
from app.db.connection import DatabaseConnection
from config.settings import Settings

router = APIRouter(prefix="/api/v1/chords", tags=["chords"])
settings = Settings()


class BulkChordCreate(BaseModel):
    """Model for bulk chord creation."""
    chords: List[ChordCreate]


@router.post("/", response_model=Chord, status_code=status.HTTP_201_CREATED)
async def create_chord(chord: ChordCreate):
    """Create a new chord in a measure."""
    
    db = DatabaseConnection()
    
    # Check if measure exists
    check_query = "SELECT COUNT(*) FROM Measures WHERE id = ?"
    count = db.execute_scalar(check_query, (chord.measure_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Measure with id {chord.measure_id} not found"
        )
    
    # Insert chord
    query = """
        INSERT INTO Chords (measure_id, beat_position, chord_symbol, roman_numeral,
                            key_center, function_label, comments, chord_order)
        OUTPUT INSERTED.id, INSERTED.measure_id, INSERTED.beat_position,
               INSERTED.chord_symbol, INSERTED.roman_numeral, INSERTED.key_center,
               INSERTED.function_label, INSERTED.comments, INSERTED.chord_order
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    result = db.execute_query(query, (
        chord.measure_id,
        float(chord.beat_position),
        chord.chord_symbol,
        chord.roman_numeral,
        chord.key_center,
        chord.function_label,
        chord.comments,
        chord.chord_order
    ))
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chord"
        )
    
    row = result[0]
    return Chord(
        id=row[0],
        measure_id=row[1],
        beat_position=row[2],
        chord_symbol=row[3],
        roman_numeral=row[4],
        key_center=row[5],
        function_label=row[6],
        comments=row[7],
        chord_order=row[8]
    )


@router.post("/bulk", response_model=List[Chord], status_code=status.HTTP_201_CREATED)
async def create_chords_bulk(bulk_data: BulkChordCreate):
    """Create multiple chords at once (for imports)."""
    
    db = DatabaseConnection()
    created_chords = []
    
    for chord in bulk_data.chords:
        # Check if measure exists
        check_query = "SELECT COUNT(*) FROM Measures WHERE id = ?"
        count = db.execute_scalar(check_query, (chord.measure_id,))
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Measure with id {chord.measure_id} not found"
            )
        
        # Insert chord
        query = """
            INSERT INTO Chords (measure_id, beat_position, chord_symbol, roman_numeral,
                                key_center, function_label, comments, chord_order)
            OUTPUT INSERTED.id, INSERTED.measure_id, INSERTED.beat_position,
                   INSERTED.chord_symbol, INSERTED.roman_numeral, INSERTED.key_center,
                   INSERTED.function_label, INSERTED.comments, INSERTED.chord_order
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        result = db.execute_query(query, (
            chord.measure_id,
            float(chord.beat_position),
            chord.chord_symbol,
            chord.roman_numeral,
            chord.key_center,
            chord.function_label,
            chord.comments,
            chord.chord_order
        ))
        
        if result:
            row = result[0]
            created_chords.append(Chord(
                id=row[0],
                measure_id=row[1],
                beat_position=row[2],
                chord_symbol=row[3],
                roman_numeral=row[4],
                key_center=row[5],
                function_label=row[6],
                comments=row[7],
                chord_order=row[8]
            ))
    
    return created_chords


@router.get("/{chord_id}", response_model=Chord)
async def get_chord(chord_id: int):
    """Get a single chord."""
    
    db = DatabaseConnection(settings)
    
    query = """
        SELECT id, measure_id, beat_position, chord_symbol, roman_numeral,
               key_center, function_label, comments, chord_order
        FROM Chords
        WHERE id = ?
    """
    result = db.execute_query(query, (chord_id,))
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chord with id {chord_id} not found"
        )
    
    row = result[0]
    return Chord(
        id=row[0],
        measure_id=row[1],
        beat_position=row[2],
        chord_symbol=row[3],
        roman_numeral=row[4],
        key_center=row[5],
        function_label=row[6],
        comments=row[7],
        chord_order=row[8]
    )


@router.get("/measure/{measure_id}", response_model=List[Chord])
async def get_measure_chords(measure_id: int):
    """List all chords in a measure."""
    
    db = DatabaseConnection()
    
    # Check if measure exists
    check_query = "SELECT COUNT(*) FROM Measures WHERE id = ?"
    count = db.execute_scalar(check_query, (measure_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Measure with id {measure_id} not found"
        )
    
    query = """
        SELECT id, measure_id, beat_position, chord_symbol, roman_numeral,
               key_center, function_label, comments, chord_order
        FROM Chords
        WHERE measure_id = ?
        ORDER BY chord_order
    """
    result = db.execute_query(query, (measure_id,))
    
    if not result:
        return []
    
    chords = []
    for row in result:
        chords.append(Chord(
            id=row[0],
            measure_id=row[1],
            beat_position=row[2],
            chord_symbol=row[3],
            roman_numeral=row[4],
            key_center=row[5],
            function_label=row[6],
            comments=row[7],
            chord_order=row[8]
        ))
    
    return chords


@router.put("/{chord_id}", response_model=Chord)
async def update_chord(chord_id: int, chord_update: ChordUpdate):
    """Update a chord's symbol, inversion, octave, or other properties."""
    
    db = DatabaseConnection()
    
    # Check if chord exists
    check_query = "SELECT COUNT(*) FROM Chords WHERE id = ?"
    count = db.execute_scalar(check_query, (chord_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chord with id {chord_id} not found"
        )
    
    # Build dynamic UPDATE query based on provided fields
    update_fields = []
    params = []
    
    if chord_update.chord_symbol is not None:
        update_fields.append("chord_symbol = ?")
        params.append(chord_update.chord_symbol)
    
    if chord_update.chord_symbol_override is not None:
        update_fields.append("chord_symbol_override = ?")
        params.append(chord_update.chord_symbol_override)
    
    if chord_update.inversion is not None:
        update_fields.append("inversion = ?")
        params.append(chord_update.inversion)
    
    if chord_update.playback_octave is not None:
        update_fields.append("playback_octave = ?")
        params.append(chord_update.playback_octave)
    
    if chord_update.is_manual_edit is not None:
        update_fields.append("is_manual_edit = ?")
        params.append(1 if chord_update.is_manual_edit else 0)
    
    if chord_update.confidence is not None:
        update_fields.append("confidence = ?")
        params.append(float(chord_update.confidence))
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Update chord
    params.append(chord_id)
    query = f"""
        UPDATE Chords
        SET {', '.join(update_fields)}
        WHERE id = ?
    """
    
    db.execute_non_query(query, tuple(params))
    
    # Return updated chord
    select_query = """
        SELECT id, measure_id, beat_position, chord_symbol, roman_numeral,
               key_center, function_label, comments, chord_order,
               chord_symbol_override, inversion, playback_octave, 
               is_manual_edit, confidence
        FROM Chords
        WHERE id = ?
    """
    result = db.execute_query(select_query, (chord_id,))
    row = result[0]
    
    return Chord(
        id=row[0],
        measure_id=row[1],
        beat_position=row[2],
        chord_symbol=row[3],
        roman_numeral=row[4],
        key_center=row[5],
        function_label=row[6],
        comments=row[7],
        chord_order=row[8],
        chord_symbol_override=row[9],
        inversion=row[10] or 0,
        playback_octave=row[11] or 3,
        is_manual_edit=bool(row[12]) if row[12] is not None else False,
        confidence=row[13]
    )


@router.delete("/{chord_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chord(chord_id: int):
    """Delete a chord."""
    
    db = DatabaseConnection()
    
    # Check if chord exists
    check_query = "SELECT COUNT(*) FROM Chords WHERE id = ?"
    count = db.execute_scalar(check_query, (chord_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chord with id {chord_id} not found"
        )
    
    # Delete chord
    query = "DELETE FROM Chords WHERE id = ?"
    db.execute_non_query(query, (chord_id,))
