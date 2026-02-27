"""
Universal music file parser for HarmonyLab.

Supports .mscz, .mscx (MuseScore), .musicxml/.xml (MusicXML), and .mid/.midi (MIDI).
Extracts chord symbols, key, time signature, and tempo from any supported format.
"""
import os
import zipfile
import tempfile
import xml.etree.ElementTree as ET
import logging
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)

# MuseScore root-note numbering — two systems exist:
# MuseScore 4.4.x and earlier: chromatic numbering (14=C, 15=C#/Db, ..., 25=B)
# MuseScore 4.5.x+: TPC (Tonal Pitch Class) from line of fifths (14=C, 15=G, 16=D, ...)
_CHROMATIC_ROOT = {
    13: 'B', 14: 'C', 15: 'Db', 16: 'D', 17: 'Eb', 18: 'E',
    19: 'F', 20: 'F#', 21: 'G', 22: 'Ab', 23: 'A', 24: 'Bb', 25: 'B'
}
_TPC_ROOT = {
    7: 'Cb', 8: 'Gb', 9: 'Db', 10: 'Ab', 11: 'Eb', 12: 'Bb', 13: 'F',
    14: 'C', 15: 'G', 16: 'D', 17: 'A', 18: 'E', 19: 'B',
    20: 'F#', 21: 'C#', 22: 'G#', 23: 'D#', 24: 'A#', 25: 'E#',
}
# Legacy alias for external callers
MSCZ_ROOT_TO_NOTE = _CHROMATIC_ROOT

# Key signature accidentals → key name
_SHARP_KEYS = {0: 'C', 1: 'G', 2: 'D', 3: 'A', 4: 'E', 5: 'B', 6: 'F#', 7: 'C#'}
_FLAT_KEYS  = {-1: 'F', -2: 'Bb', -3: 'Eb', -4: 'Ab', -5: 'Db', -6: 'Gb', -7: 'Cb'}


@dataclass
class ScoreChord:
    measure_number: int
    beat_position: float
    chord_symbol: str
    chord_order: int


@dataclass
class ScoreNote:
    measure_number: int
    beat_position: float
    midi_pitch: int
    duration_type: str  # e.g. "quarter", "half", "eighth"
    voice: int = 1


# Duration type → beat fraction (assuming quarter = 1 beat in 4/4)
_DURATION_TO_BEATS = {
    'whole': 4.0, 'half': 2.0, 'quarter': 1.0, 'eighth': 0.5,
    '16th': 0.25, '32nd': 0.125, '64th': 0.0625,
    'breve': 8.0, 'longa': 16.0,
}


@dataclass
class ParsedScore:
    title: str
    key: Optional[str]
    time_signature: Optional[str]
    tempo: Optional[int]
    chords: List[ScoreChord] = field(default_factory=list)
    notes: List[ScoreNote] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_music_file(file_path: str, filename: str) -> ParsedScore:
    """Parse any supported music file format and return structured data.

    Args:
        file_path: Absolute path to the (temp) file on disk.
        filename:  Original filename (used to determine format).

    Returns:
        ParsedScore with title, key, time_signature, tempo, and chords list.

    Raises:
        ValueError: If the format is unsupported or the file is corrupt.
    """
    ext = os.path.splitext(filename.lower())[1]

    if ext == '.mscz':
        return _parse_mscz(file_path, filename)
    elif ext == '.mscx':
        return _parse_mscx(file_path, filename)
    elif ext in ('.musicxml', '.xml', '.mxl'):
        return _parse_musicxml(file_path, filename)
    elif ext in ('.mid', '.midi'):
        return _parse_midi(file_path, filename)
    else:
        raise ValueError(f"Unsupported file format: '{ext}'. "
                         f"Supported: .mscz .mscx .musicxml .xml .mxl .mid .midi")


# ---------------------------------------------------------------------------
# MuseScore (.mscz / .mscx)
# ---------------------------------------------------------------------------

def _parse_mscz(file_path: str, filename: str) -> ParsedScore:
    """Unzip .mscz and parse the .mscx inside."""
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            mscx_names = [n for n in zf.namelist() if n.lower().endswith('.mscx')]
            if not mscx_names:
                raise ValueError("No .mscx file found inside the .mscz archive")
            xml_bytes = zf.read(mscx_names[0])
    except zipfile.BadZipFile:
        raise ValueError(".mscz file appears to be corrupt or not a valid ZIP archive")

    base_title = os.path.splitext(filename)[0]
    return _parse_mscx_content(xml_bytes.decode('utf-8', errors='replace'), base_title)


def _parse_mscx(file_path: str, filename: str) -> ParsedScore:
    """Parse .mscx MuseScore XML directly."""
    with open(file_path, 'r', encoding='utf-8', errors='replace') as fh:
        content = fh.read()
    base_title = os.path.splitext(filename)[0]
    return _parse_mscx_content(content, base_title)


def _parse_mscx_content(xml_content: str, default_title: str) -> ParsedScore:
    """Extract title, key, time sig, tempo, and chord symbols from MuseScore XML."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Could not parse MuseScore XML: {e}")

    # --- Detect MuseScore version to choose root-note mapping ---
    # 4.4.x and earlier: chromatic root numbering
    # 4.5.x+: TPC (Tonal Pitch Class) numbering
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
    logger.info("MuseScore version=%s root_map=%s", ms_version, 'TPC' if use_tpc else 'chromatic')

    # --- Title ---
    title = default_title
    for tag in ('metaTag[@name="workTitle"]', 'metaTag[@name="title"]'):
        el = root.find(f'.//{tag}')
        if el is not None and el.text and el.text.strip():
            title = el.text.strip()
            break
    if title == default_title:
        el = root.find('.//Title/text')
        if el is not None and el.text and el.text.strip():
            title = el.text.strip()

    # --- Time signature ---
    time_sig = "4/4"
    ts_el = root.find('.//TimeSig')
    if ts_el is not None:
        beats = ts_el.findtext('sigN') or ts_el.findtext('numerator') or '4'
        beat_type = ts_el.findtext('sigD') or ts_el.findtext('denominator') or '4'
        time_sig = f"{beats}/{beat_type}"

    # --- Tempo ---
    tempo_val = None
    tempo_el = root.find('.//Tempo')
    if tempo_el is not None:
        raw = tempo_el.findtext('tempo')
        if raw:
            try:
                tempo_val = int(float(raw) * 60)  # MuseScore stores beats/sec
            except (ValueError, TypeError):
                pass

    # --- Key signature ---
    key_str = None
    ks_el = root.find('.//KeySig')
    if ks_el is not None:
        acc_text = ks_el.findtext('accidental') or ks_el.findtext('idx') or '0'
        try:
            acc = int(acc_text)
            key_str = _SHARP_KEYS.get(acc) or _FLAT_KEYS.get(acc)
        except (ValueError, TypeError):
            pass

    # --- Chord symbols ---
    # MuseScore stores chord symbols as <Harmony> elements inside measures.
    # MuseScore 4 wraps measure content in <voice> elements, so Harmony may be
    # a grandchild (or deeper) of Measure. Use iter() to find at any depth.
    # MuseScore 4.6+ wraps name/root inside <harmonyInfo> subelement.
    chords: List[ScoreChord] = []
    measure_num = 0
    measures_scanned = 0
    measures_with_harmony = 0

    for measure in root.iter('Measure'):
        measure_num += 1
        measures_scanned += 1
        chord_order = 1
        harmony_in_measure = 0

        for elem in measure.iter('Harmony'):
            # Try direct children first, then <harmonyInfo> wrapper (4.6+)
            name_el = elem.find('name')
            root_num_text = elem.findtext('root')
            if name_el is None:
                info = elem.find('harmonyInfo')
                if info is not None:
                    name_el = info.find('name')
                    if root_num_text is None:
                        root_num_text = info.findtext('root')
            if name_el is None:
                continue
            chord_name = (name_el.text or '').strip()
            if not chord_name:
                continue

            # Skip "N.C." (no chord) markers from root prepending
            if chord_name == 'N.C.':
                chords.append(ScoreChord(
                    measure_number=measure_num,
                    beat_position=1.0,
                    chord_symbol='N.C.',
                    chord_order=chord_order,
                ))
                chord_order += 1
                harmony_in_measure += 1
                continue

            # Root note (numeric) - prepend if the name doesn't already include it
            if root_num_text is not None:
                try:
                    root_note = root_map.get(int(root_num_text), '')
                    if root_note and not chord_name[0].isupper():
                        chord_name = root_note + chord_name
                    elif root_note and chord_name in ('maj', 'min', 'dim', 'aug'):
                        chord_name = root_note + chord_name
                except (ValueError, TypeError):
                    pass

            chords.append(ScoreChord(
                measure_number=measure_num,
                beat_position=1.0,
                chord_symbol=chord_name,
                chord_order=chord_order,
            ))
            chord_order += 1
            harmony_in_measure += 1

        if harmony_in_measure > 0:
            measures_with_harmony += 1
            logger.debug("Measure %d: %d harmony element(s)", measure_num, harmony_in_measure)

    logger.info(
        "MuseScore parse complete: measures_scanned=%d measures_with_harmony=%d total_chords=%d",
        measures_scanned, measures_with_harmony, len(chords)
    )
    if len(chords) == 0:
        logger.warning(
            "No chord symbols found in MuseScore file. "
            "This file may not contain explicit chord symbols (Harmony elements). "
            "Export as .mid from MuseScore for note-based chord analysis."
        )

    # --- Note extraction ---
    # MuseScore <Chord> elements (rhythm events) contain <Note> children with <pitch>.
    # Track beat position by accumulating durations within each measure/voice.
    #
    # MuseScore 4 format: <voice> is a CONTAINER element (direct child of Measure)
    #   <Measure><voice><Chord>...</Chord></voice></Measure>
    # MuseScore 3 format: <voice> is a TEXT element INSIDE Chord (voice number)
    #   <Measure><Chord><voice>0</voice>...</Chord></Measure>
    # We must detect which format by checking if direct children named 'voice'
    # have sub-elements (container) vs only text (indicator).
    notes: List[ScoreNote] = []
    note_measure_num = 0

    # Use first Staff element to avoid duplicate measures from multi-staff scores
    first_staff = root.find('.//Staff')
    note_root = first_staff if first_staff is not None else root
    logger.debug("Note extraction: searching from <%s>, first_staff found=%s",
                 note_root.tag, first_staff is not None)

    for measure in note_root.iter('Measure'):
        note_measure_num += 1

        # Detect voice containers: direct children of Measure named 'voice'
        # that themselves contain child elements (Chord, Rest, etc.)
        voice_containers = [
            el for el in measure if el.tag == 'voice' and len(el) > 0
        ]

        if not voice_containers:
            # No voice container wrappers — MuseScore 3 or flat format.
            # Chord/Rest are direct children of Measure.
            voice_containers = [measure]
            if note_measure_num == 1:
                direct_tags = [el.tag for el in measure]
                logger.debug("No voice containers in measure 1, direct children: %s", direct_tags)

        for voice_idx, voice_el in enumerate(voice_containers, start=1):
            beat_pos = 1.0  # Start at beat 1

            for child in voice_el:
                tag = child.tag
                if tag not in ('Chord', 'Rest'):
                    continue  # Skip Harmony, KeySig, TimeSig, Clef, etc.

                dur_type_el = child.find('durationType')
                dur_type = dur_type_el.text.strip() if dur_type_el is not None and dur_type_el.text else 'quarter'
                dur_beats = _DURATION_TO_BEATS.get(dur_type, 1.0)

                # Handle dots (dotted notes = 1.5x duration)
                dots_el = child.find('dots')
                if dots_el is not None and dots_el.text:
                    try:
                        dot_count = int(dots_el.text)
                        dur_beats *= (2.0 - (0.5 ** dot_count))
                    except (ValueError, TypeError):
                        pass

                if tag == 'Chord':
                    # Extract all notes in this rhythmic event
                    for note_el in child.findall('Note'):
                        pitch_el = note_el.find('pitch')
                        if pitch_el is not None and pitch_el.text:
                            try:
                                midi_pitch = int(pitch_el.text)
                                notes.append(ScoreNote(
                                    measure_number=note_measure_num,
                                    beat_position=round(beat_pos, 2),
                                    midi_pitch=midi_pitch,
                                    duration_type=dur_type,
                                    voice=voice_idx,
                                ))
                            except (ValueError, TypeError):
                                pass

                beat_pos += dur_beats

    logger.info("Note extraction: %d notes from %d measures", len(notes), note_measure_num)

    logger.info("Parsed MuseScore file: title=%r key=%r time_sig=%r chords=%d notes=%d",
                title, key_str, time_sig, len(chords), len(notes))
    return ParsedScore(title=title, key=key_str, time_signature=time_sig,
                       tempo=tempo_val, chords=chords, notes=notes)


# ---------------------------------------------------------------------------
# MusicXML (.musicxml / .xml / .mxl)
# ---------------------------------------------------------------------------

def _parse_musicxml(file_path: str, filename: str) -> ParsedScore:
    """Parse MusicXML using music21."""
    try:
        from music21 import converter, harmony, meter
        from music21 import tempo as m21tempo
    except ImportError:
        raise ValueError("music21 is required for MusicXML parsing but is not installed")

    try:
        score = converter.parse(file_path)
    except Exception as e:
        raise ValueError(f"music21 could not parse the file: {e}")

    # --- Title ---
    base = os.path.splitext(filename)[0]
    title = base
    try:
        if score.metadata and score.metadata.title:
            title = score.metadata.title
    except Exception:
        pass

    # --- Key ---
    key_str = None
    try:
        detected = score.analyze('key')
        key_str = f"{detected.tonic.name} {detected.mode}"
    except Exception:
        pass

    # --- Time signature ---
    time_sig = "4/4"
    try:
        ts_list = list(score.recurse().getElementsByClass(meter.TimeSignature))
        if ts_list:
            ts = ts_list[0]
            time_sig = f"{ts.numerator}/{ts.denominator}"
    except Exception:
        pass

    # --- Tempo ---
    tempo_val = None
    try:
        mm_list = list(score.recurse().getElementsByClass(m21tempo.MetronomeMark))
        if mm_list:
            tempo_val = int(mm_list[0].number)
    except Exception:
        pass

    # --- Chord symbols ---
    chords: List[ScoreChord] = []
    measure_num = 0

    try:
        for part in score.parts:
            for measure in part.getElementsByClass('Measure'):
                measure_num += 1
                harmony_els = list(measure.getElementsByClass(harmony.ChordSymbol))
                for order, cs in enumerate(harmony_els, start=1):
                    symbol = cs.figure
                    if symbol:
                        chords.append(ScoreChord(
                            measure_number=measure_num,
                            beat_position=round(float(cs.beat), 2),
                            chord_symbol=symbol,
                            chord_order=order,
                        ))
            break  # First part only for chord symbols
    except Exception as e:
        logger.warning("Error extracting chord symbols from MusicXML: %s", e)

    logger.info("Parsed MusicXML: title=%r key=%r time_sig=%r chords=%d",
                title, key_str, time_sig, len(chords))
    return ParsedScore(title=title, key=key_str, time_signature=time_sig,
                       tempo=tempo_val, chords=chords)


# ---------------------------------------------------------------------------
# MIDI (.mid / .midi) — delegates to existing mido-based parser
# ---------------------------------------------------------------------------

def _parse_midi(file_path: str, filename: str) -> ParsedScore:
    """Parse MIDI using the existing mido-based parser."""
    from app.services.midi_parser import parse_midi_file

    midi = parse_midi_file(file_path)
    title = os.path.splitext(filename)[0]
    if midi.title:
        title = midi.title

    chords = [
        ScoreChord(
            measure_number=c.measure_number,
            beat_position=c.beat_position,
            chord_symbol=c.chord_symbol,
            chord_order=i + 1,
        )
        for i, c in enumerate(midi.chords)
    ]

    return ParsedScore(
        title=title,
        key=None,
        time_signature=midi.time_signature,
        tempo=midi.tempo,
        chords=chords,
    )
