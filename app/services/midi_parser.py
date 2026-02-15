"""
MIDI Parser Service

Uses the `mido` library to:
1. Parse MIDI files
2. Extract chord data from chord tracks
3. Detect time signature and tempo
4. Map MIDI notes to chord symbols

Supports both block-chord and arpeggiated MIDI styles via a configurable
time-window chord grouping algorithm.
"""
import logging
from mido import MidiFile, tempo2bpm
from typing import List, Optional, Tuple, Dict
from pydantic import BaseModel
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable defaults (all in fractions of a beat)
# ---------------------------------------------------------------------------
# Notes whose onsets fall within this many beats of each other are grouped
# into a single chord.  1.0 = one full beat; works well for arpeggiated
# passages like Bach's Prelude in C (BWV 846).
DEFAULT_CHORD_WINDOW_BEATS: float = 1.0
# Minimum number of distinct pitch-classes required to call a group a "chord".
MIN_NOTES_FOR_CHORD: int = 2


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


def parse_midi_file(
    file_path: str,
    chord_window_beats: float = DEFAULT_CHORD_WINDOW_BEATS,
) -> ParsedSong:
    """
    Parse a MIDI file and extract chord progressions.

    Args:
        file_path: Path to MIDI file.
        chord_window_beats: Size of the grouping window in beats.
            Notes whose onsets fall within this window are treated as
            belonging to the same chord.  Larger values help arpeggiated
            music (e.g. Bach BWV 846); smaller values preserve detail in
            block-chord arrangements.

    Returns:
        ParsedSong with all extracted data.
    """
    midi = MidiFile(file_path)

    # ------------------------------------------------------------------
    # Extract tempo and time-signature from the first track that has them
    # ------------------------------------------------------------------
    tempo = 120  # Default BPM
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

    # ------------------------------------------------------------------
    # Choose the best track for chord extraction
    # ------------------------------------------------------------------
    # Primary strategy: track with the most total note-on events (works
    # for both block-chord AND arpeggiated files).
    # Fallback: first track that contains any notes.
    # ------------------------------------------------------------------
    best_track = None
    best_note_count = 0

    for track in midi.tracks:
        note_count = sum(
            1 for msg in track
            if msg.type == 'note_on' and msg.velocity > 0
        )
        if note_count > best_note_count:
            best_note_count = note_count
            best_track = track

    if best_track is None:
        for track in midi.tracks:
            if any(msg.type in ('note_on', 'note_off') for msg in track):
                best_track = track
                break

    if best_track is None:
        logger.warning("MIDI file contains no note events — returning empty song")
        return ParsedSong(
            title=None,
            tempo=tempo,
            time_signature=time_signature,
            total_measures=0,
            chords=[],
        )

    # ------------------------------------------------------------------
    # Extract chords using the windowed algorithm
    # ------------------------------------------------------------------
    chords_data = extract_chords_from_track(
        best_track,
        midi.ticks_per_beat,
        time_sig_num,
        chord_window_beats=chord_window_beats,
    )

    if not chords_data:
        logger.warning(
            "MIDI chord extraction produced 0 chords. "
            "Track had %d note-on events. "
            "Consider adjusting chord_window_beats (current: %.2f).",
            best_note_count,
            chord_window_beats,
        )

    total_measures = max((c.measure_number for c in chords_data), default=0)

    return ParsedSong(
        title=None,  # MIDI files rarely carry a title meta-event
        tempo=tempo,
        time_signature=time_signature,
        total_measures=total_measures,
        chords=chords_data,
    )


# -----------------------------------------------------------------------
# Core chord-extraction algorithm (time-window grouping)
# -----------------------------------------------------------------------
def extract_chords_from_track(
    track,
    ticks_per_beat: int,
    beats_per_measure: int,
    *,
    chord_window_beats: float = DEFAULT_CHORD_WINDOW_BEATS,
) -> List[ChordData]:
    """Extract chord data from a MIDI track using time-window grouping.

    Instead of requiring notes to arrive at the *exact* same tick, this
    algorithm collects every ``note_on`` whose onset falls within a
    sliding window of ``chord_window_beats`` beats.  When the window
    closes (i.e. a new note arrives *outside* the current window), the
    accumulated notes are identified as a chord and emitted.

    This handles both block-chord voicings (Corcovado-style) and
    arpeggiated passages (Bach BWV 846-style).
    """
    window_ticks = int(ticks_per_beat * chord_window_beats)

    # Collect every (onset_tick, midi_note) pair first so we can reason
    # about timing cleanly.
    note_events: List[Tuple[int, int]] = []
    current_time = 0
    for msg in track:
        current_time += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            note_events.append((current_time, msg.note))

    if not note_events:
        return []

    # ------------------------------------------------------------------
    # Group notes whose onsets fall within the same window
    # ------------------------------------------------------------------
    chords: List[ChordData] = []
    window_start = note_events[0][0]
    window_notes: List[int] = []

    def _flush_window(window_start_tick: int) -> None:
        """Emit a chord from the current window if enough notes exist."""
        if len(window_notes) < MIN_NOTES_FOR_CHORD:
            return
        root, chord_type = identify_chord(window_notes[:])
        if not root:
            return
        beats_elapsed = window_start_tick / ticks_per_beat
        measure_number = int(beats_elapsed / beats_per_measure) + 1
        beat_position = (beats_elapsed % beats_per_measure) + 1
        chords.append(ChordData(
            measure_number=measure_number,
            beat_position=round(beat_position, 2),
            chord_symbol=f"{root}{chord_type}",
            midi_notes=window_notes[:],
        ))

    for onset, note in note_events:
        if onset - window_start >= window_ticks and window_notes:
            # Current note is outside the window — flush accumulated notes
            _flush_window(window_start)
            window_notes = []
            window_start = onset
        elif not window_notes:
            window_start = onset

        window_notes.append(note)

    # Flush the final window
    _flush_window(window_start)

    return chords
