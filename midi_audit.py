"""
MIDI Audit Report Generator

Generates a comprehensive, human-readable audit report for MIDI files.
Designed to replace the broken audit report in HarmonyLab.

Usage:
    from midi_audit import generate_audit_report
    report = generate_audit_report("path/to/file.mid")
    
    # Or run directly:
    python midi_audit.py path/to/file.mid
"""

from mido import MidiFile, tempo2bpm
from typing import List, Dict, Any, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, asdict
import json
import sys


# ============================================================================
# NOTE & CHORD UTILITIES
# ============================================================================

NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
NOTE_NAMES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_to_note_name(midi_num: int, use_sharps: bool = False) -> str:
    """Convert MIDI number to note name with octave (e.g., 60 -> 'C4')."""
    names = NOTE_NAMES_SHARP if use_sharps else NOTE_NAMES
    note = names[midi_num % 12]
    octave = (midi_num // 12) - 1
    return f"{note}{octave}"


def midi_to_pitch_class(midi_num: int) -> str:
    """Convert MIDI number to pitch class without octave (e.g., 60 -> 'C')."""
    return NOTE_NAMES[midi_num % 12]


def get_intervals(notes: List[int]) -> Set[int]:
    """Get intervals from lowest note, mod 12."""
    if not notes:
        return set()
    bass = min(notes)
    return set((n - bass) % 12 for n in notes)


def identify_chord(notes: List[int]) -> Tuple[str, float]:
    """
    Identify chord from MIDI notes.
    Returns (chord_symbol, confidence).
    """
    if len(notes) < 2:
        return ("", 0.0)
    
    notes = sorted(set(notes))
    bass = min(notes)
    root_name = NOTE_NAMES[bass % 12]
    intervals = get_intervals(notes)
    
    # Chord templates (intervals from root)
    TEMPLATES = {
        # Full voicings
        'Maj7': {0, 4, 7, 11},
        'Maj9': {0, 4, 7, 11, 14},
        'm7': {0, 3, 7, 10},
        'm9': {0, 3, 7, 10, 14},
        '7': {0, 4, 7, 10},
        '9': {0, 4, 7, 10, 14},
        'ø7': {0, 3, 6, 10},
        'dim7': {0, 3, 6, 9},
        '6': {0, 4, 7, 9},
        'm6': {0, 3, 7, 9},
        'Maj': {0, 4, 7},
        'm': {0, 3, 7},
        'aug': {0, 4, 8},
        'dim': {0, 3, 6},
        'sus4': {0, 5, 7},
        'sus2': {0, 2, 7},
        '7sus4': {0, 5, 7, 10},
        'mMaj7': {0, 3, 7, 11},
        '13': {0, 4, 7, 10, 14, 21},
        'Maj13': {0, 4, 7, 11, 14, 21},
        'add9': {0, 4, 7, 14},
        'm(add9)': {0, 3, 7, 14},
    }
    
    # Shell voicings (common jazz left-hand voicings)
    SHELLS = {
        'Maj7': {0, 4, 11},      # root, 3rd, 7th
        'm7': {0, 3, 10},        # root, b3rd, b7th
        '7': {0, 4, 10},         # root, 3rd, b7th
        'ø7': {0, 3, 10},        # root, b3rd, b7th (same as m7 shell)
        'Maj': {0, 4},           # root, 3rd
        'm': {0, 3},             # root, b3rd
        '5': {0, 7},             # root, 5th (power chord)
    }
    
    # Normalize intervals
    intervals_mod12 = {i % 12 for i in intervals}
    
    # Try exact match
    for name, template in TEMPLATES.items():
        if intervals_mod12 == {i % 12 for i in template}:
            return (f"{root_name}{name}", 1.0)
    
    # Try shell voicing match
    for name, shell in SHELLS.items():
        if intervals_mod12 == shell:
            return (f"{root_name}{name}", 0.85)
    
    # Try subset match (voicing with missing notes)
    best_match = None
    best_score = 0
    
    for name, template in TEMPLATES.items():
        template_mod12 = {i % 12 for i in template}
        if intervals_mod12.issubset(template_mod12) and len(intervals_mod12) >= 2:
            score = len(intervals_mod12) / len(template_mod12)
            if score > best_score:
                best_score = score
                best_match = name
    
    if best_match and best_score >= 0.5:
        return (f"{root_name}{best_match}", best_score * 0.7)
    
    # Fallback based on 3rd
    if 3 in intervals_mod12:
        return (f"{root_name}m", 0.4)
    elif 4 in intervals_mod12:
        return (f"{root_name}Maj", 0.4)
    
    return (root_name, 0.2)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class NoteEvent:
    """A single note event."""
    midi_note: int
    note_name: str
    start_tick: int
    end_tick: int
    duration_ticks: int
    velocity: int
    track: int
    channel: int
    measure: int
    beat: float


@dataclass  
class ChordEvent:
    """A detected chord."""
    measure: int
    beat: float
    tick: int
    chord_symbol: str
    confidence: float
    notes: List[str]
    midi_notes: List[int]
    intervals: List[int]


@dataclass
class TrackInfo:
    """Information about a MIDI track."""
    index: int
    name: str
    total_events: int
    note_on_events: int
    note_off_events: int
    max_polyphony: int
    lowest_note: Optional[str]
    highest_note: Optional[str]


@dataclass
class MeasureAnalysis:
    """Analysis of a single measure."""
    measure_number: int
    start_tick: int
    end_tick: int
    start_beat: float
    end_beat: float
    notes: List[NoteEvent]
    chords: List[ChordEvent]
    unique_pitches: List[str]


# ============================================================================
# MAIN AUDIT FUNCTION
# ============================================================================

def generate_audit_report(file_path: str) -> Dict[str, Any]:
    """
    Generate a comprehensive audit report for a MIDI file.
    
    Returns a dictionary with:
    - file_info: Basic file metadata
    - tracks: Per-track analysis
    - measures: Measure-by-measure breakdown
    - chords: All detected chords
    - summary: Statistics and summary
    """
    
    midi = MidiFile(file_path)
    
    # ========================================================================
    # EXTRACT FILE INFO
    # ========================================================================
    
    tempo_bpm = 120
    time_sig_num = 4
    time_sig_denom = 4
    key_signature = "C"
    
    for track in midi.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo_bpm = int(tempo2bpm(msg.tempo))
            elif msg.type == 'time_signature':
                time_sig_num = msg.numerator
                time_sig_denom = msg.denominator
            elif msg.type == 'key_signature':
                key_signature = msg.key
    
    ticks_per_beat = midi.ticks_per_beat
    beats_per_measure = time_sig_num * (4 / time_sig_denom)
    ticks_per_measure = int(ticks_per_beat * beats_per_measure)
    
    file_info = {
        'filename': file_path.split('/')[-1].split('\\')[-1],
        'midi_type': midi.type,
        'tempo_bpm': tempo_bpm,
        'time_signature': f"{time_sig_num}/{time_sig_denom}",
        'key_signature': key_signature,
        'ticks_per_beat': ticks_per_beat,
        'ticks_per_measure': ticks_per_measure,
        'beats_per_measure': beats_per_measure,
        'num_tracks': len(midi.tracks),
    }
    
    # ========================================================================
    # ANALYZE TRACKS & COLLECT ALL NOTES
    # ========================================================================
    
    tracks_info = []
    all_note_events = []
    
    for track_idx, track in enumerate(midi.tracks):
        abs_time = 0
        active_notes = {}  # midi_note -> (start_tick, velocity)
        max_polyphony = 0
        note_on_count = 0
        note_off_count = 0
        track_notes = []
        
        for msg in track:
            abs_time += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                active_notes[msg.note] = (abs_time, msg.velocity, msg.channel)
                max_polyphony = max(max_polyphony, len(active_notes))
                note_on_count += 1
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                note_off_count += 1
                if msg.note in active_notes:
                    start_tick, velocity, channel = active_notes.pop(msg.note)
                    
                    # Calculate measure and beat
                    measure = int(start_tick // ticks_per_measure) + 1
                    beat = (start_tick % ticks_per_measure) / ticks_per_beat + 1
                    
                    note_event = NoteEvent(
                        midi_note=msg.note,
                        note_name=midi_to_note_name(msg.note),
                        start_tick=start_tick,
                        end_tick=abs_time,
                        duration_ticks=abs_time - start_tick,
                        velocity=velocity,
                        track=track_idx,
                        channel=channel,
                        measure=measure,
                        beat=round(beat, 2)
                    )
                    track_notes.append(note_event)
                    all_note_events.append(note_event)
        
        # Track summary
        lowest = min((n.midi_note for n in track_notes), default=None)
        highest = max((n.midi_note for n in track_notes), default=None)
        
        tracks_info.append(TrackInfo(
            index=track_idx,
            name=track.name or f"Track {track_idx}",
            total_events=len(track),
            note_on_events=note_on_count,
            note_off_events=note_off_count,
            max_polyphony=max_polyphony,
            lowest_note=midi_to_note_name(lowest) if lowest else None,
            highest_note=midi_to_note_name(highest) if highest else None
        ))
    
    # Sort all notes by start time
    all_note_events.sort(key=lambda x: x.start_tick)
    
    # Calculate total measures
    if all_note_events:
        last_tick = max(n.end_tick for n in all_note_events)
        total_measures = int(last_tick // ticks_per_measure) + 1
    else:
        total_measures = 0
    
    file_info['total_measures'] = total_measures
    file_info['total_beats'] = round(total_measures * beats_per_measure, 2)
    
    # ========================================================================
    # DETECT CHORDS (combining notes from all tracks)
    # ========================================================================
    
    CHORD_WINDOW = 30  # ticks - notes within this window are "simultaneous"
    
    chord_events = []
    i = 0
    
    while i < len(all_note_events):
        start_tick = all_note_events[i].start_tick
        chord_notes = []
        
        # Collect all notes starting within window
        j = i
        while j < len(all_note_events) and all_note_events[j].start_tick - start_tick <= CHORD_WINDOW:
            chord_notes.append(all_note_events[j].midi_note)
            j += 1
        
        if len(chord_notes) >= 2:
            unique_notes = sorted(set(chord_notes))
            chord_symbol, confidence = identify_chord(unique_notes)
            
            measure = int(start_tick // ticks_per_measure) + 1
            beat = (start_tick % ticks_per_measure) / ticks_per_beat + 1
            
            # Calculate intervals for display
            bass = min(unique_notes)
            intervals = sorted((n - bass) % 12 for n in unique_notes)
            
            chord_events.append(ChordEvent(
                measure=measure,
                beat=round(beat, 2),
                tick=start_tick,
                chord_symbol=chord_symbol,
                confidence=round(confidence, 2),
                notes=[midi_to_note_name(n) for n in unique_notes],
                midi_notes=unique_notes,
                intervals=intervals
            ))
        
        i = j if j > i else i + 1
    
    # Remove duplicate chords at same position
    filtered_chords = []
    for chord in chord_events:
        if not filtered_chords or (
            filtered_chords[-1].measure != chord.measure or
            abs(filtered_chords[-1].beat - chord.beat) > 0.25
        ):
            filtered_chords.append(chord)
    
    chord_events = filtered_chords
    
    # ========================================================================
    # ORGANIZE BY MEASURE
    # ========================================================================
    
    measures_analysis = {}
    
    for m in range(1, total_measures + 1):
        start_tick = (m - 1) * ticks_per_measure
        end_tick = m * ticks_per_measure
        
        # Notes in this measure
        measure_notes = [n for n in all_note_events if n.measure == m]
        
        # Chords in this measure
        measure_chords = [c for c in chord_events if c.measure == m]
        
        # Unique pitches
        unique_pitches = sorted(set(n.note_name for n in measure_notes))
        
        measures_analysis[m] = MeasureAnalysis(
            measure_number=m,
            start_tick=start_tick,
            end_tick=end_tick,
            start_beat=(m - 1) * beats_per_measure,
            end_beat=m * beats_per_measure,
            notes=measure_notes,
            chords=measure_chords,
            unique_pitches=unique_pitches
        )
    
    # ========================================================================
    # BUILD FINAL REPORT
    # ========================================================================
    
    # Convert dataclasses to dicts for JSON serialization
    def to_dict(obj):
        if hasattr(obj, '__dataclass_fields__'):
            return {k: to_dict(v) for k, v in asdict(obj).items()}
        elif isinstance(obj, list):
            return [to_dict(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: to_dict(v) for k, v in obj.items()}
        return obj
    
    report = {
        'file_info': file_info,
        'tracks': [to_dict(t) for t in tracks_info],
        'chords': [to_dict(c) for c in chord_events],
        'measures': {m: to_dict(analysis) for m, analysis in measures_analysis.items()},
        'summary': {
            'total_notes': len(all_note_events),
            'total_chords_detected': len(chord_events),
            'measures_with_chords': len(set(c.measure for c in chord_events)),
            'unique_chord_symbols': list(set(c.chord_symbol for c in chord_events)),
            'average_confidence': round(
                sum(c.confidence for c in chord_events) / len(chord_events) if chord_events else 0,
                2
            ),
        }
    }
    
    return report


def format_audit_text(report: Dict[str, Any], max_measures: int = 32) -> str:
    """
    Format audit report as human-readable text.
    """
    lines = []
    fi = report['file_info']
    
    lines.append("=" * 70)
    lines.append(f"MIDI AUDIT REPORT: {fi['filename']}")
    lines.append("=" * 70)
    lines.append("")
    
    # File Info
    lines.append("FILE INFORMATION")
    lines.append("-" * 40)
    lines.append(f"  Tempo:           {fi['tempo_bpm']} BPM")
    lines.append(f"  Time Signature:  {fi['time_signature']}")
    lines.append(f"  Key Signature:   {fi['key_signature']}")
    lines.append(f"  Total Measures:  {fi['total_measures']}")
    lines.append(f"  Ticks/Beat:      {fi['ticks_per_beat']}")
    lines.append(f"  Ticks/Measure:   {fi['ticks_per_measure']}")
    lines.append("")
    
    # Tracks
    lines.append("TRACKS")
    lines.append("-" * 40)
    for t in report['tracks']:
        lines.append(f"  Track {t['index']}: {t['name']}")
        lines.append(f"    Notes: {t['note_on_events']}  |  Max Polyphony: {t['max_polyphony']}  |  Range: {t['lowest_note']} - {t['highest_note']}")
    lines.append("")
    
    # Summary
    s = report['summary']
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total Notes:         {s['total_notes']}")
    lines.append(f"  Chords Detected:     {s['total_chords_detected']}")
    lines.append(f"  Avg Confidence:      {s['average_confidence']:.0%}")
    lines.append(f"  Unique Chord Types:  {len(s['unique_chord_symbols'])}")
    lines.append("")
    
    # Chords by Measure
    lines.append("=" * 70)
    lines.append("CHORD PROGRESSION")
    lines.append("=" * 70)
    lines.append("")
    
    current_measure = 0
    for chord in report['chords'][:max_measures * 4]:  # Limit output
        if chord['measure'] != current_measure:
            if current_measure > 0:
                lines.append("")
            current_measure = chord['measure']
            if current_measure > max_measures:
                lines.append(f"... (showing first {max_measures} measures)")
                break
            lines.append(f"MEASURE {current_measure}")
            lines.append("-" * 40)
        
        conf_str = f" ({chord['confidence']:.0%})" if chord['confidence'] < 0.9 else ""
        lines.append(f"  Beat {chord['beat']}: {chord['chord_symbol']}{conf_str}")
        lines.append(f"    Notes: {', '.join(chord['notes'])}")
        lines.append(f"    Intervals: {chord['intervals']}")
    
    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python midi_audit.py <path_to_midi_file> [--json]")
        print("")
        print("Options:")
        print("  --json    Output as JSON instead of text")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_json = "--json" in sys.argv
    
    try:
        report = generate_audit_report(file_path)
        
        if output_json:
            # For JSON output, simplify the measures (too verbose otherwise)
            simplified = {
                'file_info': report['file_info'],
                'tracks': report['tracks'],
                'chords': report['chords'],
                'summary': report['summary']
            }
            print(json.dumps(simplified, indent=2))
        else:
            print(format_audit_text(report))
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
