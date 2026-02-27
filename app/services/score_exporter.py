"""
MuseScore export service for HarmonyLab.

Generates annotated .mscx (MuseScore XML) files with chord symbols,
Roman numerals, and harmonic function color coding.
"""
import xml.etree.ElementTree as ET
import zipfile
import io
import uuid
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Note name to MuseScore TPC (Tonal Pitch Class) value
_NOTE_TO_TPC = {
    'Cb': 7, 'Gb': 8, 'Db': 9, 'Ab': 10, 'Eb': 11, 'Bb': 12, 'F': 13,
    'C': 14, 'G': 15, 'D': 16, 'A': 17, 'E': 18, 'B': 19,
    'F#': 20, 'C#': 21, 'G#': 22, 'D#': 23, 'A#': 24, 'E#': 25,
}

# Key name to accidentals count for KeySig
_KEY_TO_ACCIDENTALS = {
    'C': 0, 'G': 1, 'D': 2, 'A': 3, 'E': 4, 'B': 5, 'F#': 6, 'C#': 7,
    'F': -1, 'Bb': -2, 'Eb': -3, 'Ab': -4, 'Db': -5, 'Gb': -6, 'Cb': -7,
}

# Function colors matching HarmonicAnalyzer
_FUNCTION_COLORS = {
    'tonic': (34, 197, 94),       # #22c55e green
    'subdominant': (59, 130, 246), # #3b82f6 blue
    'dominant': (239, 68, 68),     # #ef4444 red
    'secondary': (245, 158, 11),   # #f59e0b orange
    'chromatic': (139, 92, 246),   # #8b5cf6 purple
    'diminished': (107, 114, 128), # #6b7280 gray
    'unknown': (156, 163, 175),    # #9ca3af light gray
}


def _eid() -> str:
    """Generate a placeholder eid for MuseScore XML."""
    return str(uuid.uuid4().hex[:20])


def _parse_root_from_symbol(symbol: str) -> tuple:
    """Extract root note and quality from chord symbol.

    Returns (root_note, quality) tuple.
    """
    if not symbol:
        return None, ''
    import re
    match = re.match(r'^([A-G][#b]?)(.*)', symbol)
    if not match:
        return None, symbol
    return match.group(1), match.group(2)


def export_mscx(
    title: str,
    composer: Optional[str],
    key_str: Optional[str],
    time_sig: str,
    tempo: Optional[int],
    chords: List[Dict],
    analysis: Optional[Dict] = None,
) -> str:
    """Generate MuseScore 4.5 compatible .mscx XML content.

    Args:
        title: Song title.
        composer: Composer name.
        key_str: Key string (e.g. "C", "Bb", "F#").
        time_sig: Time signature (e.g. "4/4", "3/4").
        tempo: Tempo in BPM.
        chords: List of dicts with keys: measure, beat, symbol.
        analysis: Optional analysis dict with 'chords' list containing
                  roman, function, color fields.

    Returns:
        XML string content of the .mscx file.
    """
    # Build analysis lookup by index
    analysis_by_idx = {}
    if analysis and 'chords' in analysis:
        for ac in analysis['chords']:
            analysis_by_idx[ac.get('index', -1)] = ac

    # Parse time signature
    ts_parts = time_sig.split('/')
    sig_n = ts_parts[0] if len(ts_parts) > 0 else '4'
    sig_d = ts_parts[1] if len(ts_parts) > 1 else '4'

    # Parse key for accidentals
    key_root = None
    if key_str:
        import re
        km = re.match(r'^([A-G][#b]?)', key_str)
        if km:
            key_root = km.group(1)
    accidentals = _KEY_TO_ACCIDENTALS.get(key_root, 0) if key_root else 0

    # Group chords by measure
    measures_dict: Dict[int, List] = {}
    for i, ch in enumerate(chords):
        m = ch.get('measure', 1)
        if m not in measures_dict:
            measures_dict[m] = []
        measures_dict[m].append((i, ch))

    max_measure = max(measures_dict.keys()) if measures_dict else 1

    # Duration type for whole rest based on time sig
    rest_type = 'whole' if sig_d == '4' else 'half'

    # Build XML
    root = ET.Element('museScore', version='4.50')
    ET.SubElement(root, 'programVersion').text = '4.5.0'
    ET.SubElement(root, 'programRevision').text = 'harmonylab'

    score = ET.SubElement(root, 'Score')
    ET.SubElement(score, 'Division').text = '480'

    # Metadata
    for name, value in [
        ('workTitle', title),
        ('composer', composer or ''),
        ('arranger', 'HarmonyLab Analysis'),
    ]:
        tag = ET.SubElement(score, 'metaTag', name=name)
        tag.text = value

    # Part and Instrument
    part = ET.SubElement(score, 'Part', id='1')
    staff_type = ET.SubElement(ET.SubElement(part, 'Staff', id='1'), 'StaffType', group='pitched')
    ET.SubElement(staff_type, 'name').text = 'stdNormal'
    ET.SubElement(part, 'trackName').text = 'Lead Sheet'
    inst = ET.SubElement(part, 'Instrument', id='piano')
    ET.SubElement(inst, 'longName').text = 'Lead Sheet'
    ET.SubElement(inst, 'shortName').text = 'L.S.'
    ET.SubElement(inst, 'instrumentId').text = 'keyboard.piano'
    chan = ET.SubElement(inst, 'Channel')
    ET.SubElement(chan, 'program', value='0')
    chan_h = ET.SubElement(inst, 'Channel', name='harmony')
    ET.SubElement(chan_h, 'program', value='0')

    # Staff content
    staff = ET.SubElement(score, 'Staff', id='1')

    # Title VBox
    vbox = ET.SubElement(staff, 'VBox')
    ET.SubElement(vbox, 'height').text = '10'
    title_text = ET.SubElement(vbox, 'Text')
    ET.SubElement(title_text, 'style').text = 'title'
    ET.SubElement(title_text, 'text').text = title
    if composer:
        comp_text = ET.SubElement(vbox, 'Text')
        ET.SubElement(comp_text, 'style').text = 'composer'
        ET.SubElement(comp_text, 'text').text = composer
    # Add key and analysis info as subtitle
    subtitle = ET.SubElement(vbox, 'Text')
    ET.SubElement(subtitle, 'style').text = 'subtitle'
    key_label = analysis.get('detected_key', key_str or 'Unknown') if analysis else (key_str or 'Unknown')
    conf_label = ''
    if analysis:
        conf = analysis.get('confidence', 0)
        conf_label = f' ({round(conf * 100)}% confidence)'
    ET.SubElement(subtitle, 'text').text = f'Key: {key_label}{conf_label}'

    # Measures
    for m_num in range(1, max_measure + 1):
        measure = ET.SubElement(staff, 'Measure')
        ET.SubElement(measure, 'eid').text = _eid()
        voice = ET.SubElement(measure, 'voice')

        # First measure: key sig, time sig, tempo
        if m_num == 1:
            ks = ET.SubElement(voice, 'KeySig')
            ET.SubElement(ks, 'eid').text = _eid()
            ET.SubElement(ks, 'concertKey').text = str(accidentals)

            ts = ET.SubElement(voice, 'TimeSig')
            ET.SubElement(ts, 'eid').text = _eid()
            ET.SubElement(ts, 'sigN').text = sig_n
            ET.SubElement(ts, 'sigD').text = sig_d

            if tempo:
                tempo_el = ET.SubElement(voice, 'Tempo')
                ET.SubElement(tempo_el, 'tempo').text = str(round(tempo / 60, 6))
                ET.SubElement(tempo_el, 'followText').text = '1'
                ET.SubElement(tempo_el, 'eid').text = _eid()
                sym = '\u266a' if tempo else ''
                ET.SubElement(tempo_el, 'text').text = f'{sym} = {tempo}'

        # Add chord symbols and roman numeral annotations
        if m_num in measures_dict:
            for chord_idx, ch_data in measures_dict[m_num]:
                symbol = ch_data.get('symbol', '')
                if not symbol or symbol == 'N.C.':
                    continue

                root_note, quality = _parse_root_from_symbol(symbol)
                tpc = _NOTE_TO_TPC.get(root_note, 14) if root_note else 14

                harm = ET.SubElement(voice, 'Harmony')
                ET.SubElement(harm, 'root').text = str(tpc)
                ET.SubElement(harm, 'name').text = quality
                ET.SubElement(harm, 'eid').text = _eid()

                # Add Roman numeral as StaffText below the chord
                if chord_idx in analysis_by_idx:
                    ac = analysis_by_idx[chord_idx]
                    roman = ac.get('roman', '?')
                    func = ac.get('function', 'unknown')
                    r, g, b = _FUNCTION_COLORS.get(func, _FUNCTION_COLORS['unknown'])

                    st = ET.SubElement(voice, 'StaffText')
                    ET.SubElement(st, 'eid').text = _eid()
                    ET.SubElement(st, 'placement').text = 'below'
                    color_el = ET.SubElement(st, 'color')
                    color_el.set('r', str(r))
                    color_el.set('g', str(g))
                    color_el.set('b', str(b))
                    color_el.set('a', '255')
                    ET.SubElement(st, 'text').text = roman

        # Add whole rest as placeholder (lead sheet style)
        rest = ET.SubElement(voice, 'Rest')
        ET.SubElement(rest, 'eid').text = _eid()
        ET.SubElement(rest, 'durationType').text = rest_type

    # Serialize
    ET.indent(root, space='  ')
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_str += ET.tostring(root, encoding='unicode')
    return xml_str


def export_mscz(
    title: str,
    composer: Optional[str],
    key_str: Optional[str],
    time_sig: str,
    tempo: Optional[int],
    chords: List[Dict],
    analysis: Optional[Dict] = None,
) -> bytes:
    """Generate a .mscz (zipped .mscx) file as bytes.

    Same args as export_mscx.
    Returns bytes of the ZIP archive.
    """
    mscx_content = export_mscx(title, composer, key_str, time_sig, tempo, chords, analysis)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        safe_title = ''.join(c for c in title if c.isalnum() or c in ' -_').strip()
        zf.writestr(f'{safe_title}.mscx', mscx_content)
    return buf.getvalue()
