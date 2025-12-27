"""
API routes for file imports (MIDI and MusicXML).
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import Optional
import tempfile
import os
from app.services.midi_parser import parse_midi_file, ParsedSong
from app.models import SongCreate, SectionCreate, MeasureCreate, ChordCreate
from app.db.connection import DatabaseConnection
from config.settings import Settings

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])
settings = Settings()


@router.post("/midi/preview")
async def preview_midi(file: UploadFile = File(...)):
    """
    Upload and parse a MIDI file to preview the extracted data.
    Does not save to database yet.
    """
    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a MIDI file (.mid or .midi)"
        )
    
    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Parse the MIDI file
        parsed_song = parse_midi_file(tmp_path)
        
        return {
            "filename": file.filename,
            "title": parsed_song.title or file.filename.replace('.mid', '').replace('.midi', ''),
            "tempo": parsed_song.tempo,
            "time_signature": parsed_song.time_signature,
            "total_measures": parsed_song.total_measures,
            "chord_count": len(parsed_song.chords),
            "chords_preview": [
                {
                    "measure": chord.measure_number,
                    "beat": chord.beat_position,
                    "symbol": chord.chord_symbol
                }
                for chord in parsed_song.chords[:20]  # Show first 20 chords
            ],
            "all_chords": [
                {
                    "measure": chord.measure_number,
                    "beat": chord.beat_position,
                    "symbol": chord.chord_symbol,
                    "midi_notes": chord.midi_notes
                }
                for chord in parsed_song.chords
            ]
        }
    
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/midi/import")
async def import_midi(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    composer: Optional[str] = None,
    genre: Optional[str] = None
):
    """
    Import a MIDI file and save the parsed data to the database.
    Creates song, sections, measures, and chords.
    """
    if not file.filename.endswith(('.mid', '.midi')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a MIDI file (.mid or .midi)"
        )
    
    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Parse the MIDI file
        parsed_song = parse_midi_file(tmp_path)
        
        db = DatabaseConnection(settings)
        
        # Create the song
        song_title = title or parsed_song.title or file.filename.replace('.mid', '').replace('.midi', '')
        
        song_query = """
            INSERT INTO Songs (title, composer, genre, time_signature, tempo_marking,
                               source_file_name, source_file_type)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, 'MIDI')
        """
        
        tempo_str = f"{parsed_song.tempo} BPM" if parsed_song.tempo else None
        song_result = db.execute_query(
            song_query,
            (song_title, composer, genre, parsed_song.time_signature, tempo_str, file.filename)
        )
        song_id = song_result[0][0]
        
        # Create a single section (MIDI files usually don't have section markers)
        section_query = """
            INSERT INTO Sections (song_id, name, section_order, repeat_count)
            OUTPUT INSERTED.id
            VALUES (?, 'Main', 1, 1)
        """
        section_result = db.execute_query(section_query, (song_id,))
        section_id = section_result[0][0]
        
        # Create measures and chords
        measures_created = {}
        
        for chord_data in parsed_song.chords:
            measure_num = chord_data.measure_number
            
            # Create measure if it doesn't exist
            if measure_num not in measures_created:
                measure_query = """
                    INSERT INTO Measures (section_id, measure_number)
                    OUTPUT INSERTED.id
                    VALUES (?, ?)
                """
                measure_result = db.execute_query(measure_query, (section_id, measure_num))
                measures_created[measure_num] = measure_result[0][0]
            
            measure_id = measures_created[measure_num]
            
            # Determine chord order within the measure
            chord_order = len([c for c in parsed_song.chords 
                             if c.measure_number == measure_num 
                             and parsed_song.chords.index(c) <= parsed_song.chords.index(chord_data)])
            
            # Create chord
            chord_query = """
                INSERT INTO Chords (measure_id, beat_position, chord_symbol, chord_order)
                VALUES (?, ?, ?, ?)
            """
            db.execute_non_query(
                chord_query,
                (measure_id, chord_data.beat_position, chord_data.chord_symbol, chord_order)
            )
        
        return {
            "success": True,
            "song_id": song_id,
            "title": song_title,
            "measures_created": len(measures_created),
            "chords_created": len(parsed_song.chords),
            "message": f"Successfully imported '{song_title}' with {len(parsed_song.chords)} chords"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import MIDI file: {str(e)}"
        )
    
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/musicxml/preview")
async def preview_musicxml(file: UploadFile = File(...)):
    """
    Upload and parse a MusicXML file to preview the extracted data.
    (Not yet implemented - placeholder for future development)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MusicXML import is not yet implemented. Coming in Sprint 3!"
    )


@router.post("/musicxml/import")
async def import_musicxml(file: UploadFile = File(...)):
    """
    Import a MusicXML file and save to database.
    (Not yet implemented - placeholder for future development)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="MusicXML import is not yet implemented. Coming in Sprint 3!"
    )
