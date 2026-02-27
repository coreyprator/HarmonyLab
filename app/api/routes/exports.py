"""
API routes for file exports: annotated MuseScore files.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from app.services.score_exporter import export_mscx, export_mscz
from app.services.analysis_service import analyze_song
from app.db.connection import DatabaseConnection, get_db
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/exports", tags=["exports"])


@router.get("/musescore/{song_id}")
async def export_musescore(
    song_id: int,
    format: str = Query(default="mscz", description="Export format: mscz or mscx"),
    include_analysis: bool = Query(default=True, description="Include Roman numerals and function colors"),
    db: DatabaseConnection = Depends(get_db),
):
    """Export a song as annotated MuseScore file.

    Generates a .mscx/.mscz file with chord symbols and optionally
    Roman numeral annotations color-coded by harmonic function.
    """
    # Fetch song metadata
    songs = db.execute_query(
        "SELECT id, title, composer, original_key, time_signature, tempo_marking FROM Songs WHERE id = ?",
        (song_id,)
    )
    if not songs:
        raise HTTPException(status_code=404, detail="Song not found")

    song = songs[0]
    title = song['title']
    composer = song.get('composer')
    key_str = song.get('original_key')
    time_sig = song.get('time_signature') or '4/4'

    # Parse tempo from "120 BPM" format
    tempo = None
    tempo_str = song.get('tempo_marking') or ''
    if tempo_str:
        import re
        tm = re.search(r'(\d+)', tempo_str)
        if tm:
            tempo = int(tm.group(1))

    # Fetch chords with measure/beat info
    chords_rows = db.execute_query("""
        SELECT c.chord_symbol, m.measure_number, c.beat_position, c.chord_order
        FROM Chords c
        JOIN Measures m ON c.measure_id = m.id
        JOIN Sections s ON m.section_id = s.id
        WHERE s.song_id = ?
        ORDER BY s.section_order, m.measure_number, c.chord_order
    """, (song_id,))

    if not chords_rows:
        raise HTTPException(status_code=404, detail="No chords found for this song")

    chords = [
        {
            "measure": c['measure_number'],
            "beat": float(c.get('beat_position') or 1.0),
            "symbol": c['chord_symbol'],
        }
        for c in chords_rows
    ]

    # Run or fetch analysis
    analysis = None
    if include_analysis:
        chord_symbols = [c['symbol'] for c in chords]
        try:
            # Check for cached analysis with key override
            cached = db.execute_query(
                "SELECT analysis_json, manual_key_override FROM SongAnalysis WHERE song_id = ?",
                (song_id,)
            )
            key_override = None
            if cached and cached[0].get('manual_key_override'):
                key_override = cached[0]['manual_key_override']

            analysis = analyze_song(chord_symbols, key_override)
            # Use detected key if no original_key
            if not key_str and analysis.get('detected_key'):
                key_str = analysis['detected_key']
        except Exception as e:
            logger.warning("Analysis failed for export of song %d: %s", song_id, e)

    # Generate export
    safe_title = ''.join(c for c in title if c.isalnum() or c in ' -_').strip() or 'export'

    if format == 'mscx':
        content = export_mscx(title, composer, key_str, time_sig, tempo, chords, analysis)
        return Response(
            content=content.encode('utf-8'),
            media_type='application/xml',
            headers={'Content-Disposition': f'attachment; filename="{safe_title}.mscx"'},
        )
    else:
        content = export_mscz(title, composer, key_str, time_sig, tempo, chords, analysis)
        return Response(
            content=content,
            media_type='application/zip',
            headers={'Content-Disposition': f'attachment; filename="{safe_title}.mscz"'},
        )
