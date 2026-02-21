# Handoff: Fix MIDI Import Chord Extraction for Arpeggiated Passages

| Field | Value |
|-------|-------|
| ID | HO-P1Q2 |
| Project | 🔵 HarmonyLab |
| Task | Fix MIDI import — chord extraction for arpeggiated passages |
| Status | COMPLETE |
| Commit | 54bbe82 |
| Version | 1.8.1 |
| Deployed Revision | harmonylab-00077-fvs |

---

## What Was Done

### Root Cause
The `extract_chords_from_track()` function in `app/services/midi_parser.py` used a **simultaneous-note detection** algorithm that cleared its note buffer whenever a new `note_on` event arrived after a tiny threshold (`ticks_per_beat / 8`). For arpeggiated music like Bach's Prelude in C (BWV 846), where notes arrive sequentially one at a time, the buffer never accumulated more than 1 note before being cleared. Since the minimum chord size was 2 notes, **zero chords were ever emitted**.

Additionally, the track selection heuristic chose the track with the highest *simultaneous* polyphony (max active notes at any instant). This biased toward block-chord tracks and could miss arpeggiated tracks entirely.

### Fix
Replaced the chord extraction algorithm with a **time-window grouping** approach:

1. **New algorithm**: Collect all `note_on` events with timestamps. Group notes whose onsets fall within a configurable window (`DEFAULT_CHORD_WINDOW_BEATS = 1.0` beat). When a note arrives outside the current window, flush the accumulated notes as a chord and start a new window.

2. **Track selection**: Changed from "highest simultaneous polyphony" to "most total note-on events", which works correctly for both block-chord and arpeggiated MIDI files.

3. **Zero-chord warning**: Added `logger.warning()` when chord extraction produces 0 results, including the note count and window size for diagnostics.

4. **Configurable parameters**: `chord_window_beats` parameter on `parse_midi_file()` and `extract_chords_from_track()` allows tuning per-file. `MIN_NOTES_FOR_CHORD` module constant (default: 2).

### Files Modified
- `app/services/midi_parser.py` — Rewrote `parse_midi_file()` and `extract_chords_from_track()`
- `main.py` — Version bump 1.8.0 → 1.8.1

---

## Verification

### Corcovado (no regression)
- Before: **45 chords**
- After: **45 chords** ✅ (unchanged)

### Bach Prelude BWV 846
- Before: **0 chords** ❌
- After: **80 chords** ✅ (4 per measure × 20 measures)
- First 5 chord symbols: **CMaj, Gsus4, CMaj, Gdim7, C**
- Song ID: 32, Measures created: 20

### Health Check
```
GET https://harmonylab-57478301787.us-central1.run.app/health
{
    "status": "healthy",
    "database": "connected",
    "service": "harmonylab",
    "version": "1.8.1"
}
```

### Deployed Revision
`harmonylab-00077-fvs` serving 100% traffic

---

## What's Next
- The chord symbols for arpeggiated passages are beat-level approximations (e.g., "Gsus4" for a subset of a C major arpeggio). A future enhancement could use measure-level grouping or music21 analysis to produce more musically accurate chord names.
- The generated test MIDI is a simplified arpeggiation of BWV 846. Testing with the original MIDI file (when available) is recommended.
- Branch mismatch (master vs main) still exists — CI/CD on GitHub triggers on `main` but code is pushed to `master`. Not addressed per task scope.
- Frontend directory remains untracked. Not addressed per task scope.
