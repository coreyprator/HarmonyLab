"""
API routes for chord management.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from pydantic import BaseModel
from app.models import Chord, ChordCreate
from app.db.connection import DatabaseConnection, get_db

router = APIRouter(prefix="/api/v1/chords", tags=["chords"])

# Columns shared by all SELECT queries — includes HM44 A2/A3 fields
_CHORD_COLS = """
    id, measure_id, beat_position, chord_symbol, roman_numeral,
    key_center, function_label, comments, chord_order,
    COALESCE(is_inferred, 0) AS is_inferred,
    voicing_notation
"""


def _row_to_chord(row: dict) -> Chord:
    """Map a DB row dict to a Chord model."""
    return Chord(
        id=row['id'],
        measure_id=row['measure_id'],
        beat_position=row['beat_position'],
        chord_symbol=row['chord_symbol'],
        roman_numeral=row['roman_numeral'],
        key_center=row['key_center'],
        function_label=row['function_label'],
        comments=row['comments'],
        chord_order=row['chord_order'],
        is_inferred=bool(row.get('is_inferred', 0)),
        voicing_notation=row.get('voicing_notation'),
    )


class BulkChordCreate(BaseModel):
    """Model for bulk chord creation."""
    chords: List[ChordCreate]


@router.post("/", response_model=Chord, status_code=status.HTTP_201_CREATED)
async def create_chord(chord: ChordCreate, db: DatabaseConnection = Depends(get_db)):
    """Create a new chord in a measure.

    BUG-039 fix: uses execute_insert (INSERT + SCOPE_IDENTITY() on same connection)
    instead of INSERT...OUTPUT INSERTED so the ID read-back is always reliable.
    """
    count = db.execute_scalar("SELECT COUNT(*) FROM Measures WHERE id = ?", (chord.measure_id,))
    if count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Measure with id {chord.measure_id} not found")

    new_id = db.execute_insert(
        """INSERT INTO Chords (measure_id, beat_position, chord_symbol, roman_numeral,
                               key_center, function_label, comments, chord_order,
                               is_inferred, voicing_notation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            chord.measure_id, float(chord.beat_position), chord.chord_symbol,
            chord.roman_numeral, chord.key_center, chord.function_label,
            chord.comments, chord.chord_order,
            1 if chord.is_inferred else 0, chord.voicing_notation,
        ),
    )
    if not new_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create chord")

    result = db.execute_query(f"SELECT {_CHORD_COLS} FROM Chords WHERE id = ?", (new_id,))
    return _row_to_chord(result[0])


@router.post("/bulk", response_model=List[Chord], status_code=status.HTTP_201_CREATED)
async def create_chords_bulk(bulk_data: BulkChordCreate, db: DatabaseConnection = Depends(get_db)):
    """Create multiple chords at once (for imports).

    BUG-039 fix: uses execute_insert for reliable ID read-back.
    """
    created_chords = []

    for chord in bulk_data.chords:
        count = db.execute_scalar("SELECT COUNT(*) FROM Measures WHERE id = ?", (chord.measure_id,))
        if count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Measure with id {chord.measure_id} not found")

        new_id = db.execute_insert(
            """INSERT INTO Chords (measure_id, beat_position, chord_symbol, roman_numeral,
                                   key_center, function_label, comments, chord_order,
                                   is_inferred, voicing_notation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chord.measure_id, float(chord.beat_position), chord.chord_symbol,
                chord.roman_numeral, chord.key_center, chord.function_label,
                chord.comments, chord.chord_order,
                1 if chord.is_inferred else 0, chord.voicing_notation,
            ),
        )
        if new_id:
            result = db.execute_query(f"SELECT {_CHORD_COLS} FROM Chords WHERE id = ?", (new_id,))
            if result:
                created_chords.append(_row_to_chord(result[0]))

    return created_chords


@router.get("/measure/{measure_id}", response_model=List[Chord])
async def get_measure_chords(measure_id: int, db: DatabaseConnection = Depends(get_db)):
    """List all chords in a measure."""
    count = db.execute_scalar("SELECT COUNT(*) FROM Measures WHERE id = ?", (measure_id,))
    if count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Measure with id {measure_id} not found")

    result = db.execute_query(
        f"SELECT {_CHORD_COLS} FROM Chords WHERE measure_id = ? ORDER BY chord_order",
        (measure_id,),
    )
    return [_row_to_chord(r) for r in result] if result else []


@router.get("/{chord_id}", response_model=Chord)
async def get_chord(chord_id: int, db: DatabaseConnection = Depends(get_db)):
    """Get a single chord."""
    result = db.execute_query(f"SELECT {_CHORD_COLS} FROM Chords WHERE id = ?", (chord_id,))
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Chord with id {chord_id} not found")
    return _row_to_chord(result[0])


@router.put("/{chord_id}", response_model=Chord)
async def update_chord(chord_id: int, chord_update: ChordCreate,
                       db: DatabaseConnection = Depends(get_db)):
    """Update a chord — including HM44 A3 voicing_notation and A2 is_inferred."""
    existing = db.execute_query(f"SELECT {_CHORD_COLS} FROM Chords WHERE id = ?", (chord_id,))
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Chord with id {chord_id} not found")

    # HM47 BUG-049: guard against FK_Chords_Measures — keep existing measure_id
    # if the incoming one doesn't resolve to a real Measures row
    measure_id_to_use = chord_update.measure_id
    if measure_id_to_use != existing[0]['measure_id']:
        m_exists = db.execute_scalar("SELECT COUNT(*) FROM Measures WHERE id = ?", (measure_id_to_use,))
        if not m_exists:
            measure_id_to_use = existing[0]['measure_id']

    db.execute_non_query(
        """UPDATE Chords
           SET measure_id = ?, beat_position = ?, chord_symbol = ?, roman_numeral = ?,
               key_center = ?, function_label = ?, comments = ?, chord_order = ?,
               is_inferred = ?, voicing_notation = ?
           WHERE id = ?""",
        (
            measure_id_to_use, float(chord_update.beat_position),
            chord_update.chord_symbol, chord_update.roman_numeral,
            chord_update.key_center, chord_update.function_label,
            chord_update.comments, chord_update.chord_order,
            1 if chord_update.is_inferred else 0, chord_update.voicing_notation,
            chord_id,
        ),
    )

    result = db.execute_query(f"SELECT {_CHORD_COLS} FROM Chords WHERE id = ?", (chord_id,))
    return _row_to_chord(result[0])


@router.delete("/{chord_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chord(chord_id: int, db: DatabaseConnection = Depends(get_db)):
    """Delete a chord."""
    count = db.execute_scalar("SELECT COUNT(*) FROM Chords WHERE id = ?", (chord_id,))
    if count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Chord with id {chord_id} not found")
    db.execute_non_query("DELETE FROM Chords WHERE id = ?", (chord_id,))
