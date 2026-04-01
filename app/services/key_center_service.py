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

    # Handle both 'm' and '-' as minor notation (iReal/MuseScore use '-')
    is_minor = (quality.startswith('m') and not quality.startswith('maj')) or quality.startswith('-')
    is_dom7 = (quality.startswith('7') or quality == '9' or quality == '13'
               or quality == '11' or quality.startswith('7') or quality.startswith('9sus')
               or quality.startswith('13sus'))
    # Handle '^' and 't' as maj7 notation (MuseScore triangle = '^'; 't7' = triangle 7)
    is_maj7 = (quality.startswith('maj7') or quality.startswith('Maj7') or quality.startswith('M7')
               or quality.startswith('^') or quality == 't7' or quality == 'T7')
    is_half_dim = 'm7b5' in quality or '-7b5' in quality or quality.startswith('ø')
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


def _are_relative_keys(key1: str, mode1: str, key2: str, mode2: str) -> bool:
    """Check if two keys are relative major/minor (share same key signature)."""
    if key1 == key2:
        return True
    pc1 = NOTE_TO_PC.get(key1, -1)
    pc2 = NOTE_TO_PC.get(key2, -1)
    if pc1 < 0 or pc2 < 0:
        return False
    interval = (pc1 - pc2) % 12
    # Relative major/minor are 3 semitones apart
    is_major_minor_pair = (mode1 == 'major' and 'minor' in mode2) or ('minor' in mode1 and mode2 == 'major')
    if is_major_minor_pair:
        return interval == 3 or interval == 9
    return False


def detect_key_centers(chords: List[Dict], detected_key: str = None) -> List[Dict]:
    """Detect key center regions in a chord progression.

    Uses ii-V-I pattern detection plus chord-to-key fitting to identify
    where key center changes occur. Merges relative major/minor regions
    to avoid over-fragmentation.

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

    # Step 1: Determine home key from last chord (90% jazz rule: last chord = tonic)
    home_key = 'C'
    home_mode = 'major'
    for p in reversed(parsed):
        if p:
            home_key = p['root_name']
            home_mode = 'minor' if (p['is_minor'] or p['is_half_dim']) else 'major'
            break

    # Refine with detected_key if it's in the same tonal center
    if detected_key:
        dk = detected_key.split()
        if dk:
            det_name = dk[0]
            det_mode = 'minor' if 'minor' in detected_key.lower() else 'major'
            if _are_relative_keys(det_name, det_mode, home_key, home_mode):
                home_key = det_name
                home_mode = det_mode

    # Step 2: Build chord-key map from patterns (first pattern wins per chord)
    chord_key_map = {}
    for pat in patterns:
        target = pat['target_key']
        mode = pat['mode']
        for idx in pat['indices']:
            if idx not in chord_key_map:
                chord_key_map[idx] = (target, mode)

    # Scales for fitting
    major_scale = {0, 2, 4, 5, 7, 9, 11}
    h_minor_scale = {0, 2, 3, 5, 7, 8, 11}

    # Collect candidate keys from patterns
    pattern_keys = []
    for pat in patterns:
        pk = (pat['target_key'], pat['mode'])
        if pk not in pattern_keys:
            pattern_keys.append(pk)

    if not pattern_keys:
        pattern_keys.append((home_key, home_mode))

    # Step 2.5: Sliding window key discovery — when pattern detection finds < 2 candidates,
    # score all 24 keys against windows of chords to discover additional key regions.
    # This handles songs where chord symbols don't form clean ii-V-I patterns.
    if len(pattern_keys) < 2 and len(parsed) >= 4:
        window_size = 4
        for i in range(0, len(parsed), window_size):
            window = parsed[i:i + window_size]
            best_wk, best_score = pattern_keys[0], -1
            for key_name in NOTE_NAMES:
                key_pc_val = NOTE_TO_PC[key_name]
                for mode_name, scale_pcs in [('major', major_scale), ('minor', h_minor_scale)]:
                    score = sum(
                        1 for p in window if p and (p['root_pc'] - key_pc_val) % 12 in scale_pcs
                    )
                    if score > best_score:
                        best_score, best_wk = score, (key_name, mode_name)
            if best_wk not in pattern_keys:
                pattern_keys.append(best_wk)

    def _chord_fits_key(chord_pc, key_name, mode):
        key_pc = NOTE_TO_PC.get(key_name, 0)
        interval = (chord_pc - key_pc) % 12
        scale = h_minor_scale if 'minor' in mode else major_scale
        return interval in scale

    # Step 3: Assign each chord to the best-fit key using scoring
    # Score each candidate key for each chord; prefer home key on ties
    assignments = []
    for i, p in enumerate(parsed):
        if i in chord_key_map:
            assignments.append(chord_key_map[i])
        elif p:
            best = pattern_keys[0]
            best_score = -1
            for k, m in pattern_keys:
                score = 0
                if _chord_fits_key(p['root_pc'], k, m):
                    score += 2
                # Bonus for home key to prevent fragmentation
                if k == home_key and m == home_mode:
                    score += 1
                # Bonus for keys with strong pattern evidence nearby
                for pat in patterns:
                    if pat['target_key'] == k and abs(i - pat['indices'][1]) <= 4:
                        score += 1
                        break
                if score > best_score:
                    best_score = score
                    best = (k, m)
            assignments.append(best)
        else:
            assignments.append((home_key, home_mode))

    # Step 4: Build raw regions from consecutive same-key assignments
    raw_regions = []
    if not assignments:
        return raw_regions

    current_key, current_mode = assignments[0]
    start_idx = 0

    for i in range(1, len(assignments)):
        k, m = assignments[i]
        if k != current_key or m != current_mode:
            raw_regions.append({
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

    raw_regions.append({
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

    # Step 5: Merge adjacent relative major/minor regions
    # Use the home key's label for the merged region
    merged = []
    for r in raw_regions:
        if merged and _are_relative_keys(
            merged[-1]['key_center'], merged[-1]['mode'],
            r['key_center'], r['mode']
        ):
            merged[-1]['end_index'] = r['end_index']
            merged[-1]['end_measure'] = r['end_measure']
            merged[-1]['confidence'] = max(merged[-1]['confidence'], r['confidence'])
            # Prefer home key label for the merged region
            if _are_relative_keys(r['key_center'], r['mode'], home_key, home_mode):
                merged[-1]['key_center'] = home_key
                merged[-1]['mode'] = home_mode
        else:
            merged.append(dict(r))

    # Step 6: Absorb tiny regions (< 3 chords) into their nearest neighbor
    if len(merged) > 1:
        final = []
        for r in merged:
            size = r['end_index'] - r['start_index'] + 1
            if size < 3 and final:
                # Absorb into previous region
                final[-1]['end_index'] = r['end_index']
                final[-1]['end_measure'] = r['end_measure']
            else:
                final.append(r)
        # Also check if the last region is tiny and should merge backward
        if len(final) > 1:
            last = final[-1]
            if last['end_index'] - last['start_index'] + 1 < 3:
                final[-2]['end_index'] = last['end_index']
                final[-2]['end_measure'] = last['end_measure']
                final.pop()
        merged = final

    # Step 7: Final pass — merge consecutive same-key regions
    # (can arise after absorbing tiny regions)
    if len(merged) > 1:
        consolidated = [merged[0]]
        for r in merged[1:]:
            prev = consolidated[-1]
            if r['key_center'] == prev['key_center'] and r['mode'] == prev['mode']:
                prev['end_index'] = r['end_index']
                prev['end_measure'] = r['end_measure']
                prev['confidence'] = max(prev['confidence'], r['confidence'])
            else:
                consolidated.append(dict(r))
        merged = consolidated

    return merged


def detect_turnarounds(chords: List[Dict]) -> List[Dict]:
    """
    Detect iii-vi-ii-V turnaround patterns in a chord list.

    Jazz turnaround: three minor 7ths descending in 4ths, resolving to a dom7.
    Interval pattern (root PCs): iii → vi (down P5/up P4) → ii (down P5/up P4) → V (down P5/up P4).
    """
    turnarounds = []
    if len(chords) < 4:
        return turnarounds

    def get_pc(symbol: str) -> Optional[int]:
        m = re.match(r'^([A-G][#b]?)', symbol or '')
        if not m:
            return None
        return NOTE_TO_PC.get(m.group(1))

    def quality_type(symbol: str) -> str:
        q = re.sub(r'^[A-G][#b]?', '', symbol or '')
        q = re.sub(r'[/\\].*', '', q)  # strip slash bass
        if re.match(r'^(m7|m9|m11|-7|-9)', q):
            return 'm7'
        if re.match(r'^(7|9|13|7b9|7#9|7alt|7sus4)', q):
            return 'dom7'
        return 'other'

    for i in range(len(chords) - 3):
        c1, c2, c3, c4 = chords[i], chords[i+1], chords[i+2], chords[i+3]
        syms = [c.get('symbol', '') for c in (c1, c2, c3, c4)]
        types = [quality_type(s) for s in syms]

        # Pattern: m7, m7, m7, dom7 (or m7, m7, dom7, dom7 for ii-V-ii-V variant)
        if types[:3] == ['m7', 'm7', 'm7'] and types[3] == 'dom7':
            pcs = [get_pc(s) for s in syms]
            if None in pcs:
                continue
            # Verify descending fourths: each root is 5 semitones above the next (= P4 down)
            intervals = [(pcs[j] - pcs[j+1]) % 12 for j in range(3)]
            if all(iv == 5 for iv in intervals):
                turnarounds.append({
                    'start_measure': c1.get('measure', i),
                    'end_measure': c4.get('measure', i + 3),
                    'start_index': i,
                    'end_index': i + 3,
                    'type': 'iii-vi-ii-V',
                    'label': f"{syms[0]} – {syms[1]} – {syms[2]} – {syms[3]}",
                })

    return turnarounds
