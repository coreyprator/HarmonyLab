# midi_diagnostic.py
# Run this to see EXACTLY what the parser is reading from the MIDI file
# Usage: python midi_diagnostic.py path/to/file.mid

import sys
from mido import MidiFile

def midi_note_to_name(note_num):
    """Convert MIDI note number to note name."""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (note_num // 12) - 1
    note = notes[note_num % 12]
    return f"{note}{octave}"

def diagnose_midi(filepath):
    """Dump everything mido sees in the MIDI file."""
    
    print("=" * 70)
    print(f"MIDI DIAGNOSTIC: {filepath}")
    print("=" * 70)
    
    try:
        mid = MidiFile(filepath)
    except Exception as e:
        print(f"ERROR: Could not open file: {e}")
        return
    
    # Header info
    print(f"\n[HEADER]")
    print(f"  File type: {mid.type}")
    print(f"  Ticks per beat: {mid.ticks_per_beat}")
    print(f"  Number of tracks: {len(mid.tracks)}")
    
    # Calculate measure length (assuming 4/4 until we find time signature)
    ticks_per_measure = mid.ticks_per_beat * 4  # Default 4/4
    tempo_bpm = 120  # Default
    
    print(f"\n[TRACKS OVERVIEW]")
    for i, track in enumerate(mid.tracks):
        note_count = sum(1 for msg in track if msg.type == 'note_on' and msg.velocity > 0)
        print(f"  Track {i}: '{track.name or '(unnamed)'}' - {note_count} note-on events")
    
    # Detailed track analysis
    for track_idx, track in enumerate(mid.tracks):
        print(f"\n{'=' * 70}")
        print(f"[TRACK {track_idx}] {track.name or '(unnamed)'}")
        print("=" * 70)
        
        abs_time = 0
        active_notes = {}  # note_num -> start_time
        note_events = []
        
        for msg in track:
            abs_time += msg.time
            
            # Meta events
            if msg.type == 'set_tempo':
                tempo_bpm = 60_000_000 / msg.tempo
                print(f"  [META] Tick {abs_time}: Tempo = {tempo_bpm:.1f} BPM")
            
            elif msg.type == 'time_signature':
                ticks_per_measure = mid.ticks_per_beat * msg.numerator * (4 / msg.denominator)
                print(f"  [META] Tick {abs_time}: Time Signature = {msg.numerator}/{msg.denominator}")
                print(f"         -> Ticks per measure = {ticks_per_measure}")
            
            elif msg.type == 'key_signature':
                print(f"  [META] Tick {abs_time}: Key Signature = {msg.key}")
            
            # Note events
            elif msg.type == 'note_on' and msg.velocity > 0:
                active_notes[msg.note] = abs_time
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in active_notes:
                    start = active_notes.pop(msg.note)
                    duration = abs_time - start
                    note_events.append({
                        'start': start,
                        'end': abs_time,
                        'note': msg.note,
                        'name': midi_note_to_name(msg.note),
                        'duration': duration,
                        'channel': msg.channel
                    })
        
        if not note_events:
            print("  (No note events in this track)")
            continue
        
        # Sort by start time
        note_events.sort(key=lambda x: x['start'])
        
        # Group notes by measure
        print(f"\n  [NOTES BY MEASURE] (ticks_per_measure = {ticks_per_measure})")
        print(f"  {'Measure':<8} {'Beat':<6} {'Tick':<8} {'Note':<6} {'MIDI#':<6} {'Duration':<10} {'Channel'}")
        print(f"  {'-'*8} {'-'*6} {'-'*8} {'-'*6} {'-'*6} {'-'*10} {'-'*7}")
        
        current_measure = -1
        measure_notes = []
        
        for event in note_events[:100]:  # First 100 notes
            measure = int(event['start'] // ticks_per_measure) + 1
            beat_in_measure = (event['start'] % ticks_per_measure) / mid.ticks_per_beat + 1
            
            if measure != current_measure:
                # Print simultaneous notes summary for previous measure
                if measure_notes:
                    print(f"  >> Measure {current_measure} had {len(measure_notes)} note events")
                current_measure = measure
                measure_notes = []
            
            measure_notes.append(event)
            
            print(f"  {measure:<8} {beat_in_measure:<6.2f} {event['start']:<8} {event['name']:<6} {event['note']:<6} {event['duration']:<10} {event['channel']}")
        
        # Find simultaneous notes (potential chords)
        print(f"\n  [CHORD DETECTION ANALYSIS]")
        print(f"  Looking for notes starting within 10 ticks of each other...")
        
        chord_window = 10  # ticks
        i = 0
        chord_count = 0
        
        while i < len(note_events):
            # Collect all notes within window
            chord_notes = [note_events[i]]
            j = i + 1
            while j < len(note_events) and note_events[j]['start'] - note_events[i]['start'] <= chord_window:
                chord_notes.append(note_events[j])
                j += 1
            
            if len(chord_notes) >= 3:  # At least 3 notes = potential chord
                chord_count += 1
                if chord_count <= 20:  # Show first 20 potential chords
                    measure = int(chord_notes[0]['start'] // ticks_per_measure) + 1
                    beat = (chord_notes[0]['start'] % ticks_per_measure) / mid.ticks_per_beat + 1
                    note_names = [n['name'] for n in chord_notes]
                    note_nums = [n['note'] for n in chord_notes]
                    
                    # Try to identify chord
                    root = min(note_nums)
                    intervals = sorted(set((n - root) % 12 for n in note_nums))
                    
                    print(f"  Measure {measure}, Beat {beat:.2f}: {note_names}")
                    print(f"    MIDI notes: {note_nums}")
                    print(f"    Intervals from bass: {intervals}")
                    print()
            
            i = j if j > i else i + 1
        
        print(f"  Total potential chords (3+ simultaneous notes): {chord_count}")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python midi_diagnostic.py <path_to_midi_file>")
        print("Example: python midi_diagnostic.py data/blue_bossa.mid")
        sys.exit(1)
    
    diagnose_midi(sys.argv[1])
