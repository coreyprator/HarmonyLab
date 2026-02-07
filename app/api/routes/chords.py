"""
API routes for chord management.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from pydantic import BaseModel
from app.models import Chord, ChordCreate
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

    db = DatabaseConnection(settings)

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
        id=row['id'],
        measure_id=row['measure_id'],
        beat_position=row['beat_position'],
        chord_symbol=row['chord_symbol'],
        roman_numeral=row['roman_numeral'],
        key_center=row['key_center'],
        function_label=row['function_label'],
        comments=row['comments'],
        chord_order=row['chord_order']
    )


@router.post("/bulk", response_model=List[Chord], status_code=status.HTTP_201_CREATED)
async def create_chords_bulk(bulk_data: BulkChordCreate):
    """Create multiple chords at once (for imports)."""

    db = DatabaseConnection(settings)
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
                id=row['id'],
                measure_id=row['measure_id'],
                beat_position=row['beat_position'],
                chord_symbol=row['chord_symbol'],
                roman_numeral=row['roman_numeral'],
                key_center=row['key_center'],
                function_label=row['function_label'],
                comments=row['comments'],
                chord_order=row['chord_order']
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
        id=row['id'],
        measure_id=row['measure_id'],
        beat_position=row['beat_position'],
        chord_symbol=row['chord_symbol'],
        roman_numeral=row['roman_numeral'],
        key_center=row['key_center'],
        function_label=row['function_label'],
        comments=row['comments'],
        chord_order=row['chord_order']
    )


@router.get("/measure/{measure_id}", response_model=List[Chord])
async def get_measure_chords(measure_id: int):
    """List all chords in a measure."""

    db = DatabaseConnection(settings)

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
            id=row['id'],
            measure_id=row['measure_id'],
            beat_position=row['beat_position'],
            chord_symbol=row['chord_symbol'],
            roman_numeral=row['roman_numeral'],
            key_center=row['key_center'],
            function_label=row['function_label'],
            comments=row['comments'],
            chord_order=row['chord_order']
        ))

    return chords


@router.put("/{chord_id}", response_model=Chord)
async def update_chord(chord_id: int, chord_update: ChordCreate):
    """Update a chord."""

    db = DatabaseConnection(settings)

    # Check if chord exists
    check_query = "SELECT COUNT(*) FROM Chords WHERE id = ?"
    count = db.execute_scalar(check_query, (chord_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chord with id {chord_id} not found"
        )

    # Update chord
    query = """
        UPDATE Chords
        SET measure_id = ?, beat_position = ?, chord_symbol = ?, roman_numeral = ?,
            key_center = ?, function_label = ?, comments = ?, chord_order = ?
        WHERE id = ?
    """

    db.execute_non_query(query, (
        chord_update.measure_id,
        float(chord_update.beat_position),
        chord_update.chord_symbol,
        chord_update.roman_numeral,
        chord_update.key_center,
        chord_update.function_label,
        chord_update.comments,
        chord_update.chord_order,
        chord_id
    ))

    # Return updated chord
    select_query = """
        SELECT id, measure_id, beat_position, chord_symbol, roman_numeral,
               key_center, function_label, comments, chord_order
        FROM Chords
        WHERE id = ?
    """
    result = db.execute_query(select_query, (chord_id,))
    row = result[0]

    return Chord(
        id=row['id'],
        measure_id=row['measure_id'],
        beat_position=row['beat_position'],
        chord_symbol=row['chord_symbol'],
        roman_numeral=row['roman_numeral'],
        key_center=row['key_center'],
        function_label=row['function_label'],
        comments=row['comments'],
        chord_order=row['chord_order']
    )


@router.delete("/{chord_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chord(chord_id: int):
    """Delete a chord."""

    db = DatabaseConnection(settings)

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
