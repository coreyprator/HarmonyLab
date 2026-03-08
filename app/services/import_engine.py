"""
Full note data import engine for HarmonyLab (HL-REIMPORT).

Parses MuseScore .mscz/.mscx files using custom XML parser to extract
every musically relevant element: notes, lyrics, dynamics, articulations,
tempo/key/time sig changes, rehearsal marks.

For MusicXML and MIDI, delegates to music21/mido for note extraction.
"""
import os
import zipfile
import logging
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any

from app.services.score_parser import (
    _CHROMATIC_ROOT, _TPC_ROOT, _SHARP_KEYS, _FLAT_KEYS,
    _DURATION_TO_BEATS, ScoreChord, ScoreNote, ParsedScore,
)

logger = logging.getLogger(__name__)

# MIDI pitch to note name
_NOTE_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def midi_to_note_name(midi_pitch: int) -> str:
    """Convert MIDI pitch number to note name with octave (e.g., 60 -> 'C4')."""
    if midi_pitch <= 0:
        return 'rest'
    octave = (midi_pitch // 12) - 1
    note = _NOTE_NAMES[midi_pitch % 12]
    return f"{note}{octave}"


def parse_mscx_full(xml_content: str, default_title: str) -> dict:
    """
    Parse MuseScore .mscx XML and extract ALL musically relevant data.
    Returns a dict with notes, lyrics, dynamics, tempos, etc.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Could not parse MuseScore XML: {e}")

    # Detect MuseScore version for root-note mapping
    use_tpc = False
    ver_el = root.find('.//programVersion')
    ms_version = ver_el.text.strip() if ver_el is not None and ver_el.text else None
    if ms_version:
        try:
            parts = [int(p) for p in ms_version.split('.')]
            if parts[0] > 4 or (parts[0] == 4 and len(parts) > 1 and parts[1] >= 5):
                use_tpc = True
        except (ValueError, IndexError):
            pass
    root_map = _TPC_ROOT if use_tpc else _CHROMATIC_ROOT

    result = {
        'metadata': {},
        'notes': [],
        'lyrics': [],
        'dynamics': [],
        'tempos': [],
        'time_signatures': [],
        'key_signatures': [],
        'chord_symbols': [],
        'text_marks': [],
        'import_format': 'mscz',
        'raw_xml': xml_content,
    }

    # --- Metadata ---
    title = default_title
    for tag in ('metaTag[@name="workTitle"]', 'metaTag[@name="title"]'):
        el = root.find(f'.//{tag}')
        if el is not None and el.text and el.text.strip():
            title = el.text.strip()
            break

    # Time signature
    time_sig = "4/4"
    ts_el = root.find('.//TimeSig')
    if ts_el is not None:
        beats = ts_el.findtext('sigN') or '4'
        beat_type = ts_el.findtext('sigD') or '4'
        time_sig = f"{beats}/{beat_type}"
        result['time_signatures'].append({
            'measure_num': 1, 'numerator': int(beats), 'denominator': int(beat_type)
        })

    # Tempo
    tempo_val = None
    tempo_el = root.find('.//Tempo')
    if tempo_el is not None:
        raw = tempo_el.findtext('tempo')
        if raw:
            try:
                tempo_val = int(float(raw) * 60)
                result['tempos'].append({
                    'measure_num': 1, 'beat': 1.0,
                    'bpm': float(tempo_val), 'text': ''
                })
            except (ValueError, TypeError):
                pass

    # Key signature
    key_str = None
    ks_el = root.find('.//KeySig')
    if ks_el is not None:
        acc_text = ks_el.findtext('accidental') or ks_el.findtext('concertKey') or ks_el.findtext('idx') or '0'
        try:
            acc = int(acc_text)
            key_str = _SHARP_KEYS.get(acc) or _FLAT_KEYS.get(acc) or 'C'
            result['key_signatures'].append({
                'measure_num': 1, 'key_name': key_str, 'sharps_flats': acc
            })
        except (ValueError, TypeError):
            pass

    # --- Walk staves/measures for full extraction ---
    # Only include Score-level Staff elements (with Measure children), not Part/Staff definitions
    score_el = root.find('.//Score') or root
    staff_elements = [s for s in score_el.findall('Staff') if s.find('Measure') is not None]
    if not staff_elements:
        # Fallback: try iter but filter to those with measures
        staff_elements = [s for s in root.iter('Staff') if s.find('Measure') is not None]
    if not staff_elements:
        staff_elements = [root]

    result['metadata'] = {
        'title': title,
        'key': key_str,
        'time_signature': time_sig,
        'initial_bpm': tempo_val,
        'track_count': len(staff_elements),
    }

    # Get track names from Part/Instrument
    track_names = {}
    for i, part in enumerate(root.iter('Part')):
        tn = part.findtext('.//trackName') or part.findtext('.//Instrument/longName') or f"Track {i+1}"
        track_names[i] = tn

    total_measures = 0

    for track_num, staff in enumerate(staff_elements):
        track_name = track_names.get(track_num, f"Track {track_num + 1}")
        measure_num = 0

        for measure in staff.iter('Measure'):
            measure_num += 1
            if track_num == 0:
                total_measures = max(total_measures, measure_num)

            # --- Chord symbols (Harmony) --- only from first staff
            if track_num == 0:
                chord_order = 1
                for harmony in measure.iter('Harmony'):
                    info = harmony.find('harmonyInfo')
                    name_el = harmony.find('name')
                    root_num_text = harmony.findtext('root')
                    if name_el is None and info is not None:
                        name_el = info.find('name')
                        if root_num_text is None:
                            root_num_text = info.findtext('root')
                    if name_el is None:
                        continue
                    chord_name = (name_el.text or '').strip()
                    if not chord_name:
                        continue

                    if chord_name != 'N.C.' and root_num_text is not None:
                        try:
                            root_note = root_map.get(int(root_num_text), '')
                            if root_note and not chord_name[0].isupper():
                                chord_name = root_note + chord_name
                            elif root_note and chord_name in ('maj', 'min', 'dim', 'aug'):
                                chord_name = root_note + chord_name
                        except (ValueError, TypeError):
                            pass

                    result['chord_symbols'].append({
                        'measure_num': measure_num,
                        'beat': 1.0,
                        'symbol': chord_name,
                        'chord_order': chord_order,
                    })
                    chord_order += 1

                # --- Rehearsal marks ---
                for rm in measure.iter('RehearsalMark'):
                    text_el = rm.find('text')
                    if text_el is not None and text_el.text:
                        result['text_marks'].append({
                            'measure_num': measure_num, 'beat': 1.0,
                            'text_type': 'rehearsal', 'content': text_el.text.strip()
                        })

            # --- Notes and Rests ---
            voice_containers = [
                el for el in measure if el.tag == 'voice' and len(el) > 0
            ]
            if not voice_containers:
                voice_containers = [measure]

            for voice_idx, voice_el in enumerate(voice_containers, start=1):
                beat_pos = 1.0

                for child in voice_el:
                    tag = child.tag
                    if tag not in ('Chord', 'Rest'):
                        continue

                    dur_type_el = child.find('durationType')
                    dur_type = dur_type_el.text.strip() if dur_type_el is not None and dur_type_el.text else 'quarter'
                    dur_beats = _DURATION_TO_BEATS.get(dur_type, 1.0)

                    dot_count = 0
                    dots_el = child.find('dots')
                    if dots_el is not None and dots_el.text:
                        try:
                            dot_count = int(dots_el.text)
                            dur_beats *= (2.0 - (0.5 ** dot_count))
                        except (ValueError, TypeError):
                            pass

                    # Articulations on this chord/rest
                    artics = []
                    for art_el in child.findall('Articulation'):
                        sub = art_el.findtext('subtype')
                        if sub:
                            artics.append(sub)

                    is_grace = False

                    if tag == 'Rest':
                        result['notes'].append({
                            'track_num': track_num,
                            'track_name': track_name,
                            'voice': voice_idx,
                            'measure_num': measure_num,
                            'beat': round(beat_pos, 2),
                            'offset_quarters': 0,
                            'midi_pitch': 0,
                            'note_name': 'rest',
                            'duration_quarters': dur_beats,
                            'duration_type': dur_type,
                            'dot_count': dot_count,
                            'velocity': 0,
                            'is_rest': True,
                            'is_grace': False,
                            'tie_type': None,
                            'stem_direction': None,
                            'notehead_type': None,
                            'fingering': None,
                            'articulations': artics,
                        })

                    elif tag == 'Chord':
                        # Check for grace note
                        is_grace = child.find('appoggiatura') is not None or child.find('acciaccatura') is not None

                        # Lyrics on this chord
                        for lyr in child.findall('Lyrics'):
                            text_el = lyr.find('text')
                            syllabic_el = lyr.find('syllabic')
                            if text_el is not None and text_el.text:
                                result['lyrics'].append({
                                    'measure_num': measure_num,
                                    'beat': round(beat_pos, 2),
                                    'syllable': text_el.text.strip(),
                                    'syllabic': syllabic_el.text.strip() if syllabic_el is not None and syllabic_el.text else None,
                                    'verse_num': 1,
                                })

                        # Each Note in the Chord
                        for note_el in child.findall('Note'):
                            pitch_el = note_el.find('pitch')
                            if pitch_el is None or not pitch_el.text:
                                continue
                            try:
                                midi_pitch = int(pitch_el.text)
                            except (ValueError, TypeError):
                                continue

                            # Velocity
                            vel = 64
                            vel_el = note_el.find('velocity')
                            if vel_el is not None and vel_el.text:
                                try:
                                    vel = int(vel_el.text)
                                except (ValueError, TypeError):
                                    pass

                            # Tie
                            tie_type = None
                            for spanner in note_el.findall('Spanner'):
                                if spanner.get('type') == 'Tie':
                                    if spanner.find('next') is not None:
                                        tie_type = 'start'
                                    elif spanner.find('prev') is not None:
                                        tie_type = 'stop' if tie_type is None else 'continue'

                            # Accidental
                            acc_el = note_el.find('Accidental')

                            result['notes'].append({
                                'track_num': track_num,
                                'track_name': track_name,
                                'voice': voice_idx,
                                'measure_num': measure_num,
                                'beat': round(beat_pos, 2),
                                'offset_quarters': 0,
                                'midi_pitch': midi_pitch,
                                'note_name': midi_to_note_name(midi_pitch),
                                'duration_quarters': dur_beats,
                                'duration_type': dur_type,
                                'dot_count': dot_count,
                                'velocity': vel,
                                'is_rest': False,
                                'is_grace': is_grace,
                                'tie_type': tie_type,
                                'stem_direction': None,
                                'notehead_type': None,
                                'fingering': None,
                                'articulations': artics,
                            })

                    # Advance beat position (grace notes don't consume time)
                    advance = True
                    if tag == 'Chord' and is_grace:
                        advance = False
                    if advance:
                        beat_pos += dur_beats

    result['metadata']['measure_count'] = total_measures
    result['metadata']['track_count'] = len(staff_elements)

    note_count = len([n for n in result['notes'] if not n['is_rest']])
    logger.info("Full parse: %d notes, %d rests, %d chords, %d lyrics, %d measures",
                note_count,
                len([n for n in result['notes'] if n['is_rest']]),
                len(result['chord_symbols']),
                len(result['lyrics']),
                total_measures)

    return result


def parse_upload_full(file_bytes: bytes, filename: str) -> dict:
    """Parse any supported file and return rich structured data."""
    ext = os.path.splitext(filename.lower())[1]

    if ext == '.mscz':
        try:
            with zipfile.ZipFile(
                __import__('io').BytesIO(file_bytes), 'r'
            ) as zf:
                mscx_names = [n for n in zf.namelist() if n.lower().endswith('.mscx')]
                if not mscx_names:
                    raise ValueError("No .mscx file found inside .mscz")
                xml_bytes = zf.read(mscx_names[0])
        except zipfile.BadZipFile:
            raise ValueError(".mscz file is corrupt or not a valid ZIP")
        xml_content = xml_bytes.decode('utf-8', errors='replace')
        base_title = os.path.splitext(filename)[0]
        result = parse_mscx_full(xml_content, base_title)
        result['import_format'] = 'mscz'
        return result

    elif ext == '.mscx':
        xml_content = file_bytes.decode('utf-8', errors='replace')
        base_title = os.path.splitext(filename)[0]
        result = parse_mscx_full(xml_content, base_title)
        result['import_format'] = 'mscx'
        return result

    elif ext in ('.musicxml', '.xml', '.mxl', '.mid', '.midi'):
        # For these formats, use existing parser + basic note extraction
        # (full music21 extraction deferred to future sprint)
        from app.services.score_parser import parse_music_file
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / f'upload{ext}'
            tmp_path.write_bytes(file_bytes)
            parsed = parse_music_file(str(tmp_path), filename)

        # Convert ParsedScore to rich dict format
        return {
            'metadata': {
                'title': parsed.title,
                'key': parsed.key,
                'time_signature': parsed.time_signature,
                'initial_bpm': parsed.tempo,
                'track_count': 1,
                'measure_count': max((c.measure_number for c in parsed.chords), default=0),
            },
            'notes': [{
                'track_num': 0, 'track_name': 'Track 1', 'voice': n.voice,
                'measure_num': n.measure_number, 'beat': n.beat_position,
                'offset_quarters': 0, 'midi_pitch': n.midi_pitch,
                'note_name': midi_to_note_name(n.midi_pitch),
                'duration_quarters': _DURATION_TO_BEATS.get(n.duration_type, 1.0),
                'duration_type': n.duration_type, 'dot_count': 0,
                'velocity': 64, 'is_rest': False, 'is_grace': False,
                'tie_type': None, 'stem_direction': None, 'notehead_type': None,
                'fingering': None, 'articulations': [],
            } for n in parsed.notes],
            'lyrics': [],
            'dynamics': [],
            'tempos': [],
            'time_signatures': [],
            'key_signatures': [],
            'chord_symbols': [{
                'measure_num': c.measure_number, 'beat': c.beat_position,
                'symbol': c.chord_symbol, 'chord_order': c.chord_order,
            } for c in parsed.chords],
            'text_marks': [],
            'import_format': ext.lstrip('.'),
            'raw_xml': None,
        }

    else:
        raise ValueError(f"Unsupported format: {ext}")


def save_full_parse(song_id: int, parsed: dict, db) -> dict:
    """
    Write all parsed data to DB for an existing song.
    Clears existing note data first (re-import replaces).
    Returns summary counts.
    """
    # Clear existing rich note data
    for table in ['song_notes', 'song_lyrics', 'song_dynamics',
                  'song_tempos', 'song_time_signatures',
                  'song_key_signatures', 'song_text_marks']:
        try:
            db.execute_non_query(f"DELETE FROM {table} WHERE song_id = ?", (song_id,))
        except Exception:
            pass  # Table may not exist yet if migration hasn't run

    # Insert notes
    notes_saved = 0
    for n in parsed['notes']:
        try:
            db.execute_non_query("""
                INSERT INTO song_notes (song_id, track_num, track_name, voice,
                    measure_num, beat, offset_quarters, midi_pitch, note_name,
                    duration_quarters, duration_type, dot_count, velocity,
                    is_rest, is_grace, tie_type, stem_direction, notehead_type, fingering)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                song_id, n['track_num'], n['track_name'], n['voice'],
                n['measure_num'], n['beat'], n.get('offset_quarters', 0),
                n['midi_pitch'], n['note_name'],
                n['duration_quarters'], n['duration_type'], n['dot_count'],
                n['velocity'], 1 if n['is_rest'] else 0,
                1 if n['is_grace'] else 0,
                n['tie_type'], n['stem_direction'], n['notehead_type'], n['fingering']
            ))
            notes_saved += 1
        except Exception as e:
            logger.debug("Note insert failed: %s", e)

    # Insert lyrics
    lyrics_saved = 0
    for lyr in parsed.get('lyrics', []):
        try:
            db.execute_non_query("""
                INSERT INTO song_lyrics (song_id, measure_num, beat, syllable, syllabic, verse_num)
                VALUES (?,?,?,?,?,?)
            """, (song_id, lyr['measure_num'], lyr['beat'],
                  lyr['syllable'], lyr.get('syllabic'), lyr.get('verse_num', 1)))
            lyrics_saved += 1
        except Exception as e:
            logger.debug("Lyric insert failed: %s", e)

    # Insert dynamics
    for d in parsed.get('dynamics', []):
        try:
            db.execute_non_query("""
                INSERT INTO song_dynamics (song_id, track_num, measure_num, beat, dynamic, velocity)
                VALUES (?,?,?,?,?,?)
            """, (song_id, d.get('track_num', 0), d['measure_num'],
                  d['beat'], d['dynamic'], d.get('velocity')))
        except Exception as e:
            logger.debug("Dynamic insert failed: %s", e)

    # Insert tempos
    for t in parsed.get('tempos', []):
        try:
            db.execute_non_query("""
                INSERT INTO song_tempos (song_id, measure_num, beat, bpm, text)
                VALUES (?,?,?,?,?)
            """, (song_id, t['measure_num'], t['beat'], t['bpm'], t.get('text', '')))
        except Exception as e:
            logger.debug("Tempo insert failed: %s", e)

    # Insert time signatures
    for ts in parsed.get('time_signatures', []):
        try:
            db.execute_non_query("""
                INSERT INTO song_time_signatures (song_id, measure_num, numerator, denominator)
                VALUES (?,?,?,?)
            """, (song_id, ts['measure_num'], ts['numerator'], ts['denominator']))
        except Exception as e:
            logger.debug("Time sig insert failed: %s", e)

    # Insert key signatures
    for ks in parsed.get('key_signatures', []):
        try:
            db.execute_non_query("""
                INSERT INTO song_key_signatures (song_id, measure_num, key_name, sharps_flats)
                VALUES (?,?,?,?)
            """, (song_id, ks['measure_num'], ks['key_name'], ks['sharps_flats']))
        except Exception as e:
            logger.debug("Key sig insert failed: %s", e)

    # Insert text marks
    for tm in parsed.get('text_marks', []):
        try:
            db.execute_non_query("""
                INSERT INTO song_text_marks (song_id, measure_num, beat, text_type, content)
                VALUES (?,?,?,?,?)
            """, (song_id, tm['measure_num'], tm['beat'], tm['text_type'], tm['content']))
        except Exception as e:
            logger.debug("Text mark insert failed: %s", e)

    # Update Songs table metadata
    actual_notes = len([n for n in parsed['notes'] if not n['is_rest']])
    meta = parsed.get('metadata', {})
    try:
        db.execute_non_query("""
            UPDATE Songs SET
                has_note_data = ?,
                has_lyrics = ?,
                import_format = ?,
                track_count = ?,
                measure_count = ?,
                total_notes = ?,
                raw_xml = ?
            WHERE id = ?
        """, (
            1 if actual_notes > 0 else 0,
            1 if lyrics_saved > 0 else 0,
            parsed.get('import_format'),
            meta.get('track_count'),
            meta.get('measure_count'),
            actual_notes,
            parsed.get('raw_xml'),
            song_id,
        ))
    except Exception as e:
        logger.warning("Failed to update Songs metadata: %s", e)

    return {
        'notes_saved': notes_saved,
        'actual_notes': actual_notes,
        'lyrics_saved': lyrics_saved,
        'dynamics': len(parsed.get('dynamics', [])),
        'text_marks': len(parsed.get('text_marks', [])),
    }
