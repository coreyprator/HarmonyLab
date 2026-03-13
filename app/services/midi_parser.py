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
from typing import Any, List, Optional, Tuple, Dict
from pydantic import BaseModel
from collections import defaultdict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable defaults (all in fractions of a beat)
# ---------------------------------------------------------------------------
# Notes whose onsets fall within this many beats of each other are grouped
# into a single chord.  2.0 = half a measure in 4/4; captures full chord
# voicings for both arpeggiated passages (Bach BWV 846) and block chords.
DEFAULT_CHORD_WINDOW_BEATS: float = 2.0
# Minimum number of distinct pitch-classes required to call a group a "chord".
MIN_NOTES_FOR_CHORD: int = 2


class NoteData(BaseModel):
    """Individual note data from MIDI."""
    measure_number: int
    beat_position: float
    midi_pitch: int
    duration_beats: float
    velocity: int


class ChordData(BaseModel):
    """Parsed chord data from MIDI."""
    measure_number: int
    beat_position: float
    chord_symbol: str
    midi_notes: List[int]  # Original notes for verification
    is_rootless: bool = False  # HL-006A: rootless voicing detected
    chord_source: str = "algorithm"  # HL-006B: provenance tracking


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
    notes: List[NoteData] = []


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
    
    # Altered dominant chords
    '7b9': [0, 4, 7, 10, 13],       # dom7 + flat 9
    '7#9': [0, 4, 7, 10, 15],       # dom7 + sharp 9 (Hendrix chord)
    '7b13': [0, 4, 7, 10, 20],      # dom7 + flat 13
    '7#11': [0, 4, 7, 10, 18],      # dom7 + sharp 11 (lydian dominant)
    '7alt': [0, 4, 10, 13, 15, 20], # dom7 + b9 + #9 + b13 (no 5th)

    # Additional extended chords
    '6/9': [0, 4, 7, 9, 14],        # major 6 + 9
    'm6/9': [0, 3, 7, 9, 14],       # minor 6 + 9

    # Suspended chords
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    '7sus4': [0, 5, 7, 10],
    '9sus4': [0, 5, 7, 10, 14],
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


# Pre-compute mod-12 normalized templates for rotation-based matching.
# Extended chord intervals (e.g. 14 = 9th) are reduced to mod 12.
_TEMPLATES_MOD12: Dict[str, List[int]] = {}
for _ct, _tmpl in CHORD_TEMPLATES.items():
    _mod = sorted(set(i % 12 for i in _tmpl))
    _TEMPLATES_MOD12[_ct] = _mod


# HL-006A: Chord types that are 7th chords or extensions (for jazz bias)
_7TH_OR_EXTENSION = {
    'Maj7', 'm7', '7', 'ø7', 'dim7', 'mMaj7',
    '9', 'Maj9', 'm9', '11', 'm11', '13', 'Maj13',
    '7b9', '7#9', '7b13', '7#11', '7alt',
    '6/9', 'm6/9', '7sus4', '9sus4',
}


def _beat_weight(beat_position: float) -> float:
    """HL-006A Change 4: Beat position weighting multiplier."""
    beat = round(beat_position, 2)
    if abs(beat - 1.0) < 0.1:
        return 2.0
    elif abs(beat - 3.0) < 0.1:
        return 1.5
    elif abs(beat - 2.0) < 0.1 or abs(beat - 4.0) < 0.1:
        return 1.0
    else:
        return 0.75  # off-beats


def _duration_weight(duration_beats: float) -> float:
    """HL-006A Change 3: Duration weighting."""
    if duration_beats < 0.25:
        return 0.1  # ornaments, grace notes
    return max(duration_beats, 0.1)


def identify_chord(
    notes: List[int],
    note_details: Optional[List[Dict]] = None,
) -> Tuple[str, str, bool]:
    """Identify a chord from MIDI notes using rotation-based root detection.

    HL-006A v1.1 algorithm:
    - Jazz 7th bias: prefer 7th chord over triad when both match equally
    - Rootless voicing tolerance: allow root-absent matching for 7th chords
    - Duration weighting: weight pitch classes by note duration
    - Beat position weighting: weight by beat position

    Args:
        notes: List of MIDI note numbers.
        note_details: Optional list of dicts with 'midi_pitch', 'duration_beats',
                      'beat_position' for weighted analysis.

    Returns ``(root_name, chord_type, is_rootless)``.
    """
    if not notes:
        return ("", "", False)

    # Build weighted pitch class profile (Changes 3 & 4)
    pc_weights: Dict[int, float] = defaultdict(float)
    if note_details:
        for nd in note_details:
            pc = nd['midi_pitch'] % 12
            dur_w = _duration_weight(nd.get('duration_beats', 1.0))
            beat_w = _beat_weight(nd.get('beat_position', 1.0))
            pc_weights[pc] += dur_w * beat_w
    else:
        for n in notes:
            pc_weights[n % 12] += 1.0

    pitch_classes = sorted(pc_weights.keys())
    num_pcs = len(pitch_classes)
    bass_pc = min(notes) % 12

    if num_pcs < 2:
        return (NOTE_NAMES[pitch_classes[0]], "", False)

    # Find the dominant pitch class by weight (candidate for root)
    weighted_root_pc = max(pc_weights, key=pc_weights.get)

    # ----- Try every pitch class as a candidate root -----
    best_root: Optional[str] = None
    best_type = ""
    best_score = -1.0
    best_rootless = False

    for root_pc in pitch_classes:
        intervals = sorted(set((pc - root_pc) % 12 for pc in pitch_classes))

        # --- Exact template match ---
        for chord_type, template in _TEMPLATES_MOD12.items():
            if intervals == template:
                root_pos_bonus = 50 if root_pc == bass_pc else 0
                weight_bonus = 20 if root_pc == weighted_root_pc else 0
                # Change 1: Jazz 7th bias — 7th chords and extensions get +100
                jazz_bonus = 100 if chord_type in _7TH_OR_EXTENSION else 0
                score = 1000 + len(template) * 10 + root_pos_bonus + weight_bonus + jazz_bonus
                if score > best_score:
                    best_score = score
                    best_root = NOTE_NAMES[root_pc]
                    best_type = chord_type
                    best_rootless = False

        # --- Subset match — only when ≥ 3 pitch classes ---
        if num_pcs >= 3 and best_score < 1000:
            for chord_type, template in _TEMPLATES_MOD12.items():
                if set(intervals).issubset(set(template)) and len(intervals) > 1:
                    coverage = len(intervals) / len(template)
                    root_pos_bonus = 10 if root_pc == bass_pc else 0
                    jazz_bonus = 50 if chord_type in _7TH_OR_EXTENSION else 0
                    score = int(coverage * 100) + len(template) + root_pos_bonus + jazz_bonus
                    if score > best_score:
                        best_score = score
                        best_root = NOTE_NAMES[root_pc]
                        best_type = chord_type
                        best_rootless = False

    # --- Change 2: Rootless voicing tolerance ---
    # Try rootless when no exact match found, OR when the best match is a
    # dim/aug triad (these are almost always part of a larger chord in jazz).
    _triad_only = best_type in ('dim', 'aug', 'sus2', 'sus4') and best_score < 1130
    if num_pcs >= 3 and (best_score < 1000 or _triad_only):
        for absent_root_pc in range(12):
            if absent_root_pc in pitch_classes:
                continue  # root is present, skip
            # What intervals would we have if absent_root_pc were the root?
            intervals_with_root = sorted(set(
                [(pc - absent_root_pc) % 12 for pc in pitch_classes] + [0]
            ))
            for chord_type, template in _TEMPLATES_MOD12.items():
                if chord_type not in _7TH_OR_EXTENSION:
                    continue  # rootless only for 7th+ chords
                if len(template) < 4:
                    continue  # need at least 4-note template
                if intervals_with_root == template:
                    # Check: at least 3 chord tones present (excluding root)
                    present_tones = set((pc - absent_root_pc) % 12 for pc in pitch_classes)
                    template_tones = set(template) - {0}
                    if len(present_tones & template_tones) >= 3:
                        # Score above triads (1030) but below full 7th matches (1140)
                        rootless_score = 1100 + len(template) * 10
                        if rootless_score > best_score:
                            best_score = rootless_score
                            best_root = NOTE_NAMES[absent_root_pc]
                            best_type = chord_type
                            best_rootless = True

    if best_root:
        return (best_root, best_type, best_rootless)

    # ----- Fallback for 2-note dyads -----
    if num_pcs == 2:
        interval = (pitch_classes[1] - pitch_classes[0]) % 12
        if interval == 7:
            return (NOTE_NAMES[pitch_classes[0]], "", False)
        elif interval == 5:
            return (NOTE_NAMES[pitch_classes[1]], "", False)
        elif interval == 4:
            return (NOTE_NAMES[pitch_classes[0]], "", False)
        elif interval == 3:
            return (NOTE_NAMES[pitch_classes[0]], "m", False)
        elif interval == 8:
            return (NOTE_NAMES[pitch_classes[1]], "", False)
        elif interval == 9:
            return (NOTE_NAMES[pitch_classes[1]], "m", False)

    # ----- Last resort: bass note as root -----
    root_name = NOTE_NAMES[bass_pc]
    intervals_from_bass = sorted(set((pc - bass_pc) % 12 for pc in pitch_classes))
    if 3 in intervals_from_bass:
        return (root_name, "m", False)
    elif 4 in intervals_from_bass:
        return (root_name, "", False)
    return (root_name, "", False)


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

    # ------------------------------------------------------------------
    # Extract individual notes (HL-006E: needed for note count badges)
    # ------------------------------------------------------------------
    notes_data = extract_notes_from_track(
        best_track,
        midi.ticks_per_beat,
        time_sig_num,
    )

    total_measures = max(
        max((c.measure_number for c in chords_data), default=0),
        max((n.measure_number for n in notes_data), default=0),
    )

    return ParsedSong(
        title=None,  # MIDI files rarely carry a title meta-event
        tempo=tempo,
        time_signature=time_signature,
        total_measures=total_measures,
        chords=chords_data,
        notes=notes_data,
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

    # Collect all events with absolute times for duration computation
    all_events: List[Tuple[int, Any]] = []
    current_time = 0
    for msg in track:
        current_time += msg.time
        all_events.append((current_time, msg))

    # Build note-on events and a duration map
    note_events: List[Tuple[int, int, int]] = []  # (onset_tick, midi_note, velocity)
    # Track note-off times for duration computation
    note_on_times: Dict[int, int] = {}  # pitch → onset_tick
    note_durations: Dict[Tuple[int, int], float] = {}  # (onset_tick, pitch) → duration_beats

    for tick, msg in all_events:
        if msg.type == 'note_on' and msg.velocity > 0:
            note_events.append((tick, msg.note, msg.velocity))
            note_on_times[msg.note] = tick
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in note_on_times:
                onset = note_on_times.pop(msg.note)
                dur_ticks = max(tick - onset, 1)
                note_durations[(onset, msg.note)] = dur_ticks / ticks_per_beat

    if not note_events:
        return []

    # ------------------------------------------------------------------
    # Group notes whose onsets fall within the same window
    # ------------------------------------------------------------------
    chords: List[ChordData] = []
    window_start = note_events[0][0]
    window_notes: List[int] = []
    window_details: List[Dict] = []  # HL-006A: note details for weighted analysis

    def _flush_window(window_start_tick: int) -> None:
        """Emit a chord from the current window if enough notes exist."""
        if len(window_notes) < MIN_NOTES_FOR_CHORD:
            return
        root, chord_type, is_rootless = identify_chord(window_notes[:], window_details[:])
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
            is_rootless=is_rootless,
        ))

    for onset, note, velocity in note_events:
        if onset - window_start >= window_ticks and window_notes:
            # Current note is outside the window — flush accumulated notes
            _flush_window(window_start)
            window_notes = []
            window_details = []
            window_start = onset
        elif not window_notes:
            window_start = onset

        window_notes.append(note)
        # HL-006A: Compute beat position and duration for weighting
        beats_elapsed = onset / ticks_per_beat
        beat_pos = (beats_elapsed % beats_per_measure) + 1
        dur = note_durations.get((onset, note), 1.0)
        window_details.append({
            'midi_pitch': note,
            'duration_beats': dur,
            'beat_position': beat_pos,
        })

    # Flush the final window
    _flush_window(window_start)

    return chords


# -----------------------------------------------------------------------
# Individual note extraction (HL-006E)
# -----------------------------------------------------------------------
def extract_notes_from_track(
    track,
    ticks_per_beat: int,
    beats_per_measure: int,
) -> List[NoteData]:
    """Extract individual notes with onset, duration, and velocity from a MIDI track.

    Pairs note_on/note_off events to compute durations. Returns one NoteData
    per sounding note (velocity > 0).
    """
    # Build (absolute_tick, msg) list
    events: List[Tuple[int, Any]] = []
    current_time = 0
    for msg in track:
        current_time += msg.time
        events.append((current_time, msg))

    # Pair note-on → note-off for duration
    active: Dict[int, Tuple[int, int]] = {}  # pitch → (onset_tick, velocity)
    notes: List[NoteData] = []

    for tick, msg in events:
        if msg.type == 'note_on' and msg.velocity > 0:
            active[msg.note] = (tick, msg.velocity)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active:
                onset_tick, velocity = active.pop(msg.note)
                duration_ticks = max(tick - onset_tick, 1)
                beats_elapsed = onset_tick / ticks_per_beat
                measure_number = int(beats_elapsed / beats_per_measure) + 1
                beat_position = (beats_elapsed % beats_per_measure) + 1
                duration_beats = duration_ticks / ticks_per_beat
                notes.append(NoteData(
                    measure_number=measure_number,
                    beat_position=round(beat_position, 4),
                    midi_pitch=msg.note,
                    duration_beats=round(duration_beats, 4),
                    velocity=velocity,
                ))

    # Flush notes still active at end of track (assume duration = 1 beat)
    for pitch, (onset_tick, velocity) in active.items():
        beats_elapsed = onset_tick / ticks_per_beat
        measure_number = int(beats_elapsed / beats_per_measure) + 1
        beat_position = (beats_elapsed % beats_per_measure) + 1
        notes.append(NoteData(
            measure_number=measure_number,
            beat_position=round(beat_position, 4),
            midi_pitch=pitch,
            duration_beats=1.0,
            velocity=velocity,
        ))

    notes.sort(key=lambda n: (n.measure_number, n.beat_position, n.midi_pitch))
    return notes
