"""
API routes for measure management.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from app.models import Measure, MeasureCreate, MeasureWithChords, Chord
from app.db.connection import DatabaseConnection
from config.settings import Settings

router = APIRouter(prefix="/api/v1/measures", tags=["measures"])
settings = Settings()


@router.post("/", response_model=Measure, status_code=status.HTTP_201_CREATED)
async def create_measure(measure: MeasureCreate):
    """Create a new measure in a section."""
    
    db = DatabaseConnection(settings)
    
    # Check if section exists
    check_query = "SELECT COUNT(*) FROM Sections WHERE id = ?"
    count = db.execute_scalar(check_query, (measure.section_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section with id {measure.section_id} not found"
        )
    
    # Insert measure
    query = """
        INSERT INTO Measures (section_id, measure_number)
        OUTPUT INSERTED.id, INSERTED.section_id, INSERTED.measure_number, INSERTED.created_at
        VALUES (?, ?)
    """
    
    result = db.execute_query(query, (measure.section_id, measure.measure_number))
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create measure"
        )
    
    row = result[0]
    return Measure(
        id=row[0],
        section_id=row[1],
        measure_number=row[2],
        created_at=row[3]
    )


@router.get("/{measure_id}", response_model=MeasureWithChords)
async def get_measure(measure_id: int):
    """Get a single measure with its chords."""
    
    db = DatabaseConnection(settings)
    
    # Get measure
    measure_query = """
        SELECT id, section_id, measure_number, created_at
        FROM Measures
        WHERE id = ?
    """
    measure_result = db.execute_query(measure_query, (measure_id,))
    
    if not measure_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Measure with id {measure_id} not found"
        )
    
    row = measure_result[0]
    measure = Measure(
        id=row[0],
        section_id=row[1],
        measure_number=row[2],
        created_at=row[3]
    )
    
    # Get chords for this measure
    chords_query = """
        SELECT id, measure_id, beat_position, chord_symbol, roman_numeral,
               key_center, function_label, comments, chord_order
        FROM Chords
        WHERE measure_id = ?
        ORDER BY chord_order
    """
    chords_result = db.execute_query(chords_query, (measure_id,))
    
    chords = []
    if chords_result:
        for chord_row in chords_result:
            chords.append(Chord(
                id=chord_row[0],
                measure_id=chord_row[1],
                beat_position=chord_row[2],
                chord_symbol=chord_row[3],
                roman_numeral=chord_row[4],
                key_center=chord_row[5],
                function_label=chord_row[6],
                comments=chord_row[7],
                chord_order=chord_row[8]
            ))
    
    return MeasureWithChords(
        id=measure.id,
        section_id=measure.section_id,
        measure_number=measure.measure_number,
        created_at=measure.created_at,
        chords=chords
    )


@router.get("/section/{section_id}", response_model=List[MeasureWithChords])
async def get_section_measures(section_id: int):
    """List all measures in a section with their chords."""
    
    db = DatabaseConnection(settings)
    
    # Check if section exists
    check_query = "SELECT COUNT(*) FROM Sections WHERE id = ?"
    count = db.execute_scalar(check_query, (section_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section with id {section_id} not found"
        )
    
    # Get all measures for the section
    measures_query = """
        SELECT id, section_id, measure_number, created_at
        FROM Measures
        WHERE section_id = ?
        ORDER BY measure_number
    """
    measures_result = db.execute_query(measures_query, (section_id,))
    
    if not measures_result:
        return []
    
    measures = []
    for row in measures_result:
        measure_id = row[0]
        
        # Get chords for this measure
        chords_query = """
            SELECT id, measure_id, beat_position, chord_symbol, roman_numeral,
                   key_center, function_label, comments, chord_order
            FROM Chords
            WHERE measure_id = ?
            ORDER BY chord_order
        """
        chords_result = db.execute_query(chords_query, (measure_id,))
        
        chords = []
        if chords_result:
            for chord_row in chords_result:
                chords.append(Chord(
                    id=chord_row[0],
                    measure_id=chord_row[1],
                    beat_position=chord_row[2],
                    chord_symbol=chord_row[3],
                    roman_numeral=chord_row[4],
                    key_center=chord_row[5],
                    function_label=chord_row[6],
                    comments=chord_row[7],
                    chord_order=chord_row[8]
                ))
        
        measures.append(MeasureWithChords(
            id=row[0],
            section_id=row[1],
            measure_number=row[2],
            created_at=row[3],
            chords=chords
        ))
    
    return measures


@router.put("/{measure_id}", response_model=Measure)
async def update_measure(measure_id: int, measure_update: MeasureCreate):
    """Update a measure's data."""
    
    db = DatabaseConnection(settings)
    
    # Check if measure exists
    check_query = "SELECT COUNT(*) FROM Measures WHERE id = ?"
    count = db.execute_scalar(check_query, (measure_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Measure with id {measure_id} not found"
        )
    
    # Update measure
    query = """
        UPDATE Measures
        SET section_id = ?, measure_number = ?
        WHERE id = ?
    """
    
    db.execute_non_query(query, (measure_update.section_id, measure_update.measure_number, measure_id))
    
    # Return updated measure
    select_query = """
        SELECT id, section_id, measure_number, created_at
        FROM Measures
        WHERE id = ?
    """
    result = db.execute_query(select_query, (measure_id,))
    row = result[0]
    
    return Measure(
        id=row[0],
        section_id=row[1],
        measure_number=row[2],
        created_at=row[3]
    )


@router.delete("/{measure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_measure(measure_id: int):
    """Delete a measure (cascades to chords)."""
    
    db = DatabaseConnection(settings)
    
    # Check if measure exists
    check_query = "SELECT COUNT(*) FROM Measures WHERE id = ?"
    count = db.execute_scalar(check_query, (measure_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Measure with id {measure_id} not found"
        )
    
    # Delete measure (chords will cascade)
    query = "DELETE FROM Measures WHERE id = ?"
    db.execute_non_query(query, (measure_id,))
