"""
MIDI Parser Service - CORRECTED VERSION

Fixes from diagnostic analysis:
1. Combines notes from ALL tracks at same time point (not just one track)
2. Uses lowest note as bass/root reference
3. Handles 2/2 time signature correctly
4. Detects jazz shell voicings (root + 3rd/7th patterns)
"""
from mido import MidiFile, tempo2bpm
from typing import List, Optional, Tuple, Dict, Set
from pydantic import BaseModel
from collections import defaultdict


class ChordData(BaseModel):
    """Parsed chord data from MIDI."""
    measure_number: int
    beat_position: float
    chord_symbol: str
    midi_notes: List[int]
    confidence: float = 1.0  # How confident we are in the detection


class ParsedSong(BaseModel):
    """Complete parsed song data."""
    title: Optional[str]
    tempo: Optional[int]
    time_signature: str
    total_measures: int
    ticks_per_beat: int
    chords: List[ChordData]


# Note names for chord symbols
NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
NOTE_NAMES_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_note_to_name(note: int, prefer_sharp: bool = False) -> str:
    """Convert MIDI note number to note name."""
    names = NOTE_NAMES_SHARP if prefer_sharp else NOTE_NAMES
    return names[note % 12]


def get_intervals_from_bass(notes: List[int]) -> Set[int]:
    """Get intervals (in semitones mod 12) from the bass note."""
    if not notes:
        return set()
    bass = min(notes)
    return set((n - bass) % 12 for n in notes)


def identify_chord_from_intervals(bass_note: int, intervals: Set[int]) -> Tuple[str, str, float]:
    """
    Identify chord from bass note and intervals.
    Returns (root_name, chord_type, confidence).
    
    Jazz voicings often omit notes:
    - Shell voicing: root + 3rd + 7th (omit 5th)
    - Root + 7th only
    - Root + 3rd only
    """
    root_name = NOTE_NAMES[bass_note % 12]
    
    # Full chord templates (intervals from root)
    CHORD_TEMPLATES = {
        # Major family
        'Maj7': {0, 4, 7, 11},
        'Maj9': {0, 4, 7, 11, 14},
        'Maj6': {0, 4, 7, 9},
        '6/9': {0, 4, 7, 9, 14},
        'Maj': {0, 4, 7},
        
        # Minor family
        'm7': {0, 3, 7, 10},
        'm9': {0, 3, 7, 10, 14},
        'm6': {0, 3, 7, 9},
        'm': {0, 3, 7},
        'mMaj7': {0, 3, 7, 11},
        
        # Dominant family
        '7': {0, 4, 7, 10},
        '9': {0, 4, 7, 10, 14},
        '13': {0, 4, 7, 10, 14, 21},
        '7sus4': {0, 5, 7, 10},
        '7#9': {0, 4, 7, 10, 15},
        '7b9': {0, 4, 7, 10, 13},
        '7alt': {0, 4, 8, 10},  # altered dominant
        
        # Diminished/Half-diminished
        'ø7': {0, 3, 6, 10},  # half-diminished
        'dim7': {0, 3, 6, 9},
        'dim': {0, 3, 6},
        
        # Augmented
        'aug': {0, 4, 8},
        'aug7': {0, 4, 8, 10},
        
        # Suspended
        'sus4': {0, 5, 7},
        'sus2': {0, 2, 7},
    }
    
    # Shell voicing patterns (common in jazz piano left hand)
    SHELL_VOICINGS = {
        # Root + 3rd + 7th (no 5th)
        'Maj7': {0, 4, 11},
        'm7': {0, 3, 10},
        '7': {0, 4, 10},
        'ø7': {0, 3, 10},  # half-dim without b5
        
        # Root + 7th only
        'Maj7': {0, 11},
        'm7': {0, 10},
        '7': {0, 10},
        
        # Root + 3rd only
        'Maj': {0, 4},
        'm': {0, 3},
        
        # Root + 5th (power chord / bass pattern)
        '5': {0, 7},
        
        # 3rd + 7th (rootless, common in left hand)
        # These need special handling - bass might be the 3rd
    }
    
    # Normalize intervals to mod 12
    intervals_mod12 = {i % 12 for i in intervals}
    
    # Try exact match first
    for chord_type, template in CHORD_TEMPLATES.items():
        if intervals_mod12 == {i % 12 for i in template}:
            return (root_name, chord_type, 1.0)
    
    # Try shell voicing matches
    shell_matches = []
    for chord_type, shell in SHELL_VOICINGS.items():
        if intervals_mod12 == shell:
            shell_matches.append((chord_type, 0.8))
    
    if shell_matches:
        # Return the most specific match
        return (root_name, shell_matches[0][0], shell_matches[0][1])
    
    # Try subset matching (voicing with some notes missing)
    best_match = None
    best_score = 0
    
    for chord_type, template in CHORD_TEMPLATES.items():
        template_mod12 = {i % 12 for i in template}
        if intervals_mod12.issubset(template_mod12):
            # Score based on how many notes match
            score = len(intervals_mod12) / len(template_mod12)
            if score > best_score:
                best_score = score
                best_match = chord_type
    
    if best_match and best_score >= 0.5:
        return (root_name, best_match, best_score * 0.7)
    
    # Fallback: guess based on 3rd
    if 3 in intervals_mod12:
        return (root_name, 'm', 0.4)
    elif 4 in intervals_mod12:
        return (root_name, 'Maj', 0.4)
    
    # Can't identify
    return (root_name, '', 0.2)


def parse_midi_file(file_path: str) -> ParsedSong:
    """
    Parse a MIDI file and extract chord progressions.
    
    CORRECTED: Combines notes from ALL tracks at each time point.
    """
    midi = MidiFile(file_path)
    
    # Get tempo and time signature
    tempo = 120
    time_sig_num = 4
    time_sig_denom = 4
    
    for track in midi.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = int(tempo2bpm(msg.tempo))
            elif msg.type == 'time_signature':
                time_sig_num = msg.numerator
                time_sig_denom = msg.denominator
    
    time_signature = f"{time_sig_num}/{time_sig_denom}"
    
    # Calculate ticks per measure
    # For 2/2: 2 half notes = 4 quarter notes worth
    # For 4/4: 4 quarter notes
    beats_per_measure = time_sig_num * (4 / time_sig_denom)
    ticks_per_measure = int(midi.ticks_per_beat * beats_per_measure)
    
    # Collect ALL note events from ALL tracks with absolute timing
    all_note_events = []
    
    for track_idx, track in enumerate(midi.tracks):
        abs_time = 0
        active_notes = {}  # note -> start_time
        
        for msg in track:
            abs_time += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                active_notes[msg.note] = abs_time
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active_notes:
                    start_time = active_notes.pop(msg.note)
                    all_note_events.append({
                        'note': msg.note,
                        'start': start_time,
                        'end': abs_time,
                        'track': track_idx
                    })
    
    # Sort by start time
    all_note_events.sort(key=lambda x: x['start'])
    
    # Group notes that start at the same time (within tolerance)
    CHORD_WINDOW_TICKS = 30  # Notes within 30 ticks are "simultaneous"
    
    chords_data = []
    i = 0
    
    while i < len(all_note_events):
        # Collect all notes starting within the window
        chord_start = all_note_events[i]['start']
        chord_notes = []
        
        j = i
        while j < len(all_note_events) and all_note_events[j]['start'] - chord_start <= CHORD_WINDOW_TICKS:
            chord_notes.append(all_note_events[j]['note'])
            j += 1
        
        # Only process if we have 2+ notes (could be a chord)
        if len(chord_notes) >= 2:
            # Get unique notes
            unique_notes = sorted(set(chord_notes))
            
            # Calculate measure and beat
            measure = int(chord_start // ticks_per_measure) + 1
            beat_in_measure = (chord_start % ticks_per_measure) / midi.ticks_per_beat + 1
            
            # Identify chord
            bass_note = min(unique_notes)
            intervals = get_intervals_from_bass(unique_notes)
            root_name, chord_type, confidence = identify_chord_from_intervals(bass_note, intervals)
            
            # Only add if we could identify something
            if root_name:
                chord_symbol = f"{root_name}{chord_type}" if chord_type else root_name
                
                # Avoid duplicate chords at same position
                if not chords_data or (
                    chords_data[-1].measure_number != measure or 
                    abs(chords_data[-1].beat_position - beat_in_measure) > 0.25
                ):
                    chords_data.append(ChordData(
                        measure_number=measure,
                        beat_position=round(beat_in_measure, 2),
                        chord_symbol=chord_symbol,
                        midi_notes=unique_notes,
                        confidence=confidence
                    ))
        
        # Move to next group
        i = j if j > i else i + 1
    
    # Calculate total measures
    total_measures = 0
    if all_note_events:
        last_time = max(e['end'] for e in all_note_events)
        total_measures = int(last_time // ticks_per_measure) + 1
    
    return ParsedSong(
        title=None,
        tempo=tempo,
        time_signature=time_signature,
        total_measures=total_measures,
        ticks_per_beat=midi.ticks_per_beat,
        chords=chords_data
    )


def parse_midi_file_detailed(file_path: str) -> dict:
    """
    Parse MIDI and return detailed analysis for debugging/audit.
    """
    midi = MidiFile(file_path)
    
    # Basic info
    tempo = 120
    time_sig_num = 4
    time_sig_denom = 4
    
    for track in midi.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                tempo = int(tempo2bpm(msg.tempo))
            elif msg.type == 'time_signature':
                time_sig_num = msg.numerator
                time_sig_denom = msg.denominator
    
    beats_per_measure = time_sig_num * (4 / time_sig_denom)
    ticks_per_measure = int(midi.ticks_per_beat * beats_per_measure)
    
    # Track analysis
    tracks_info = []
    for track_idx, track in enumerate(midi.tracks):
        note_on_count = sum(1 for m in track if m.type == 'note_on' and m.velocity > 0)
        tracks_info.append({
            'index': track_idx,
            'name': track.name or f'Track {track_idx}',
            'note_events': note_on_count
        })
    
    # Get parsed chords
    parsed = parse_midi_file(file_path)
    
    # Organize by measure
    measures = defaultdict(list)
    for chord in parsed.chords:
        measures[chord.measure_number].append({
            'beat': chord.beat_position,
            'symbol': chord.chord_symbol,
            'notes': [midi_note_to_name(n) + str(n // 12 - 1) for n in chord.midi_notes],
            'midi_notes': chord.midi_notes,
            'confidence': chord.confidence
        })
    
    return {
        'filename': file_path,
        'tempo': tempo,
        'time_signature': f"{time_sig_num}/{time_sig_denom}",
        'ticks_per_beat': midi.ticks_per_beat,
        'ticks_per_measure': ticks_per_measure,
        'total_measures': parsed.total_measures,
        'tracks': tracks_info,
        'measures': dict(measures),
        'total_chords_detected': len(parsed.chords)
    }


# Convenience function for testing
if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python midi_parser.py <path_to_midi>")
        sys.exit(1)
    
    result = parse_midi_file_detailed(sys.argv[1])
    
    print(f"\n{'='*60}")
    print(f"MIDI PARSER ANALYSIS: {result['filename']}")
    print(f"{'='*60}")
    print(f"Tempo: {result['tempo']} BPM")
    print(f"Time Signature: {result['time_signature']}")
    print(f"Ticks per beat: {result['ticks_per_beat']}")
    print(f"Total Measures: {result['total_measures']}")
    print(f"Total Chords Detected: {result['total_chords_detected']}")
    print(f"\nTracks:")
    for t in result['tracks']:
        print(f"  {t['index']}: {t['name']} ({t['note_events']} notes)")
    
    print(f"\n{'='*60}")
    print("CHORDS BY MEASURE (first 16 measures)")
    print(f"{'='*60}")
    
    for measure_num in sorted(result['measures'].keys())[:16]:
        chords = result['measures'][measure_num]
        print(f"\nMeasure {measure_num}:")
        for c in chords:
            conf = f" (conf: {c['confidence']:.0%})" if c['confidence'] < 1.0 else ""
            print(f"  Beat {c['beat']}: {c['symbol']}{conf}")
            print(f"    Notes: {', '.join(c['notes'])}")
