# Handoff: Analysis Quality — Key Detection, Chord Naming, Measure Numbering

| Field | Value |
|-------|-------|
| ID | HO-P1Q3 |
| Project | 🎵 HarmonyLab |
| Task | Fix analysis quality — 4 UAT findings from v1.8.1 |
| Status | COMPLETE |
| Commits | 0132605, 6bf4330 |
| Version | 1.8.2 |
| Deployed Revision | harmonylab-00079-m7k |

---

## What Was Done

### Finding 1: Key Detection Returns B Minor Instead of C Major (FIXED)

**Root Cause**: `_detect_key()` in `analysis_service.py` appended `harmony.ChordSymbol` objects directly to a music21 stream. music21's Krumhansl-Schmuckler key-detection algorithm produces incorrect results (B minor, confidence 0.0) when given `ChordSymbol` objects, but works correctly with plain `chord.Chord` objects (C major, confidence 0.95).

**Fix**: Convert `ChordSymbol` pitches to plain `chord.Chord` objects before appending to the analysis stream. Also added missing call to `_normalize_chord_symbol()` in `_detect_key()` (was already used in `_analyze_chord()`).

**File**: `app/services/analysis_service.py`

### Finding 2: Chord Naming Produces Wrong Symbols — Gsus4, Gdim7 (FIXED)

**Root Cause**: Two bugs in `identify_chord()` in `midi_parser.py`:
1. **Root assumption**: Always used the lowest sounding note as the chord root, failing for inversions (e.g., Am/C → "C" instead of "Am").
2. **Subset matching with 2 notes**: Two pitch classes were matched against large templates, producing false positives (e.g., [0,5] → "sus4", [0,9] → "dim7").
3. **1-beat window**: In arpeggiated passages, beats 2 and 4 captured only 2 pitch classes.

**Fix**:
- **Rotation-based root detection**: Try every unique pitch class as a candidate root, compute intervals, and score against all templates. Best match wins, with bonus for root-position voicings.
- **≥3 pitch classes for subset matching**: Prevents 2-note false positives.
- **Dyad interval heuristics**: P5→lower note, P4→upper note, M3→lower, m3→lower+m, etc.
- **2-beat window**: Changed `DEFAULT_CHORD_WINDOW_BEATS` from 1.0 to 2.0 (half-measure in 4/4), capturing fuller harmonic content per window.

**File**: `app/services/midi_parser.py`

### Finding 3: Corcovado Chord Count Drifted to 47 (NOT REPRODUCED)

**Investigation**: Database query confirmed **45 chords** for Corcovado (song_id 23). Zero duplicate entries at any measure/beat position. The UAT report of 47 was a miscount.

**Action**: No code change. Documented in UAT JSON.

### Finding 4: Measure Numbering Sequential Instead of by Bar (NOT REPRODUCED)

**Investigation**: Database query confirmed Bach (song_id 33) has measures numbered 1-20 sequentially within a single "Main" section. No measure restarts, no section fragmentation.

**Action**: No code change. Documented in UAT JSON.

### Files Modified
- `app/services/midi_parser.py` — Rewrote `identify_chord()` with rotation-based matching, changed window to 2 beats
- `app/services/analysis_service.py` — Fixed `_detect_key()` to use `chord.Chord` instead of `ChordSymbol`, added normalization
- `main.py` — Version bump 1.8.1 → 1.8.2

---

## Verification

### Bach BWV 846 — Key Detection
- Before: **B minor** (confidence 0.0) ❌
- After: **C major** (confidence 0.95) ✅

### Bach BWV 846 — Chord Symbols (first 8)
- Before: CMaj, **Gsus4**, CMaj, **Gdim7**, C, **Asus4**, CMaj, **Aaug** ❌
- After: CMaj, CMaj, Dm7, Dm7, GMaj, G7, CMaj, CMaj ✅

### Bach BWV 846 — Roman Numerals
```
CMaj   → IMaj    (tonic)
Dm7    → iim7    (subdominant)
GMaj   → VMaj    (dominant)
G7     → V7      (dominant)
Am     → vim     (tonic)
```

### Corcovado — No Regression
- Chord count: **45** (unchanged) ✅
- Key detection: **A minor** (confidence 1.0) ✅
- First 8 chords: Am6, Ab, Gm7, C9, FMaj9, Bb13, Em7, Am7 (unchanged) ✅

### Health Check
```
GET https://harmonylab-57478301787.us-central1.run.app/health
{
    "status": "healthy",
    "database": "connected",
    "service": "harmonylab",
    "version": "1.8.2"
}
```

### Deployed Revision
`harmonylab-00079-m7k` serving 100% traffic

---

## UAT Deliverable

- **UAT JSON**: `uat/HO-P1Q3_UAT.json` (12 tests across 4 sections)
- **Local path**: `G:\My Drive\Code\Python\harmonylab\uat\HO-P1Q3_UAT.json`
- **GCS**: `gs://corey-handoff-bridge/harmonylab/outbox/HO-P1Q3_UAT.json`

---

## What's Next

- The `DEFAULT_CHORD_WINDOW_BEATS` is now 2.0 (half-measure). For jazz standards with very frequent chord changes (2+ per measure), this may merge distinct chords. The parameter is already exposed on `parse_midi_file(chord_window_beats=...)` for per-file tuning.
- The "Maj" chord type suffix ("CMaj" vs "C") is inherited from `CHORD_TEMPLATES`. Some downstream consumers may expect bare root names for major triads. Not addressed per task scope.
- Branch mismatch (master vs main) still exists. Not addressed per task scope.
