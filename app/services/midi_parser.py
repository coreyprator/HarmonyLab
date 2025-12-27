"""
MIDI Parser Service

Uses the `mido` library to:
1. Parse MIDI files
2. Extract chord data from chord tracks
3. Detect time signature and tempo
4. Map MIDI notes to chord symbols
"""
from mido import MidiFile, tempo2bpm
from typing import List, Optional, Tuple, Dict
from pydantic import BaseModel
from collections import defaultdict


class ChordData(BaseModel):
    """Parsed chord data from MIDI."""
    measure_number: int
    beat_position: float
    chord_symbol: str
    midi_notes: List[int]  # Original notes for verification


class SectionData(BaseModel):
    """Section data from MIDI."""
    name: str
    section_order: int
    measures: List[int]  # Measure numbers


class ParsedSong(BaseModel):
    """Complete parsed song data."""
    title: Optional[str]
    tempo: Optional[int]
    time_signature: str
    total_measures: int
    chords: List[ChordData]


# Standard chord templates (intervals from root in semitones)
CHORD_TEMPLATES = {
    # Triads
    'Maj': [0, 4, 7],
    'm': [0, 3, 7],
    'dim': [0, 3, 6],
    'aug': [0, 4, 8],
    
    # Seventh chords
    'Maj7': [0, 4, 7, 11],
    'm7': [0, 3, 7, 10],
    '7': [0, 4, 7, 10],
    'ø7': [0, 3, 6, 10],  # half-diminished
    'dim7': [0, 3, 6, 9],
    'mMaj7': [0, 3, 7, 11],
    
    # Sixth chords
    '6': [0, 4, 7, 9],
    'm6': [0, 3, 7, 9],
    
    # Extended chords (9th, 11th, 13th)
    '9': [0, 4, 7, 10, 14],
    'Maj9': [0, 4, 7, 11, 14],
    'm9': [0, 3, 7, 10, 14],
    '11': [0, 4, 7, 10, 14, 17],
    'm11': [0, 3, 7, 10, 14, 17],
    '13': [0, 4, 7, 10, 14, 21],
    'Maj13': [0, 4, 7, 11, 14, 21],
    
    # Suspended chords
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    '7sus4': [0, 5, 7, 10],
}

NOTE_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def midi_notes_to_intervals(notes: List[int]) -> List[int]:
    """Convert MIDI note numbers to intervals from the root."""
    if not notes:
        return []
    
    notes = sorted(set(notes))
    root = notes[0]
    intervals = [(note - root) % 12 for note in notes]
    return sorted(set(intervals))


def identify_chord(notes: List[int]) -> Tuple[str, str]:
    """
    Identify chord from MIDI notes.
    Returns (root_name, chord_type).
    """
    if not notes:
        return ("", "")
    
    notes = sorted(set(notes))
    root_midi = notes[0]
    root_name = NOTE_NAMES[root_midi % 12]
    
    intervals = midi_notes_to_intervals(notes)
    
    # Try to match chord template
    for chord_type, template in CHORD_TEMPLATES.items():
        if intervals == template:
            return (root_name, chord_type)
    
    # Try partial matches (for voicings with missing notes)
    for chord_type, template in CHORD_TEMPLATES.items():
        if set(intervals).issubset(set(template)):
            return (root_name, chord_type)
    
    # Default to major/minor based on third
    if 3 in intervals:
        return (root_name, "m")
    elif 4 in intervals:
        return (root_name, "Maj")
    
    return (root_name, "")


def parse_midi_file(file_path: str) -> ParsedSong:
    """
    Parse a MIDI file and extract chord progressions.
    
    Args:
        file_path: Path to MIDI file
        
    Returns:
        ParsedSong with all extracted data
    """
    midi = MidiFile(file_path)
    
    # Get tempo and time signature from first track
    tempo = 120  # Default
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
    
    # Find the track with the most simultaneous notes (likely the chord track)
    chord_track = None
    max_polyphony = 0
    
    for track in midi.tracks:
        active_notes = []
        max_active = 0
        
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_notes.append(msg.note)
                max_active = max(max_active, len(active_notes))
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active_notes:
                    active_notes.remove(msg.note)
        
        if max_active > max_polyphony:
            max_polyphony = max_active
            chord_track = track
    
    if not chord_track:
        # No suitable track found, use first track with notes
        for track in midi.tracks:
            has_notes = any(msg.type in ['note_on', 'note_off'] for msg in track)
            if has_notes:
                chord_track = track
                break
    
    # Extract chords from the selected track
    chords_data = extract_chords_from_track(chord_track, midi.ticks_per_beat, time_sig_num)
    
    # Calculate total measures
    if chords_data:
        total_measures = max(chord.measure_number for chord in chords_data)
    else:
        total_measures = 0
    
    return ParsedSong(
        title=None,  # MIDI files usually don't have metadata
        tempo=tempo,
        time_signature=time_signature,
        total_measures=total_measures,
        chords=chords_data
    )


def extract_chords_from_track(track, ticks_per_beat: int, beats_per_measure: int) -> List[ChordData]:
    """Extract chord data from a MIDI track."""
    
    chords = []
    active_notes = []
    current_time = 0
    last_chord_time = 0
    chord_threshold = ticks_per_beat / 8  # Minimum time to consider as a chord
    
    for msg in track:
        current_time += msg.time
        
        if msg.type == 'note_on' and msg.velocity > 0:
            # If we have active notes and enough time has passed, save the chord
            if active_notes and (current_time - last_chord_time) > chord_threshold:
                if len(active_notes) >= 2:  # At least 2 notes for a chord
                    root, chord_type = identify_chord(active_notes[:])
                    if root:
                        # Calculate measure and beat
                        beats_elapsed = current_time / ticks_per_beat
                        measure_number = int(beats_elapsed / beats_per_measure) + 1
                        beat_position = (beats_elapsed % beats_per_measure) + 1
                        
                        chords.append(ChordData(
                            measure_number=measure_number,
                            beat_position=round(beat_position, 2),
                            chord_symbol=f"{root}{chord_type}",
                            midi_notes=active_notes[:]
                        ))
                
                active_notes = []
                last_chord_time = current_time
            
            active_notes.append(msg.note)
        
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active_notes:
                active_notes.remove(msg.note)
    
    # Don't forget the last chord
    if active_notes and len(active_notes) >= 2:
        root, chord_type = identify_chord(active_notes)
        if root:
            beats_elapsed = current_time / ticks_per_beat
            measure_number = int(beats_elapsed / beats_per_measure) + 1
            beat_position = (beats_elapsed % beats_per_measure) + 1
            
            chords.append(ChordData(
                measure_number=measure_number,
                beat_position=round(beat_position, 2),
                chord_symbol=f"{root}{chord_type}",
                midi_notes=active_notes
            ))
    
    return chords
