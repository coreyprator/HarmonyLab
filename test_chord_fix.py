"""Quick test of the chord identification fix for BWV 846."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import mido
from app.services.midi_parser import identify_chord, parse_midi_file

# ── Unit-test identify_chord directly ──
print("=== identify_chord unit tests ===")
tests = [
    # (midi_notes, expected_root, expected_type, label)
    ([48, 52, 55, 60, 64], "C", "Maj", "C major (root pos)"),
    ([52, 55, 60, 64],     "C", "Maj", "C major (1st inv, no bass)"),
    ([55, 60, 64],          "C", "Maj", "C major (2nd inv triad)"),
    ([48, 50, 57, 62, 65], "D", "m7",  "Dm7 (C bass)"),
    ([50, 53, 57, 60],     "D", "m7",  "Dm7 (root pos)"),
    ([47, 53, 55, 62],     "G", "7",   "G7 (B bass 3rd inv, B F G D)"),
    ([43, 47, 50, 53],     "G", "7",   "G7 (root pos, G B D F)"),
    ([48, 52, 57, 60, 64], "A", "m",   "Am (C bass 1st inv)"),
    ([57, 60, 64],          "A", "m",   "Am (root pos triad)"),
    ([50, 54, 57, 60],     "D", "7",   "D7 (root pos, D Gb A C)"),
    ([55, 60],              "C", "",   "Dyad C-G (P5)"),
    ([55, 64],              "E", "m",  "Dyad G-E (m6 = inv m3)"),
]
all_pass = True
for notes, exp_root, exp_type, label in tests:
    root, ctype = identify_chord(notes)
    status = "PASS" if root == exp_root and ctype == exp_type else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {status}: {label:30s}  got {root}{ctype:6s}  expected {exp_root}{exp_type}")

# ── Synthetic BWV 846 MIDI ──
print("\n=== Synthetic BWV 846 parse test ===")
mid = mido.MidiFile(ticks_per_beat=480)
track = mido.MidiTrack()
mid.tracks.append(track)
track.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(72)))

sixteenth = 480 // 4  # 120 ticks

# BWV 846 chord voicings: (bass, mid1, mid2, top1, top2)
chord_data = [
    (48, 52, 55, 60, 64),   # M1: C major
    (48, 50, 57, 62, 65),   # M2: Dm7
    (47, 53, 55, 59, 62),   # M3: G7/B (B F G B D)
    (48, 52, 57, 60, 64),   # M4: Am/C
    (50, 54, 57, 60, 66),   # M5: D7 (D Gb A C Gb)
]
expected = ["CMaj", "Dm7", "G7", "Am", "D7"]

time_delta = 0
for bass, m1, m2, t1, t2 in chord_data:
    for half in range(2):
        top = t1 if half == 0 else t2
        pattern = [bass, m1, m2, top, m2, top, m2, top]
        for note in pattern:
            track.append(mido.Message('note_on', note=note, velocity=64, time=time_delta))
            time_delta = 0
            track.append(mido.Message('note_off', note=note, velocity=0, time=sixteenth))

mid.save('test_bwv846_v2.mid')
result = parse_midi_file('test_bwv846_v2.mid')

print(f"Time sig: {result.time_signature}")
print(f"Total chords: {len(result.chords)}")
for c in result.chords:
    print(f"  M{c.measure_number} B{c.beat_position}: {c.chord_symbol}")

# Check first chord of each measure
measure_chords = {}
for c in result.chords:
    m = c.measure_number
    if m not in measure_chords:
        measure_chords[m] = c.chord_symbol

print("\nMeasure-level summary:")
for m in sorted(measure_chords):
    exp = expected[m-1] if m <= len(expected) else "?"
    status = "PASS" if measure_chords[m] == exp else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {status}: M{m} = {measure_chords[m]:6s} (expected {exp})")

if all_pass:
    print("\n*** ALL TESTS PASSED ***")
else:
    print("\n*** SOME TESTS FAILED ***")

# Clean up
os.remove('test_bwv846_v2.mid')
