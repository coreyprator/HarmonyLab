"""
Key Center Detection and Pattern Recognition Service

Detects key center regions and ii-V-I / ii-V-i patterns in chord progressions.
Uses interval-based analysis independent of the global key detection.
"""
import re
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Chromatic note names (flats preferred for jazz)
NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
NOTE_TO_PC = {}
for i, n in enumerate(NOTE_NAMES):
    NOTE_TO_PC[n] = i
# Add sharps as aliases
NOTE_TO_PC.update({'C#': 1, 'D#': 3, 'F#': 6, 'G#': 8, 'A#': 10, 'B#': 0, 'Cb': 11})


def _parse_chord(symbol: str) -> Optional[Dict]:
    """Parse a chord symbol into root pitch class and quality info."""
    if not symbol or symbol == 'N.C.':
        return None
    match = re.match(r'^([A-G])([#b]?)(.*)$', symbol)
    if not match:
        return None
    root_str = match.group(1) + match.group(2)
    quality = match.group(3)
    pc = NOTE_TO_PC.get(root_str)
    if pc is None:
        return None

    is_minor = quality.startswith('m') and not quality.startswith('maj')
    is_dom7 = (quality.startswith('7') or quality == '9' or quality == '13'
               or quality == '11' or quality.startswith('7'))
    is_maj7 = quality.startswith('maj7') or quality.startswith('Maj7') or quality.startswith('M7')
    is_half_dim = 'm7b5' in quality or quality.startswith('ø')
    is_dim = 'dim' in quality and not is_half_dim
    is_major_triad = not is_minor and not is_dom7 and not is_dim and not is_half_dim

    return {
        'root_pc': pc,
        'root_name': root_str,
        'quality': quality,
        'symbol': symbol,
        'is_minor': is_minor,
        'is_dom7': is_dom7,
        'is_maj7': is_maj7,
        'is_half_dim': is_half_dim,
        'is_dim': is_dim,
        'is_major_triad': is_major_triad,
    }


def detect_ii_v_i_patterns(chords: List[Dict]) -> List[Dict]:
    """Detect ii-V-I (major) and ii-V-i (harmonic minor) patterns.

    Args:
        chords: List of analyzed chord dicts with 'symbol', 'measure', 'beat' fields.

    Returns:
        List of pattern dicts with type, indices, target_key, mode.
    """
    patterns = []
    parsed = [_parse_chord(c.get('symbol', '')) for c in chords]

    for i in range(len(parsed) - 2):
        c1, c2, c3 = parsed[i], parsed[i + 1], parsed[i + 2]
        if not c1 or not c2 or not c3:
            continue

        # Check for ii-V-I in major:
        # ii = minor7 (root at +2 from I), V = dom7 (root at +7 from I), I = major
        # Interval from c1 root to c3 root should be 2 semitones (ii -> I = down whole step)
        # Interval from c2 root to c3 root should be 7 semitones (V -> I = down P5)
        target_pc = c3['root_pc']
        ii_interval = (c1['root_pc'] - target_pc) % 12
        v_interval = (c2['root_pc'] - target_pc) % 12

        if ii_interval == 2 and v_interval == 7:
            if c2['is_dom7']:
                target_name = NOTE_NAMES[target_pc]
                if c1['is_minor'] and (c3['is_major_triad'] or c3['is_maj7']):
                    # Major ii-V-I
                    patterns.append({
                        'type': 'ii-V-I',
                        'indices': [i, i + 1, i + 2],
                        'target_key': target_name,
                        'mode': 'major',
                        'label': f'ii-V-I / {target_name}',
                        'start_measure': chords[i].get('measure'),
                        'end_measure': chords[i + 2].get('measure'),
                    })
                elif c1['is_half_dim'] and c3['is_minor']:
                    # Harmonic minor ii-V-i
                    patterns.append({
                        'type': 'ii-V-i',
                        'indices': [i, i + 1, i + 2],
                        'target_key': target_name,
                        'mode': 'harmonic_minor',
                        'label': f'ii-V-i / {target_name}m',
                        'start_measure': chords[i].get('measure'),
                        'end_measure': chords[i + 2].get('measure'),
                    })
                elif c1['is_minor'] and c3['is_minor']:
                    # Minor ii-V-i (natural minor ii chord)
                    patterns.append({
                        'type': 'ii-V-i',
                        'indices': [i, i + 1, i + 2],
                        'target_key': target_name,
                        'mode': 'harmonic_minor',
                        'label': f'ii-V-i / {target_name}m',
                        'start_measure': chords[i].get('measure'),
                        'end_measure': chords[i + 2].get('measure'),
                    })

    return patterns


def detect_key_centers(chords: List[Dict], detected_key: str = None) -> List[Dict]:
    """Detect key center regions in a chord progression.

    Uses ii-V-I pattern detection plus chord-to-key fitting to identify
    where key center changes occur.

    Args:
        chords: List of analyzed chord dicts with 'symbol', 'measure', 'beat' fields.
        detected_key: The globally detected key (used as default).

    Returns:
        List of key center region dicts.
    """
    if not chords:
        return []

    patterns = detect_ii_v_i_patterns(chords)
    parsed = [_parse_chord(c.get('symbol', '')) for c in chords]

    # Build a map of chord index -> key center from patterns
    chord_key_map = {}
    for pat in patterns:
        target = pat['target_key']
        mode = pat['mode']
        for idx in pat['indices']:
            chord_key_map[idx] = (target, mode)

    # For chords not in patterns, determine key by checking which key
    # they fit best (major scale or harmonic minor scale)
    # Major scale intervals: 0, 2, 4, 5, 7, 9, 11
    major_scale = {0, 2, 4, 5, 7, 9, 11}
    # Harmonic minor intervals: 0, 2, 3, 5, 7, 8, 11
    h_minor_scale = {0, 2, 3, 5, 7, 8, 11}

    # Collect candidate keys from patterns
    pattern_keys = []
    for pat in patterns:
        pk = (pat['target_key'], pat['mode'])
        if pk not in pattern_keys:
            pattern_keys.append(pk)

    # If no patterns detected, use the global detected key
    if not pattern_keys and detected_key:
        dk = detected_key.split()
        key_name = dk[0] if dk else 'C'
        mode = 'minor' if 'minor' in detected_key.lower() else 'major'
        pattern_keys.append((key_name, mode))

    if not pattern_keys:
        pattern_keys.append(('C', 'major'))

    def _chord_fits_key(chord_pc, key_name, mode):
        key_pc = NOTE_TO_PC.get(key_name, 0)
        interval = (chord_pc - key_pc) % 12
        scale = h_minor_scale if 'minor' in mode else major_scale
        return interval in scale

    # Assign each chord to the best-fit key
    assignments = []
    for i, p in enumerate(parsed):
        if i in chord_key_map:
            assignments.append(chord_key_map[i])
        elif p:
            # Find best fitting key from candidates
            best = pattern_keys[0]
            for k, m in pattern_keys:
                if _chord_fits_key(p['root_pc'], k, m):
                    best = (k, m)
                    break
            assignments.append(best)
        else:
            assignments.append(pattern_keys[0])

    # Build regions from consecutive same-key assignments
    regions = []
    if not assignments:
        return regions

    current_key, current_mode = assignments[0]
    start_idx = 0

    for i in range(1, len(assignments)):
        k, m = assignments[i]
        if k != current_key or m != current_mode:
            regions.append({
                'start_index': start_idx,
                'end_index': i - 1,
                'start_measure': chords[start_idx].get('measure'),
                'end_measure': chords[i - 1].get('measure'),
                'key_center': current_key,
                'mode': current_mode,
                'confidence': 0.8 if any(
                    idx in chord_key_map for idx in range(start_idx, i)
                ) else 0.5,
            })
            current_key, current_mode = k, m
            start_idx = i

    # Final region
    regions.append({
        'start_index': start_idx,
        'end_index': len(assignments) - 1,
        'start_measure': chords[start_idx].get('measure'),
        'end_measure': chords[-1].get('measure'),
        'key_center': current_key,
        'mode': current_mode,
        'confidence': 0.8 if any(
            idx in chord_key_map for idx in range(start_idx, len(assignments))
        ) else 0.5,
    })

    return regions
