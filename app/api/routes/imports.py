"""
API routes for file imports: MIDI, MusicXML, MuseScore, and batch imports.
Also includes a seed endpoint for jazz standards.
"""
import os
import io
import zipfile
import tempfile
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from app.services.score_parser import parse_music_file, ParsedScore
from app.services.midi_parser import parse_midi_file
from app.db.connection import DatabaseConnection
from config.settings import Settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/imports", tags=["imports"])
settings = Settings()

SUPPORTED_EXTENSIONS = {'.mid', '.midi', '.mscz', '.mscx', '.musicxml', '.xml', '.mxl'}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ext(filename: str) -> str:
    return os.path.splitext(filename.lower())[1]


def _save_score_to_db(
    db: DatabaseConnection,
    parsed: ParsedScore,
    title_override: Optional[str],
    composer: Optional[str],
    genre: Optional[str],
    source_filename: str,
    source_type: str,
) -> Dict[str, Any]:
    """Insert a ParsedScore into the database. Returns a summary dict."""
    song_title = title_override or parsed.title or os.path.splitext(source_filename)[0]

    song_query = """
        INSERT INTO Songs (title, composer, genre, original_key, time_signature,
                           tempo_marking, source_file_name, source_file_type)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    tempo_str = f"{parsed.tempo} BPM" if parsed.tempo else None
    song_result = db.execute_query(
        song_query,
        (song_title, composer, genre, parsed.key,
         parsed.time_signature, tempo_str, source_filename, source_type)
    )
    song_id = song_result[0]['id']

    section_query = """
        INSERT INTO Sections (song_id, name, section_order, repeat_count)
        OUTPUT INSERTED.id
        VALUES (?, 'Main', 1, 1)
    """
    section_result = db.execute_query(section_query, (song_id,))
    section_id = section_result[0]['id']

    measures_created: Dict[int, int] = {}
    for chord_data in parsed.chords:
        m = chord_data.measure_number
        if m not in measures_created:
            m_res = db.execute_query(
                "INSERT INTO Measures (section_id, measure_number) OUTPUT INSERTED.id VALUES (?, ?)",
                (section_id, m)
            )
            measures_created[m] = m_res[0]['id']
        measure_id = measures_created[m]
        db.execute_non_query(
            "INSERT INTO Chords (measure_id, beat_position, chord_symbol, chord_order) VALUES (?, ?, ?, ?)",
            (measure_id, chord_data.beat_position, chord_data.chord_symbol, chord_data.chord_order)
        )

    return {
        "song_id": song_id,
        "title": song_title,
        "measures_created": len(measures_created),
        "chords_created": len(parsed.chords),
    }


def _song_exists(db: DatabaseConnection, title: str, key: Optional[str]) -> bool:
    """Check if a song with the same title (and optionally key) already exists."""
    if key:
        rows = db.execute_query(
            "SELECT id FROM Songs WHERE title = ? AND original_key = ?", (title, key)
        )
    else:
        rows = db.execute_query("SELECT id FROM Songs WHERE title = ?", (title,))
    return len(rows) > 0


# ---------------------------------------------------------------------------
# Legacy MIDI endpoints (kept for backwards compatibility)
# ---------------------------------------------------------------------------

@router.post("/midi/preview")
async def preview_midi(file: UploadFile = File(...)):
    """Preview a MIDI file without saving to database."""
    if _ext(file.filename) not in ('.mid', '.midi'):
        raise HTTPException(status_code=400, detail="File must be .mid or .midi")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        parsed = parse_midi_file(tmp_path)
        return {
            "filename": file.filename,
            "title": parsed.title or file.filename.rsplit('.', 1)[0],
            "tempo": parsed.tempo,
            "time_signature": parsed.time_signature,
            "total_measures": parsed.total_measures,
            "chord_count": len(parsed.chords),
            "chords_preview": [
                {"measure": c.measure_number, "beat": c.beat_position, "symbol": c.chord_symbol}
                for c in parsed.chords[:20]
            ],
            "all_chords": [
                {"measure": c.measure_number, "beat": c.beat_position,
                 "symbol": c.chord_symbol, "midi_notes": c.midi_notes}
                for c in parsed.chords
            ],
        }
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/midi/import")
async def import_midi(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    composer: Optional[str] = None,
    genre: Optional[str] = None,
):
    """Import a MIDI file and save to database."""
    if _ext(file.filename) not in ('.mid', '.midi'):
        raise HTTPException(status_code=400, detail="File must be .mid or .midi")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        parsed = parse_midi_file(tmp_path)
        db = DatabaseConnection(settings)

        from app.services.score_parser import ParsedScore, ScoreChord
        score = ParsedScore(
            title=parsed.title,
            key=None,
            time_signature=parsed.time_signature,
            tempo=parsed.tempo,
            chords=[
                ScoreChord(
                    measure_number=c.measure_number,
                    beat_position=c.beat_position,
                    chord_symbol=c.chord_symbol,
                    chord_order=i + 1,
                )
                for i, c in enumerate(parsed.chords)
            ],
        )
        result = _save_score_to_db(db, score, title, composer, genre, file.filename, 'MIDI')
        return {
            "success": True,
            "song_id": result["song_id"],
            "title": result["title"],
            "measures_created": result["measures_created"],
            "chords_created": result["chords_created"],
            "message": f"Successfully imported '{result['title']}' with {result['chords_created']} chords",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import MIDI: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# HL-014: Universal score import (all formats)
# ---------------------------------------------------------------------------

@router.post("/score/preview")
async def preview_score(file: UploadFile = File(...)):
    """Preview any supported music file (.mscz, .mscx, .musicxml, .mid) without saving."""
    ext = _ext(file.filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        parsed = parse_music_file(tmp_path, file.filename)
        format_label = {
            '.mscz': 'MuseScore', '.mscx': 'MuseScore XML',
            '.musicxml': 'MusicXML', '.xml': 'MusicXML', '.mxl': 'MusicXML',
            '.mid': 'MIDI', '.midi': 'MIDI',
        }.get(ext, ext.lstrip('.').upper())

        return {
            "filename": file.filename,
            "format": format_label,
            "title": parsed.title,
            "key": parsed.key,
            "time_signature": parsed.time_signature,
            "tempo": parsed.tempo,
            "chord_count": len(parsed.chords),
            "has_chord_symbols": len(parsed.chords) > 0,
            "chords_preview": [
                {"measure": c.measure_number, "beat": c.beat_position, "symbol": c.chord_symbol}
                for c in parsed.chords[:20]
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error previewing file %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/score/import")
async def import_score(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    composer: Optional[str] = None,
    genre: Optional[str] = None,
):
    """Import any supported music file and save to database."""
    ext = _ext(file.filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    tmp_path = None
    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        parsed = parse_music_file(tmp_path, file.filename)
        source_type = {
            '.mscz': 'MuseScore', '.mscx': 'MuseScore',
            '.musicxml': 'MusicXML', '.xml': 'MusicXML', '.mxl': 'MusicXML',
            '.mid': 'MIDI', '.midi': 'MIDI',
        }.get(ext, 'Unknown')

        db = DatabaseConnection(settings)
        result = _save_score_to_db(db, parsed, title, composer, genre, file.filename, source_type)

        chord_warning = ""
        if result["chords_created"] == 0:
            if ext in ('.mscz', '.mscx'):
                chord_warning = (
                    " MuseScore format partially supported: metadata imported, but no explicit "
                    "chord symbols (Harmony elements) found. If this score has written chord "
                    "symbols, ensure they are visible in MuseScore. Alternatively, export as "
                    ".mid from MuseScore for note-based chord analysis."
                )
            else:
                chord_warning = (
                    " No chord symbols found in this file — open the song and add analysis manually."
                )

        measures_with_chords = len(set(c.measure_number for c in parsed.chords)) if parsed.chords else 0

        return {
            "success": True,
            "song_id": result["song_id"],
            "title": result["title"],
            "format": source_type,
            "measures_created": result["measures_created"],
            "chords_created": result["chords_created"],
            "message": f"Imported '{result['title']}' ({result['chords_created']} chords){chord_warning}",
            "diagnostic": {
                "measures_with_chords": measures_with_chords,
                "chords_derived": result["chords_created"],
                "key_detected": parsed.key,
                "time_signature": parsed.time_signature,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error importing file %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Import failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# HL-018: Batch import (ZIP of music files or multi-file)
# ---------------------------------------------------------------------------

@router.post("/batch")
async def batch_import(
    file: UploadFile = File(...),
    composer: Optional[str] = None,
    genre: Optional[str] = None,
    skip_duplicates: bool = Query(default=True),
):
    """
    Batch import music files from a ZIP archive.

    The ZIP may contain any mix of .mscz, .mscx, .musicxml, .mid files.
    Files are processed sequentially. Duplicates (same title+key) are skipped
    unless skip_duplicates=false.

    Returns a summary: imported / skipped / failed counts and per-file details.
    """
    if _ext(file.filename) != '.zip':
        raise HTTPException(status_code=400, detail="Batch import requires a .zip file")

    zip_bytes = await file.read()
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes), 'r')
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive")

    music_files = [
        name for name in zf.namelist()
        if _ext(name) in SUPPORTED_EXTENSIONS and not name.startswith('__MACOSX')
    ]

    if not music_files:
        raise HTTPException(
            status_code=400,
            detail=f"No supported music files found in ZIP. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    db = DatabaseConnection(settings)
    results = {
        "total": len(music_files),
        "imported": 0,
        "skipped_duplicate": 0,
        "failed": 0,
        "files": [],
    }

    for name in music_files:
        base_name = os.path.basename(name)
        ext = _ext(base_name)
        file_result: Dict[str, Any] = {"filename": base_name, "status": "unknown"}

        tmp_path = None
        try:
            file_bytes = zf.read(name)
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            parsed = parse_music_file(tmp_path, base_name)

            if skip_duplicates and _song_exists(db, parsed.title, parsed.key):
                file_result["status"] = "skipped"
                file_result["reason"] = f"Duplicate: '{parsed.title}' already exists"
                results["skipped_duplicate"] += 1
            else:
                source_type = {
                    '.mscz': 'MuseScore', '.mscx': 'MuseScore',
                    '.musicxml': 'MusicXML', '.xml': 'MusicXML', '.mxl': 'MusicXML',
                    '.mid': 'MIDI', '.midi': 'MIDI',
                }.get(ext, 'Unknown')
                saved = _save_score_to_db(db, parsed, None, composer, genre, base_name, source_type)
                file_result["status"] = "imported"
                file_result["song_id"] = saved["song_id"]
                file_result["title"] = saved["title"]
                file_result["chords"] = saved["chords_created"]
                results["imported"] += 1

        except Exception as e:
            logger.warning("Batch import failed for %s: %s", base_name, e)
            file_result["status"] = "failed"
            file_result["error"] = str(e)
            results["failed"] += 1
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        results["files"].append(file_result)

    zf.close()

    summary = (f"Batch complete: {results['imported']} imported, "
               f"{results['skipped_duplicate']} skipped (duplicate), "
               f"{results['failed']} failed")
    results["summary"] = summary
    logger.info(summary)
    return results


# ---------------------------------------------------------------------------
# HL-008: Seed jazz standards directly into the database
# ---------------------------------------------------------------------------

# Well-known jazz standard chord progressions (single chorus, main changes).
# Format: list of (measure, beat, symbol) tuples — 1-indexed measure numbers.
_JAZZ_STANDARDS: List[Dict[str, Any]] = [
    {
        "title": "Autumn Leaves",
        "composer": "Joseph Kosma",
        "key": "G major",
        "time_signature": "4/4",
        "tempo": 120,
        "chords": [
            (1,1,"Cm7"),(2,1,"F7"),(3,1,"BbMaj7"),(4,1,"EbMaj7"),
            (5,1,"Am7b5"),(6,1,"D7"),(7,1,"Gm"),(8,1,"Gm"),
            (9,1,"Am7b5"),(10,1,"D7"),(11,1,"Gm"),(12,1,"Gm"),
            (13,1,"Cm7"),(14,1,"F7"),(15,1,"BbMaj7"),(16,1,"EbMaj7"),
            (17,1,"Am7b5"),(18,1,"D7"),(19,1,"Gm7"),(20,1,"C7"),
            (21,1,"Fm7"),(22,1,"Bb7"),(23,1,"EbMaj7"),(24,1,"EbMaj7"),
            (25,1,"Am7b5"),(26,1,"D7"),(27,1,"Gm"),(28,1,"Gm"),
            (29,1,"Am7b5"),(30,1,"D7"),(31,1,"Gm"),(32,1,"Gm"),
        ],
    },
    {
        "title": "All The Things You Are",
        "composer": "Jerome Kern",
        "key": "Ab major",
        "time_signature": "4/4",
        "tempo": 132,
        "chords": [
            (1,1,"Fm7"),(2,1,"Bbm7"),(3,1,"Eb7"),(4,1,"AbMaj7"),
            (5,1,"DbMaj7"),(6,1,"Dm7"),(7,1,"G7"),(8,1,"CMaj7"),
            (9,1,"CMaj7"),(10,1,"Cm7"),(11,1,"Fm7"),(12,1,"Bb7"),
            (13,1,"EbMaj7"),(14,1,"AbMaj7"),(15,1,"Am7b5"),(16,1,"D7b9"),
            (17,1,"GMaj7"),(18,1,"GMaj7"),(19,1,"Am7"),(20,1,"D7"),
            (21,1,"GMaj7"),(22,1,"GMaj7"),(23,1,"F#m7"),(24,1,"B7"),
            (25,1,"EMaj7"),(26,1,"C7"),(27,1,"Fm7"),(28,1,"Bbm7"),
            (29,1,"Eb7"),(30,1,"AbMaj7"),(31,1,"DbMaj7"),(32,1,"Gb7"),
            (33,1,"Cm7"),(34,1,"Bo7"),(35,1,"Bbm7"),(36,1,"Eb7"),
        ],
    },
    {
        "title": "Blue Bossa",
        "composer": "Kenny Dorham",
        "key": "C minor",
        "time_signature": "4/4",
        "tempo": 130,
        "chords": [
            (1,1,"Cm7"),(2,1,"Cm7"),(3,1,"Fm7"),(4,1,"Fm7"),
            (5,1,"Dm7b5"),(6,1,"G7b9"),(7,1,"Cm7"),(8,1,"Cm7"),
            (9,1,"Ebm7"),(10,1,"Ab7"),(11,1,"DbMaj7"),(12,1,"DbMaj7"),
            (13,1,"Dm7b5"),(14,1,"G7b9"),(15,1,"Cm7"),(16,1,"Cm7"),
        ],
    },
    {
        "title": "Fly Me To The Moon",
        "composer": "Bart Howard",
        "key": "C major",
        "time_signature": "3/4",
        "tempo": 144,
        "chords": [
            (1,1,"Am7"),(2,1,"Dm7"),(3,1,"G7"),(4,1,"CMaj7"),
            (5,1,"FMaj7"),(6,1,"Bm7b5"),(7,1,"E7"),(8,1,"Am7"),
            (9,1,"A7"),(10,1,"Dm7"),(11,1,"G7"),(12,1,"CMaj7"),
            (13,1,"CMaj7"),(14,1,"Bm7b5"),(15,1,"E7"),(16,1,"Am7"),
            (17,1,"Dm7"),(18,1,"G7"),(19,1,"Em7"),(20,1,"A7"),
            (21,1,"Dm7"),(22,1,"G7"),(23,1,"CMaj7"),(24,1,"CMaj7"),
        ],
    },
    {
        "title": "Take The A Train",
        "composer": "Billy Strayhorn",
        "key": "C major",
        "time_signature": "4/4",
        "tempo": 200,
        "chords": [
            (1,1,"CMaj7"),(2,1,"CMaj7"),(3,1,"D7"),(4,1,"D7"),
            (5,1,"Dm7"),(6,1,"G7"),(7,1,"CMaj7"),(8,1,"CMaj7"),
            (9,1,"CMaj7"),(10,1,"CMaj7"),(11,1,"D7"),(12,1,"D7"),
            (13,1,"Dm7"),(14,1,"G7"),(15,1,"CMaj7"),(16,1,"CMaj7"),
            (17,1,"CMaj7"),(18,1,"C7"),(19,1,"FMaj7"),(20,1,"FMaj7"),
            (21,1,"CMaj7"),(22,1,"CMaj7"),(23,1,"Dm7"),(24,1,"G7"),
            (25,1,"CMaj7"),(26,1,"CMaj7"),(27,1,"D7"),(28,1,"D7"),
            (29,1,"Dm7"),(30,1,"G7"),(31,1,"CMaj7"),(32,1,"CMaj7"),
        ],
    },
    {
        "title": "Misty",
        "composer": "Erroll Garner",
        "key": "Eb major",
        "time_signature": "4/4",
        "tempo": 76,
        "chords": [
            (1,1,"EbMaj7"),(2,1,"Bbm7"),(3,1,"Eb7"),(4,1,"AbMaj7"),
            (5,1,"Abm7"),(6,1,"Db7"),(7,1,"EbMaj7"),(7,3,"Cm7"),
            (8,1,"Fm7"),(8,3,"Bb7"),(9,1,"EbMaj7"),(10,1,"Bbm7"),
            (11,1,"Eb7"),(12,1,"AbMaj7"),(13,1,"Abm7"),(14,1,"Db7"),
            (15,1,"EbMaj7"),(15,3,"Cm7"),(16,1,"Fm7"),(16,3,"Bb7"),
            (17,1,"EbMaj7"),(18,1,"Bbm7"),(19,1,"Eb7"),(20,1,"AbMaj7"),
            (21,1,"Am7"),(21,3,"D7"),(22,1,"GMaj7"),(23,1,"Am7"),
            (23,3,"D7"),(24,1,"GMaj7"),(25,1,"Gm7"),(25,3,"C7"),
            (26,1,"FMaj7"),(27,1,"Fm7"),(27,3,"Bb7"),(28,1,"EbMaj7"),
            (29,1,"EbMaj7"),(30,1,"Bbm7"),(31,1,"Eb7"),(32,1,"AbMaj7"),
            (33,1,"Abm7"),(34,1,"Db7"),(35,1,"EbMaj7"),(35,3,"Cm7"),
            (36,1,"Fm7"),(36,3,"Bb7"),(37,1,"EbMaj7"),(38,1,"EbMaj7"),
        ],
    },
    {
        "title": "Summertime",
        "composer": "George Gershwin",
        "key": "A minor",
        "time_signature": "4/4",
        "tempo": 60,
        "chords": [
            (1,1,"Am"),(2,1,"E7"),(3,1,"Am"),(3,3,"Am7"),
            (4,1,"Dm"),(4,3,"Dm7"),(5,1,"Am"),(5,3,"F7"),
            (6,1,"E7"),(7,1,"Am"),(7,3,"E7"),(8,1,"Am"),
            (9,1,"Am"),(10,1,"E7"),(11,1,"Am"),(11,3,"Am7"),
            (12,1,"Dm"),(12,3,"Dm7"),(13,1,"Am"),(13,3,"F7"),
            (14,1,"E7"),(15,1,"Am"),(16,1,"Am"),
        ],
    },
    {
        "title": "Satin Doll",
        "composer": "Duke Ellington",
        "key": "C major",
        "time_signature": "4/4",
        "tempo": 120,
        "chords": [
            (1,1,"Dm7"),(1,3,"G7"),(2,1,"Dm7"),(2,3,"G7"),
            (3,1,"Em7"),(3,3,"A7"),(4,1,"Em7"),(4,3,"A7"),
            (5,1,"Am7"),(5,3,"D7"),(6,1,"Ab7"),(6,3,"Db7"),
            (7,1,"CMaj7"),(8,1,"CMaj7"),
            (9,1,"Dm7"),(9,3,"G7"),(10,1,"Dm7"),(10,3,"G7"),
            (11,1,"Em7"),(11,3,"A7"),(12,1,"Em7"),(12,3,"A7"),
            (13,1,"Am7"),(13,3,"D7"),(14,1,"Ab7"),(14,3,"Db7"),
            (15,1,"CMaj7"),(16,1,"CMaj7"),
            (17,1,"Gm7"),(17,3,"C7"),(18,1,"FMaj7"),(19,1,"FMaj7"),
            (20,1,"Am7"),(20,3,"D7"),(21,1,"GMaj7"),(22,1,"GMaj7"),
            (23,1,"Dm7"),(23,3,"G7"),(24,1,"Dm7"),(24,3,"G7"),
            (25,1,"Em7"),(25,3,"A7"),(26,1,"Em7"),(26,3,"A7"),
            (27,1,"Am7"),(27,3,"D7"),(28,1,"Ab7"),(28,3,"Db7"),
            (29,1,"CMaj7"),(30,1,"CMaj7"),
        ],
    },
    {
        "title": "So What",
        "composer": "Miles Davis",
        "key": "D dorian",
        "time_signature": "4/4",
        "tempo": 136,
        "chords": [
            (1,1,"Dm7"),(2,1,"Dm7"),(3,1,"Dm7"),(4,1,"Dm7"),
            (5,1,"Dm7"),(6,1,"Dm7"),(7,1,"Dm7"),(8,1,"Dm7"),
            (9,1,"Dm7"),(10,1,"Dm7"),(11,1,"Dm7"),(12,1,"Dm7"),
            (13,1,"Dm7"),(14,1,"Dm7"),(15,1,"Dm7"),(16,1,"Dm7"),
            (17,1,"Ebm7"),(18,1,"Ebm7"),(19,1,"Ebm7"),(20,1,"Ebm7"),
            (21,1,"Ebm7"),(22,1,"Ebm7"),(23,1,"Ebm7"),(24,1,"Ebm7"),
            (25,1,"Dm7"),(26,1,"Dm7"),(27,1,"Dm7"),(28,1,"Dm7"),
            (29,1,"Dm7"),(30,1,"Dm7"),(31,1,"Dm7"),(32,1,"Dm7"),
        ],
    },
    {
        "title": "Wave",
        "composer": "Antonio Carlos Jobim",
        "key": "D major",
        "time_signature": "4/4",
        "tempo": 116,
        "chords": [
            (1,1,"DMaj7"),(2,1,"E7"),(3,1,"Em7"),(3,3,"A7"),
            (4,1,"DMaj7"),(5,1,"G#m7"),(5,3,"C#7"),(6,1,"F#m7"),
            (7,1,"B7"),(8,1,"Em7"),(8,3,"A7"),(9,1,"DMaj7"),
            (10,1,"Am7"),(10,3,"D7"),(11,1,"GMaj7"),
            (12,1,"Gm7"),(12,3,"C7"),(13,1,"DMaj7"),(14,1,"F#m7"),
            (14,3,"B7"),(15,1,"Em7"),(16,1,"A7"),
            (17,1,"DMaj7"),(18,1,"E7"),(19,1,"Em7"),(19,3,"A7"),
            (20,1,"DMaj7"),(21,1,"G#m7"),(21,3,"C#7"),(22,1,"F#m7"),
            (23,1,"B7"),(24,1,"Em7"),(24,3,"A7"),(25,1,"DMaj7"),
        ],
    },
    {
        "title": "Maiden Voyage",
        "composer": "Herbie Hancock",
        "key": "D major",
        "time_signature": "4/4",
        "tempo": 112,
        "chords": [
            (1,1,"D7sus"),(2,1,"D7sus"),(3,1,"D7sus"),(4,1,"D7sus"),
            (5,1,"F7sus"),(6,1,"F7sus"),(7,1,"F7sus"),(8,1,"F7sus"),
            (9,1,"Eb7sus"),(10,1,"Eb7sus"),(11,1,"Eb7sus"),(12,1,"Eb7sus"),
            (13,1,"C7sus"),(14,1,"C7sus"),(15,1,"C7sus"),(16,1,"C7sus"),
        ],
    },
    {
        "title": "Watermelon Man",
        "composer": "Herbie Hancock",
        "key": "F major",
        "time_signature": "4/4",
        "tempo": 126,
        "chords": [
            (1,1,"F7"),(2,1,"F7"),(3,1,"Bb7"),(4,1,"Bb7"),
            (5,1,"F7"),(6,1,"F7"),(7,1,"F7"),(8,1,"F7"),
            (9,1,"Bb7"),(10,1,"Bb7"),(11,1,"F7"),(12,1,"F7"),
            (13,1,"Cm7"),(14,1,"Bb7"),(15,1,"F7"),(16,1,"F7"),
        ],
    },
    {
        "title": "Round Midnight",
        "composer": "Thelonious Monk",
        "key": "Bb minor",
        "time_signature": "4/4",
        "tempo": 60,
        "chords": [
            (1,1,"Ebm7"),(2,1,"Bbm"),(3,1,"Fm7"),(3,3,"Bb7"),
            (4,1,"Ebm"),(5,1,"Ebm7"),(5,3,"Ab7"),(6,1,"DbMaj7"),
            (7,1,"Dm7b5"),(7,3,"G7b9"),(8,1,"Cm7"),(8,3,"F7"),
            (9,1,"Bbm"),(10,1,"Bbm"),(11,1,"Cm7b5"),(11,3,"F7b9"),
            (12,1,"Bbm"),(13,1,"Dm7b5"),(13,3,"G7b9"),(14,1,"Cm7b5"),
            (14,3,"F7b9"),(15,1,"Bbm"),(16,1,"Bbm"),
        ],
    },
    {
        "title": "Footprints",
        "composer": "Wayne Shorter",
        "key": "C minor",
        "time_signature": "6/4",
        "tempo": 100,
        "chords": [
            (1,1,"Cm7"),(2,1,"Cm7"),(3,1,"Fm7"),(4,1,"Cm7"),
            (5,1,"Ab7"),(6,1,"G7"),(7,1,"Cm7"),(8,1,"Cm7"),
        ],
    },
    {
        "title": "There Will Never Be Another You",
        "composer": "Harry Warren",
        "key": "Eb major",
        "time_signature": "4/4",
        "tempo": 140,
        "chords": [
            (1,1,"EbMaj7"),(2,1,"EbMaj7"),(3,1,"Fm7"),(3,3,"Bb7"),
            (4,1,"EbMaj7"),(5,1,"Fm7b5"),(5,3,"Bb7"),(6,1,"EbMaj7"),
            (7,1,"Cm7"),(7,3,"F7"),(8,1,"Fm7"),(8,3,"Bb7"),
            (9,1,"Gm7"),(9,3,"C7"),(10,1,"Fm7"),(10,3,"Bb7"),
            (11,1,"EbMaj7"),(12,1,"EbMaj7"),(13,1,"Fm7"),(13,3,"Bb7"),
            (14,1,"EbMaj7"),(15,1,"Dm7b5"),(15,3,"G7"),(16,1,"Cm7"),
            (17,1,"Cm7"),(17,3,"F7"),(18,1,"Fm7"),(18,3,"Bb7"),
            (19,1,"EbMaj7"),(20,1,"EbMaj7"),
        ],
    },
]


@router.post("/seed-standards")
async def seed_jazz_standards(
    skip_duplicates: bool = Query(default=True),
):
    """
    Seed the database with well-known jazz standard chord progressions.

    This endpoint generates structured chord data from built-in progressions
    and inserts them directly — no file upload needed. Safe to call multiple
    times (skip_duplicates=true by default).
    """
    db = DatabaseConnection(settings)
    results = {"total": len(_JAZZ_STANDARDS), "imported": 0, "skipped": 0, "songs": []}

    for std in _JAZZ_STANDARDS:
        title = std["title"]
        key = std.get("key")

        if skip_duplicates and _song_exists(db, title, key):
            results["skipped"] += 1
            results["songs"].append({"title": title, "status": "skipped"})
            continue

        try:
            # Insert song
            song_q = """
                INSERT INTO Songs (title, composer, genre, original_key, time_signature,
                                   tempo_marking, source_file_name, source_file_type)
                OUTPUT INSERTED.id
                VALUES (?, ?, 'Jazz', ?, ?, ?, ?, 'Seeded')
            """
            tempo_str = f"{std['tempo']} BPM" if std.get("tempo") else None
            song_res = db.execute_query(
                song_q,
                (title, std.get("composer"), key,
                 std.get("time_signature", "4/4"), tempo_str,
                 f"{title}.seed")
            )
            song_id = song_res[0]['id']

            # Section
            sec_res = db.execute_query(
                "INSERT INTO Sections (song_id, name, section_order, repeat_count) OUTPUT INSERTED.id VALUES (?, 'Main', 1, 1)",
                (song_id,)
            )
            section_id = sec_res[0]['id']

            # Group chords by measure
            measures: Dict[int, int] = {}
            chord_count = 0
            measure_chord_order: Dict[int, int] = {}

            for measure_num, beat, symbol in std["chords"]:
                if measure_num not in measures:
                    m_res = db.execute_query(
                        "INSERT INTO Measures (section_id, measure_number) OUTPUT INSERTED.id VALUES (?, ?)",
                        (section_id, measure_num)
                    )
                    measures[measure_num] = m_res[0]['id']
                    measure_chord_order[measure_num] = 0

                measure_chord_order[measure_num] += 1
                measure_id = measures[measure_num]
                db.execute_non_query(
                    "INSERT INTO Chords (measure_id, beat_position, chord_symbol, chord_order) VALUES (?, ?, ?, ?)",
                    (measure_id, float(beat), symbol, measure_chord_order[measure_num])
                )
                chord_count += 1

            results["imported"] += 1
            results["songs"].append({
                "title": title,
                "status": "imported",
                "song_id": song_id,
                "chords": chord_count,
            })
            logger.info("Seeded jazz standard: %s (%d chords)", title, chord_count)

        except Exception as e:
            logger.exception("Failed to seed %s", title)
            results["songs"].append({"title": title, "status": "failed", "error": str(e)})

    results["summary"] = (
        f"Seeded {results['imported']} jazz standards, "
        f"skipped {results['skipped']} (already exist)"
    )
    return results
