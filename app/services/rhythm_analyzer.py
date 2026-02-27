"""
Rhythm analysis service for HarmonyLab.

Analyzes rhythmic patterns from MIDI data to identify swing, straight,
and syncopation characteristics.
"""
import logging
from typing import List, Dict, Optional
from collections import Counter

logger = logging.getLogger(__name__)


def analyze_rhythm(
    note_onsets: List[float],
    ticks_per_beat: int = 480,
    time_sig_numerator: int = 4,
    time_sig_denominator: int = 4,
) -> Dict:
    """Analyze rhythmic patterns from note onset positions.

    Args:
        note_onsets: List of note onset times in ticks.
        ticks_per_beat: MIDI ticks per beat.
        time_sig_numerator: Top number of time signature.
        time_sig_denominator: Bottom number of time signature.

    Returns:
        Dict with rhythm analysis results.
    """
    if len(note_onsets) < 4:
        return {
            "feel": "insufficient_data",
            "swing_ratio": None,
            "syncopation_score": 0.0,
            "note_count": len(note_onsets),
            "details": "Need at least 4 notes for rhythm analysis",
        }

    sorted_onsets = sorted(note_onsets)

    # Calculate inter-onset intervals (IOIs)
    iois = [sorted_onsets[i+1] - sorted_onsets[i] for i in range(len(sorted_onsets) - 1)]
    iois = [ioi for ioi in iois if ioi > 0]  # Remove zero-length intervals

    if not iois:
        return {
            "feel": "insufficient_data",
            "swing_ratio": None,
            "syncopation_score": 0.0,
            "note_count": len(note_onsets),
            "details": "No valid inter-onset intervals",
        }

    eighth_note = ticks_per_beat / 2
    beat_ticks = ticks_per_beat

    # Swing detection: look at consecutive 8th note pairs
    # In swing, pairs of 8th notes have a long-short ratio > 1.2
    swing_ratios = []
    for i in range(len(iois) - 1):
        # Look for pairs that sum to approximately one beat
        pair_sum = iois[i] + iois[i+1]
        if abs(pair_sum - beat_ticks) < beat_ticks * 0.3:
            if iois[i+1] > 0:
                ratio = iois[i] / iois[i+1]
                swing_ratios.append(ratio)

    avg_swing_ratio = sum(swing_ratios) / len(swing_ratios) if swing_ratios else 1.0

    # Classify feel
    if avg_swing_ratio > 1.3:
        feel = "swing"
    elif avg_swing_ratio < 0.8:
        feel = "reverse_swing"
    else:
        feel = "straight"

    # Syncopation analysis: count notes on off-beats
    syncopated = 0
    on_beat = 0
    for onset in sorted_onsets:
        beat_pos = (onset % beat_ticks) / beat_ticks
        if beat_pos < 0.1 or abs(beat_pos - 0.5) < 0.1:
            on_beat += 1
        else:
            syncopated += 1

    total_notes = on_beat + syncopated
    syncopation_score = syncopated / total_notes if total_notes > 0 else 0.0

    # Rhythmic density (notes per beat)
    total_duration = sorted_onsets[-1] - sorted_onsets[0] if len(sorted_onsets) > 1 else beat_ticks
    density = len(sorted_onsets) / (total_duration / beat_ticks) if total_duration > 0 else 0

    # Common subdivisions
    subdivision_counts = Counter()
    for ioi in iois:
        beats = ioi / beat_ticks
        if abs(beats - 1.0) < 0.15:
            subdivision_counts['quarter'] += 1
        elif abs(beats - 0.5) < 0.1:
            subdivision_counts['eighth'] += 1
        elif abs(beats - 0.25) < 0.05:
            subdivision_counts['sixteenth'] += 1
        elif abs(beats - 0.333) < 0.05:
            subdivision_counts['triplet'] += 1
        elif abs(beats - 2.0) < 0.3:
            subdivision_counts['half'] += 1
        else:
            subdivision_counts['other'] += 1

    primary_subdivision = subdivision_counts.most_common(1)[0][0] if subdivision_counts else 'quarter'

    return {
        "feel": feel,
        "swing_ratio": round(avg_swing_ratio, 2),
        "syncopation_score": round(syncopation_score, 2),
        "note_count": len(sorted_onsets),
        "density_notes_per_beat": round(density, 2),
        "primary_subdivision": primary_subdivision,
        "subdivision_breakdown": dict(subdivision_counts),
        "details": _format_details(feel, avg_swing_ratio, syncopation_score, primary_subdivision),
    }


def analyze_rhythm_from_midi(file_path: str) -> Dict:
    """Analyze rhythm from a MIDI file.

    Args:
        file_path: Path to the MIDI file.

    Returns:
        Dict with per-track rhythm analysis.
    """
    from mido import MidiFile

    mid = MidiFile(file_path)
    tpb = mid.ticks_per_beat

    # Extract time signature
    time_sig_n, time_sig_d = 4, 4
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'time_signature':
                time_sig_n = msg.numerator
                time_sig_d = msg.denominator
                break

    # Collect note onsets from all tracks
    all_onsets = []
    track_analyses = []

    for i, track in enumerate(mid.tracks):
        onsets = []
        abs_time = 0
        for msg in track:
            abs_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                onsets.append(abs_time)

        if len(onsets) >= 4:
            analysis = analyze_rhythm(onsets, tpb, time_sig_n, time_sig_d)
            analysis['track_index'] = i
            analysis['track_name'] = track.name or f'Track {i}'
            track_analyses.append(analysis)
            all_onsets.extend(onsets)

    # Overall analysis
    overall = analyze_rhythm(all_onsets, tpb, time_sig_n, time_sig_d) if len(all_onsets) >= 4 else {
        "feel": "insufficient_data",
        "swing_ratio": None,
        "syncopation_score": 0.0,
        "note_count": len(all_onsets),
    }

    return {
        "overall": overall,
        "tracks": track_analyses,
        "time_signature": f"{time_sig_n}/{time_sig_d}",
        "ticks_per_beat": tpb,
    }


def _format_details(feel: str, ratio: float, syncopation: float, subdivision: str) -> str:
    """Format human-readable rhythm description."""
    parts = []
    if feel == 'swing':
        if ratio > 2.0:
            parts.append(f'Heavy swing feel (ratio {ratio:.1f}:1)')
        else:
            parts.append(f'Swing feel (ratio {ratio:.1f}:1)')
    elif feel == 'straight':
        parts.append('Straight feel (even subdivisions)')
    elif feel == 'reverse_swing':
        parts.append('Reverse swing feel')

    if syncopation > 0.4:
        parts.append(f'Highly syncopated ({int(syncopation*100)}% off-beat)')
    elif syncopation > 0.2:
        parts.append(f'Moderate syncopation ({int(syncopation*100)}% off-beat)')
    else:
        parts.append('Low syncopation')

    parts.append(f'Primary subdivision: {subdivision}')
    return '. '.join(parts)
