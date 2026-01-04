"""
MIDI Parser Audit Service

Provides detailed debugging information about MIDI file parsing.
Shows ALL MIDI events, measure calculations, and chord detection decisions.
"""
from mido import MidiFile, tempo2bpm
from typing import List, Dict, Any
from pydantic import BaseModel
from collections import defaultdict


NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


class MidiEvent(BaseModel):
    """Individual MIDI event."""
    time_ticks: int
    time_beats: float
    measure: int
    beat_in_measure: float
    event_type: str  # note_on, note_off, etc.
    note: int = None
    note_name: str = None
    velocity: int = None


class MeasureAudit(BaseModel):
    """Audit data for a single measure."""
    measure_number: int
    start_beat: float
    end_beat: float
    all_notes_played: List[str]  # All notes that sounded during measure
    simultaneous_note_groups: List[Dict[str, Any]]  # Groups of notes sounding together
    detected_chords: List[Dict[str, Any]]  # What chords the parser identified
    events: List[MidiEvent]  # All MIDI events in this measure


class ParseAudit(BaseModel):
    """Complete audit report of MIDI parsing."""
    filename: str
    tempo: int
    time_signature: str
    ticks_per_beat: int
    total_ticks: int
    total_beats: float
    total_measures: int
    tracks_analyzed: List[Dict[str, Any]]
    measures: List[MeasureAudit]
    parser_issues: List[str]


def midi_note_to_name(midi_note: int) -> str:
    """Convert MIDI note number to name (e.g., 60 -> C4)."""
    octave = (midi_note // 12) - 1
    note_name = NOTE_NAMES[midi_note % 12]
    return f"{note_name}{octave}"


def audit_midi_file(file_path: str) -> ParseAudit:
    """
    Perform detailed audit of MIDI file parsing.
    Returns comprehensive report of what the parser sees.
    """
    midi = MidiFile(file_path)
    issues = []
    
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
    ticks_per_beat = midi.ticks_per_beat
    
    # Analyze all tracks
    tracks_info = []
    for idx, track in enumerate(midi.tracks):
        track_info = {
            "track_number": idx,
            "track_name": track.name if hasattr(track, 'name') else f"Track {idx}",
            "total_events": len(track),
            "note_events": sum(1 for msg in track if msg.type in ['note_on', 'note_off']),
            "polyphony": 0
        }
        
        # Calculate max polyphony
        active_notes = []
        max_active = 0
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                active_notes.append(msg.note)
                max_active = max(max_active, len(active_notes))
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active_notes:
                    active_notes.remove(msg.note)
        
        track_info["polyphony"] = max_active
        tracks_info.append(track_info)
    
    # Find track with most polyphony (chord track)
    chord_track = max(tracks_info, key=lambda t: t["polyphony"])
    track_idx = chord_track["track_number"]
    
    if chord_track["polyphony"] == 0:
        issues.append("No polyphonic track found - may not contain chords")
    
    # Parse all events from chord track
    track = midi.tracks[track_idx]
    all_events = []
    current_time = 0
    
    for msg in track:
        current_time += msg.time
        
        if msg.type in ['note_on', 'note_off']:
            beats_elapsed = current_time / ticks_per_beat
            measure_number = int(beats_elapsed / time_sig_num) + 1
            beat_in_measure = (beats_elapsed % time_sig_num) + 1
            
            event = MidiEvent(
                time_ticks=current_time,
                time_beats=beats_elapsed,
                measure=measure_number,
                beat_in_measure=round(beat_in_measure, 2),
                event_type=msg.type,
                note=msg.note,
                note_name=midi_note_to_name(msg.note),
                velocity=msg.velocity if hasattr(msg, 'velocity') else 0
            )
            all_events.append(event)
    
    # Calculate total measures
    total_beats = current_time / ticks_per_beat
    total_measures = int(total_beats / time_sig_num) + 1
    
    # Group events by measure
    measures_audit = []
    for measure_num in range(1, total_measures + 1):
        measure_events = [e for e in all_events if e.measure == measure_num]
        
        # Track notes active in this measure
        all_notes = set()
        active_notes = []
        note_groups = []
        
        for event in measure_events:
            if event.event_type == 'note_on' and event.velocity > 0:
                active_notes.append(event.note)
                all_notes.add(event.note_name)
                # Capture simultaneous notes
                if len(active_notes) > 1:
                    note_groups.append({
                        "beat": event.beat_in_measure,
                        "notes": [midi_note_to_name(n) for n in sorted(active_notes)],
                        "midi_notes": sorted(active_notes)
                    })
            elif event.event_type == 'note_off' or (event.event_type == 'note_on' and event.velocity == 0):
                if event.note in active_notes:
                    active_notes.remove(event.note)
        
        # What chords were detected? (We'll need to call the actual parser)
        # For now, just list the note groups
        detected_chords = []
        
        measure_audit = MeasureAudit(
            measure_number=measure_num,
            start_beat=(measure_num - 1) * time_sig_num,
            end_beat=measure_num * time_sig_num,
            all_notes_played=sorted(list(all_notes)),
            simultaneous_note_groups=note_groups,
            detected_chords=detected_chords,
            events=measure_events
        )
        measures_audit.append(measure_audit)
    
    # Check for issues
    if len([m for m in measures_audit if len(m.all_notes_played) > 0]) < total_measures / 2:
        issues.append(f"Only {len([m for m in measures_audit if len(m.all_notes_played) > 0])} measures have notes out of {total_measures} total")
    
    return ParseAudit(
        filename=file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1],
        tempo=tempo,
        time_signature=time_signature,
        ticks_per_beat=ticks_per_beat,
        total_ticks=current_time,
        total_beats=total_beats,
        total_measures=total_measures,
        tracks_analyzed=tracks_info,
        measures=measures_audit,
        parser_issues=issues
    )
