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

# MuseScore root-note numbering (used in .mscx files)
MSCZ_ROOT_TO_NOTE = {
    14: 'C', 15: 'Db', 16: 'D', 17: 'Eb', 18: 'E',
    19: 'F', 20: 'F#', 21: 'G', 22: 'Ab', 23: 'A', 24: 'Bb', 25: 'B'
}

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
class ParsedScore:
    title: str
    key: Optional[str]
    time_signature: Optional[str]
    tempo: Optional[int]
    chords: List[ScoreChord] = field(default_factory=list)


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
    chords: List[ScoreChord] = []
    measure_num = 0

    for measure in root.iter('Measure'):
        measure_num += 1
        chord_order = 1

        for elem in measure:
            if elem.tag != 'Harmony':
                continue

            # Chord name may be directly in <name> or structured
            name_el = elem.find('name')
            if name_el is None:
                continue
            chord_name = (name_el.text or '').strip()
            if not chord_name:
                continue

            # Root note (numeric) – prepend if the name doesn't already include it
            root_num_text = elem.findtext('root')
            if root_num_text is not None:
                try:
                    root_note = MSCZ_ROOT_TO_NOTE.get(int(root_num_text), '')
                    if root_note and not chord_name[0].isupper():
                        chord_name = root_note + chord_name
                    elif root_note and chord_name == 'maj' or chord_name == 'min':
                        # Plain quality only, prepend root
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

    logger.info("Parsed MuseScore file: title=%r key=%r time_sig=%r chords=%d",
                title, key_str, time_sig, len(chords))
    return ParsedScore(title=title, key=key_str, time_signature=time_sig,
                       tempo=tempo_val, chords=chords)


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
