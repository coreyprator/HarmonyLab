"""
API routes for file imports: MIDI, MusicXML, MuseScore, and batch imports.
Also includes a seed endpoint for jazz standards.
"""
import os
import io
import re
import hashlib
import time
import traceback
import zipfile
import tempfile
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Form
from fastapi.responses import JSONResponse
from app.services.score_parser import parse_music_file, ParsedScore, _DURATION_TO_BEATS
from app.services.midi_parser import parse_midi_file
from app.services.import_engine import parse_upload_full, save_full_parse
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

    # Save notes to MelodyNotes if available
    notes_saved = 0
    if hasattr(parsed, 'notes') and parsed.notes:
        for note in parsed.notes:
            try:
                dur_beats = _DURATION_TO_BEATS.get(note.duration_type, 1.0)
                db.execute_non_query(
                    "INSERT INTO MelodyNotes (song_id, measure_number, beat_position, midi_note, duration, velocity) VALUES (?, ?, ?, ?, ?, ?)",
                    (song_id, note.measure_number, note.beat_position, note.midi_pitch, dur_beats, 80)
                )
                notes_saved += 1
            except Exception as e:
                logger.debug("Note insert skip: %s", e)

    return {
        "song_id": song_id,
        "title": song_title,
        "measures_created": len(measures_created),
        "chords_created": len(parsed.chords),
        "notes_saved": notes_saved,
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


def _strip_version_suffix(title: str) -> str:
    """Strip version suffix like ' (2)', ' (3)' from title."""
    return re.sub(r'\s*\(\d+\)\s*$', '', title).strip()


def _compute_version(db: DatabaseConnection, base_title: str) -> int:
    """Compute the next version number for a given base title."""
    normalized = _strip_version_suffix(base_title).strip().lower()
    try:
        rows = db.execute_query(
            "SELECT COUNT(*) as cnt FROM Songs WHERE LOWER(LTRIM(RTRIM(COALESCE(base_title, title)))) = ?",
            (normalized,)
        )
        return (rows[0]['cnt'] if rows else 0) + 1
    except Exception:
        return 1


def _compute_file_hashes(content: bytes) -> dict:
    """Compute MD5 and SHA256 of file content."""
    return {
        'md5': hashlib.md5(content).hexdigest(),
        'sha256': hashlib.sha256(content).hexdigest(),
    }


def _check_duplicate_hash(db: DatabaseConnection, md5: str, base_title: str) -> Optional[str]:
    """Check if same file hash was already imported for this base title. Returns warning or None."""
    try:
        rows = db.execute_query(
            "SELECT si.id, si.uploaded_at FROM song_imports si "
            "JOIN Songs s ON si.song_id = s.id "
            "WHERE si.file_hash_md5 = ? AND LOWER(LTRIM(RTRIM(COALESCE(s.base_title, s.title)))) = ?",
            (md5, _strip_version_suffix(base_title).strip().lower())
        )
        if rows:
            r = rows[0]
            return f"File identical to import #{r['id']} on {r['uploaded_at']}. Proceeding anyway."
    except Exception:
        pass
    return None


def _create_import_record(db: DatabaseConnection, **kwargs) -> int:
    """Create a song_imports record and return its id."""
    try:
        result = db.execute_query("""
            INSERT INTO song_imports (
                song_id, original_filename, file_size_bytes, file_hash_md5, file_hash_sha256,
                fs_modified_at, import_format, parser_version, import_status,
                source_path, version_number
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            kwargs.get('song_id'),
            kwargs.get('original_filename', ''),
            kwargs.get('file_size_bytes'),
            kwargs.get('file_hash_md5'),
            kwargs.get('file_hash_sha256'),
            kwargs.get('fs_modified_at'),
            kwargs.get('import_format'),
            kwargs.get('parser_version', '2.5.0'),
            kwargs.get('import_status', 'pending'),
            kwargs.get('source_path'),
            kwargs.get('version_number', 1),
        ))
        return result[0]['id'] if result else 0
    except Exception as e:
        logger.warning("Failed to create import record: %s", e)
        return 0


def _update_import_record(db: DatabaseConnection, import_id: int, **kwargs):
    """Update a song_imports record with results."""
    if import_id <= 0:
        return
    sets = []
    params = []
    for key, val in kwargs.items():
        sets.append(f"{key} = ?")
        params.append(val)
    if not sets:
        return
    params.append(import_id)
    try:
        db.execute_non_query(
            f"UPDATE song_imports SET {', '.join(sets)} WHERE id = ?",
            tuple(params)
        )
    except Exception as e:
        logger.warning("Failed to update import record %d: %s", import_id, e)


# ---------------------------------------------------------------------------
# Note extraction for existing songs (FAIL 1)
# ---------------------------------------------------------------------------

@router.post("/score/reparse-notes")
async def reparse_notes(
    file: UploadFile = File(...),
    song_id: int = Query(..., description="Song ID to add notes to"),
):
    """Re-upload a .mscz/.mscx file to extract individual notes for an existing song.

    This endpoint parses the file for Note data only and stores in MelodyNotes.
    Useful for songs imported before note extraction was added.
    """
    ext = _ext(file.filename)
    if ext not in ('.mscz', '.mscx', '.musicxml', '.xml', '.mxl', '.mid', '.midi'):
        raise HTTPException(status_code=400, detail="File must be .mscz, .mscx, .musicxml, .mid, or .midi")

    db = DatabaseConnection(settings)

    # Verify song exists
    songs = db.execute_query("SELECT id, title FROM Songs WHERE id = ?", (song_id,))
    if not songs:
        raise HTTPException(status_code=404, detail=f"Song ID {song_id} not found")

    suffix = ext
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # Use the new rich import engine for full note extraction
        with open(tmp_path, 'rb') as f:
            file_bytes = f.read()
        rich_parsed = parse_upload_full(file_bytes, file.filename)
        rich_result = save_full_parse(song_id, rich_parsed, db)

        actual_notes = rich_result.get('actual_notes', 0)
        if actual_notes == 0:
            return {
                "song_id": song_id,
                "notes_count": 0,
                "message": "No note data found in this file. The file may not contain staff notation.",
            }

        return {
            "song_id": song_id,
            "notes_count": actual_notes,
            "lyrics_count": rich_result.get('lyrics_saved', 0),
            "message": f"Extracted {actual_notes} notes and {rich_result.get('lyrics_saved', 0)} lyrics for '{songs[0]['title']}'",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


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
    fs_modified_at: Optional[str] = Form(None),
    source_path: Optional[str] = Form(None),
):
    """Import any supported music file and save to database.

    Returns import_id, import_status, note_count, version_number.
    HTTP 200 on success, 207 on partial, 422 on total parse failure.
    """
    ext = _ext(file.filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    tmp_path = None
    t_start = time.monotonic()
    db = DatabaseConnection(settings)

    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Compute file hashes
        hashes = _compute_file_hashes(content)
        import_format = ext.lstrip('.')
        warnings_list = []

        # --- Parse with legacy parser (chords + metadata) ---
        parsed = parse_music_file(tmp_path, file.filename)
        source_type = {
            '.mscz': 'MuseScore', '.mscx': 'MuseScore',
            '.musicxml': 'MusicXML', '.xml': 'MusicXML', '.mxl': 'MusicXML',
            '.mid': 'MIDI', '.midi': 'MIDI',
        }.get(ext, 'Unknown')

        # --- Versioning ---
        song_title = title or parsed.title or os.path.splitext(file.filename)[0]
        base_title = _strip_version_suffix(song_title)
        version_num = _compute_version(db, base_title)
        if version_num > 1:
            song_title = f"{base_title} ({version_num})"

        # Check for duplicate file hash
        dup_warning = _check_duplicate_hash(db, hashes['md5'], base_title)
        if dup_warning:
            warnings_list.append(dup_warning)

        # --- Create song + chords (legacy path) ---
        result = _save_score_to_db(db, parsed, song_title, composer, genre, file.filename, source_type)
        song_id = result["song_id"]

        # Set base_title and version_number on the song
        try:
            db.execute_non_query(
                "UPDATE Songs SET base_title = ?, version_number = ? WHERE id = ?",
                (base_title, version_num, song_id)
            )
        except Exception as e:
            logger.debug("Could not set version fields: %s", e)

        # --- Create import provenance record ---
        import_id = _create_import_record(
            db,
            song_id=song_id,
            original_filename=file.filename,
            file_size_bytes=len(content),
            file_hash_md5=hashes['md5'],
            file_hash_sha256=hashes['sha256'],
            fs_modified_at=fs_modified_at,
            import_format=import_format,
            import_status='pending',
            source_path=source_path or '',
            version_number=version_num,
        )

        # --- Rich note extraction ---
        rich_result = None
        rich_error = None
        try:
            rich_parsed = parse_upload_full(content, file.filename)
            rich_result = save_full_parse(song_id, rich_parsed, db)
            logger.info("Rich import for song %d: %s", song_id, rich_result)
        except Exception as e:
            rich_error = traceback.format_exc()
            logger.error("Rich import failed for song %d: %s", song_id, e)

        # --- Determine import status ---
        note_count = rich_result['actual_notes'] if rich_result else 0
        lyric_count = rich_result.get('lyrics_saved', 0) if rich_result else 0
        chord_count = result["chords_created"]
        duration_ms = int((time.monotonic() - t_start) * 1000)

        if rich_result and note_count > 0:
            import_status = 'success'
        elif rich_result and note_count == 0 and chord_count > 0:
            import_status = 'partial'
            warnings_list.append("File parsed but no individual notes found. Chord symbols were saved.")
        elif rich_error:
            import_status = 'partial' if chord_count > 0 else 'failed'
        else:
            import_status = 'partial' if chord_count > 0 else 'failed'

        # --- Update import record ---
        _update_import_record(
            db, import_id,
            song_id=song_id,
            import_status=import_status,
            note_count_imported=note_count,
            lyric_count_imported=lyric_count,
            chord_count_imported=chord_count,
            import_duration_ms=duration_ms,
            import_error_log=rich_error,
            import_warnings='\n'.join(warnings_list) if warnings_list else None,
        )

        response_body = {
            "success": import_status in ('success', 'partial'),
            "song_id": song_id,
            "title": song_title,
            "version_number": version_num,
            "import_id": import_id,
            "import_status": import_status,
            "format": source_type,
            "measures_created": result["measures_created"],
            "chords_created": chord_count,
            "note_count": note_count,
            "lyric_count": lyric_count,
            "import_duration_ms": duration_ms,
            "warnings": warnings_list,
            "message": f"Imported '{song_title}' ({chord_count} chords, {note_count} notes)",
            "diagnostic": {
                "key_detected": parsed.key,
                "time_signature": parsed.time_signature,
            },
        }

        if import_status == 'failed':
            response_body["error"] = str(rich_error or "Parse produced no data")
            return JSONResponse(status_code=422, content=response_body)
        elif import_status == 'partial':
            return JSONResponse(status_code=207, content=response_body)
        else:
            return response_body

    except ValueError as e:
        duration_ms = int((time.monotonic() - t_start) * 1000)
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.monotonic() - t_start) * 1000)
        logger.exception("Error importing file %s", file.filename)
        # Try to record the failure
        try:
            _create_import_record(
                db,
                original_filename=file.filename or 'unknown',
                file_size_bytes=len(content) if 'content' in dir() else None,
                import_format=ext.lstrip('.') if ext else None,
                import_status='failed',
                import_error_log=traceback.format_exc(),
                import_duration_ms=duration_ms,
            )
        except Exception:
            pass
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
