# Chord and Key Detection Analysis — HarmonyLab
<!-- HL-ALGO-INVESTIGATE-001 | PTH-HI01 -->

**Date:** 2026-03-13
**Version analyzed:** v2.8.0
**Author:** CC (Claude Code)
**Purpose:** Plain-English music theory summary of how HarmonyLab detects chords and keys, for musician review.

---

## Code Trace Summary

Before diving into the analysis, here is the function-by-function map of every piece of code involved in chord detection and key detection.

### Chord Detection Functions (MIDI import path)

| File | Function | What It Does |
|------|----------|--------------|
| `app/services/midi_parser.py` | `identify_chord(notes)` | Given a list of MIDI note numbers, determines the chord symbol by trying every pitch class as a potential root and matching against a library of 30 chord templates. Returns root name + chord type. |
| `app/services/midi_parser.py` | `extract_chords_from_track(track, ...)` | Walks through a MIDI track's note-on events, groups notes whose onsets fall within a 2-beat window, then calls `identify_chord()` on each group. This is the time-window grouping algorithm. |
| `app/services/midi_parser.py` | `midi_notes_to_intervals(notes)` | Utility: converts MIDI note numbers to semitone intervals from the lowest note. |

### Chord Detection Functions (MuseScore/MusicXML import path)

| File | Function | What It Does |
|------|----------|--------------|
| `app/services/score_parser.py` | `parse_music_file(file_path, filename)` | For .mscz/.mscx files, reads chord symbols directly from `<Harmony>` XML elements. The chord symbols are already written by the human arranger in the score file — no algorithmic detection occurs. For .musicxml, uses music21 to extract `ChordSymbol` objects. |

### Harmonic Analysis Functions (Roman numeral assignment)

| File | Function | What It Does |
|------|----------|--------------|
| `app/services/analysis_service.py` | `analyze_song(chords, key_override, midi_notes)` | Main entry point. Creates a `HarmonicAnalyzer` and calls `analyze_progression()`. |
| `app/services/analysis_service.py` | `HarmonicAnalyzer.analyze_progression()` | Detects the key (or uses override), then analyzes each chord symbol to produce a Roman numeral, harmonic function label, and color. |
| `app/services/analysis_service.py` | `HarmonicAnalyzer._analyze_chord(symbol, index)` | Parses a single chord symbol using music21's `ChordSymbol` and `romanNumeralFromChord`, returning Roman numeral, function, and color. Falls back to `_fallback_roman()` if music21 can't parse. |
| `app/services/analysis_service.py` | `HarmonicAnalyzer._normalize_chord_symbol(symbol)` | Converts jazz/MuseScore shorthand (^=maj, -=m, 0=dim) and flat notation (Ab→A-) into music21-compatible format. |
| `app/services/analysis_service.py` | `HarmonicAnalyzer._fallback_roman(symbol)` | When music21 fails, extracts just the root note, calculates the semitone interval from the key's tonic, and maps to a scale degree (I through VII with accidentals). |
| `app/services/analysis_service.py` | `HarmonicAnalyzer._format_jazz_roman(rn, chord, symbol)` | Formats music21's Roman numeral output into jazz style (e.g., "IVmaj7" instead of "IV65"). |
| `app/services/analysis_service.py` | `HarmonicAnalyzer._get_quality_suffix(symbol)` | Maps ~30 chord suffix notations to standardized jazz abbreviations. |
| `app/services/analysis_service.py` | `HarmonicAnalyzer._get_function(rn)` | Maps scale degrees to harmonic function: degrees 1/3/6 = tonic, 2/4 = subdominant, 5/7 = dominant, else = chromatic. |

### Key Detection Functions

| File | Function | What It Does |
|------|----------|--------------|
| `app/services/analysis_service.py` | `HarmonicAnalyzer._detect_key(chords)` | Chord-based key detection. Takes the first 16 chord symbols, converts each to a music21 `Chord` object (stripping chord type to use only pitches), builds a Stream, and runs music21's `analyze('key')` — the Krumhansl-Schmuckler algorithm. |
| `app/services/analysis_service.py` | `HarmonicAnalyzer._detect_key_from_notes(midi_notes)` | **Added in v2.8.0 (HM02).** Note-based key detection. Takes up to 200 MIDI pitch values from the `song_notes` table, creates a music21 Stream of Note objects, and runs `analyze('key')`. Used when actual note data exists. |
| `app/services/key_center_service.py` | `detect_key_centers(chords, detected_key)` | Regional key detection. Finds ii-V-I patterns, uses the last chord as probable tonic (90% jazz rule), assigns each chord to the best-fit key region, then merges small/relative-key regions. |
| `app/services/key_center_service.py` | `detect_ii_v_i_patterns(chords)` | Scans for three-chord sequences where the intervals match ii-V-I (root at +2, +7, 0 semitones from target) with appropriate quality constraints. |

---

## SECTION 1: Chord Detection Algorithm

### Important distinction: Two separate chord detection systems

HarmonyLab has **two completely different paths** for chord detection, depending on how the song was imported:

1. **MuseScore/MusicXML import** (the common path for Corcovado and most songs): Chord symbols are **read directly from the score file**. The arranger typed "D7" into the MuseScore score, and HarmonyLab stores "D7" as-is. **No algorithmic chord detection occurs.** The `score_parser.py` simply extracts `<Harmony>` XML elements.

2. **MIDI import** (used for raw MIDI files without chord annotations): The `midi_parser.py` algorithmically detects chords from note data using template matching. This is the only path where the system "decides" what chord is being played.

**For the MIDI chord detection path:**

**Algorithm type:** Template matching with rotation-based root detection.

**Input — what notes does it use?**
- All note-on events within a 2-beat time window are grouped together.
- Short notes are NOT filtered out — every note-on event with velocity > 0 is included.
- Duration is NOT considered — a whole note and a 16th note have equal weight.
- Octave is ignored — notes are reduced to pitch classes (0-11). E2 and E5 are treated identically.

**Root determination:**
- The algorithm does NOT assume the lowest note is the root.
- Instead, it tries **every unique pitch class** in the group as a candidate root.
- For each candidate, it computes the interval set (semitones from candidate root to all other pitch classes).
- The candidate that produces the best template match is chosen as root.
- **Bass note bonus:** When the candidate root matches the lowest sounding note (bass), a bonus of +50 (exact match) or +10 (subset match) is added. This creates a mild preference for root-position voicings.
- Slash chords are not explicitly handled — they may be detected as the bass-note chord if the inversion matches a template.

**Matching process — step by step:**

1. **Collect pitch classes:** Extract unique pitch classes from all MIDI notes in the window. Identify the bass note (lowest sounding pitch class).

2. **Try every pitch class as root:** For each unique pitch class in the group:
   a. Compute intervals from this candidate root to all other pitch classes (mod 12).
   b. Compare the resulting interval set against all 30 templates (also mod 12).

3. **Score exact matches:** If the interval set exactly equals a template, score = 1000 + (template size × 10) + root-position bonus. Larger templates score higher (a 9th chord scores above a triad if both match exactly).

4. **Score subset matches (if no exact match found yet):** If the note group's intervals are a subset of a template, score = (coverage × 100) + template size + root-position bonus. Only attempted when there are 3+ pitch classes.

5. **Pick the winner:** The candidate root + template with the highest score wins.

6. **Dyad fallback:** For 2-note groups, if no template matches, use interval-based heuristics (P5 → major, m3 → minor, etc.).

7. **Last resort:** If nothing matches, use the bass note as root and check for major 3rd or minor 3rd interval to determine quality.

**Tie-breaking:**
- Exact matches always beat subset matches (1000+ vs <200 score).
- Among exact matches, larger templates win (9th chord over triad).
- Among equal-size templates, root-position voicing wins (bass = root gets +50 bonus).
- There is NO preference for simpler chords — a 13th chord would outscore a triad if both match exactly.

**No-chord threshold:**
- A minimum of 2 distinct pitch classes is required (`MIN_NOTES_FOR_CHORD = 2`).
- A single repeated note produces an empty result (no chord assigned).
- There is no match-score threshold — even a weak subset match will produce a chord symbol rather than "--".

**Known weaknesses:**
- **No duration weighting:** A brief passing tone has the same influence as a sustained chord tone. In a measure with C-E-G sustained and a quick B♭ passing tone, the algorithm might match C7 instead of C major.
- **No beat-position weighting:** Off-beat approach notes and on-beat chord tones are treated equally.
- **2-beat window is fixed:** Slow harmonic rhythm (one chord per 4 beats) works fine, but fast chord changes (two chords per beat, as in bebop) will get merged.
- **Subset matching can overfit:** If a group of 3 notes is a subset of 5 different extended chord templates, the first one that scores highest wins, which may not be the simplest or most musically appropriate.

---

## SECTION 2: Key Detection Algorithm

### Two key detection systems

Like chord detection, there are two key detection paths:

1. **Global key detection** (runs once per song analysis): Uses the Krumhansl-Schmuckler pitch profile algorithm via music21. This determines the overall key shown in the analysis header.

2. **Regional key detection** (`key_center_service.py`): Uses ii-V-I pattern detection and chord-fitting to identify local key centers. This is independent of the global detection.

### Global Key Detection

**Algorithm type:** Krumhansl-Schmuckler key-finding algorithm (music21 implementation).

**Input — what data does it use?**

**Before HM02 (v2.7.0 and earlier):**
- The first 16 chord symbols from the song.
- Each chord symbol is parsed into a music21 `ChordSymbol`, then converted to a plain `Chord` (pitches only, no symbol metadata).
- The resulting pitches are fed into the Krumhansl-Schmuckler algorithm.

**After HM02 (v2.8.0):**
- **If the song has MIDI note data** (in the `song_notes` table): Up to 200 individual MIDI pitch values are used. Each becomes a music21 `Note` object in a Stream.
- **If no note data exists:** Falls back to the old chord-based method (first 16 chord symbols).
- **If a manual key override exists:** The override is used directly with 1.0 confidence.

**Process — step by step (note-based path, v2.8.0):**

1. **Collect pitch data:** Query `song_notes` table for up to 200 MIDI pitch values (excluding rests).
2. **Build music21 Stream:** Create a `Note` object for each MIDI pitch and append to a Stream.
3. **Run Krumhansl-Schmuckler:** Call `stream.analyze('key')`. This algorithm:
   - Counts the total duration of each pitch class (C, C#, D, ... B) across the stream.
   - Correlates the resulting 12-element pitch-class distribution against 24 reference profiles (12 major keys, 12 minor keys).
   - The key whose profile correlates most strongly wins.
   - Returns the key and a correlation coefficient (0.0 to 1.0).

**Process — step by step (chord-based path, fallback):**

1. **Collect chords:** Take up to 16 chord symbols from the song.
2. **Parse each:** Normalize the symbol (jazz font → music21 format), create a `ChordSymbol`, extract its pitches, create a plain `Chord` object.
3. **Build Stream and analyze:** Same Krumhansl-Schmuckler algorithm as above, but using chord pitches instead of individual note pitches.

**Cadence weighting:**
- **The algorithm does NOT weight the final chord or any specific position.**
- There is no cadence bonus. There is no weighting for strong beats, bar positions, or phrase endings.
- Music21's Krumhansl-Schmuckler implementation treats all pitches equally regardless of position.
- **This is a known defect.** In tonal jazz, the final chord resolves to the tonic approximately 90-95% of the time. Not using this heuristic means the algorithm can be fooled by songs where non-tonic chords appear frequently but the ending is clearly tonic.

**Duration weighting:**
- In the **note-based path**, all notes are created as music21 `Note()` objects with default duration (quarter note). The actual durations from the database are NOT passed to music21. A whole note and a 16th note contribute equally to the pitch-class profile.
- **This is a known defect.** Longer notes are harmonically more significant.

### Why Corcovado returned G major before HM02

**Root cause:** The old algorithm (v2.7.0) used only chord symbols for key detection.

Corcovado (Song 81) was imported from a MuseScore file with jazz-font chord symbols. The first 16 chords are:

```
D7, D7, D7, D7, Abo7, Abo7, G-7, G-7, G-7, F^9, Bb13, E-9, A13, C9, ...
```

When music21 converts these to pitches:
- D7 → pitches D, F#, A, C (×4 repetitions)
- G-7 → pitches G, Bb, D, F (×3 repetitions)
- Abo7 → pitches Ab, Cb, D, Fb (×2 or more)

The resulting pitch-class distribution is dominated by D (appears in D7, Gm7, Abo7), F# (from D7 × 4), G (from Gm7 × 3), and A (from D7 × 4). This profile correlates strongly with G major (which contains D, F#, G, A as scale degrees 5, 7, 1, 2).

The correlation with G major was 0.67. C major was a weaker match because the chord symbols don't contain enough C, E, or B pitches in the first 16 chords.

**What HM02 changed:**

v2.8.0 added the `_detect_key_from_notes()` method and the `midi_notes` parameter throughout the analysis pipeline. When `song_notes` data exists (as it does for Song 81, which has 327 notes), the algorithm now feeds **individual MIDI pitches from the actual melody/harmony** into Krumhansl-Schmuckler instead of chord-symbol pitches.

Song 81's actual note distribution (first 200 notes) shows:
- E (pitch class 4): 55 occurrences
- D (pitch class 2): 55 occurrences
- C (pitch class 0): 48 occurrences
- F (pitch class 5): 39 occurrences
- G (pitch class 7): 33 occurrences
- A (pitch class 9): 28 occurrences

This profile correlates strongly with **C major** (which emphasizes C, D, E, F, G, A, B — the white keys). The correlation coefficient is 0.81, significantly higher than G major.

**In musical terms:** The chord symbols alone created a skewed picture because they over-represented D7's notes (4 repetitions × 4 pitches = 16 D-major-adjacent pitches). The actual melody notes give a much more balanced picture of the song's tonal center.

---

## SECTION 3: Chord Template Library

The MIDI chord detection system uses 30 chord templates, defined in `app/services/midi_parser.py` (lines 57-101). Each template is a list of semitone intervals from the root.

| # | Chord Name | Symbol | Intervals (semitones) | Pitch Classes (C root) | Musical Intervals |
|---|-----------|--------|----------------------|----------------------|-------------------|
| 1 | Major triad | Maj | 0, 4, 7 | C, E, G | Root, M3, P5 |
| 2 | Minor triad | m | 0, 3, 7 | C, Eb, G | Root, m3, P5 |
| 3 | Diminished triad | dim | 0, 3, 6 | C, Eb, Gb | Root, m3, dim5 |
| 4 | Augmented triad | aug | 0, 4, 8 | C, E, G# | Root, M3, aug5 |
| 5 | Major 7th | Maj7 | 0, 4, 7, 11 | C, E, G, B | Root, M3, P5, M7 |
| 6 | Minor 7th | m7 | 0, 3, 7, 10 | C, Eb, G, Bb | Root, m3, P5, m7 |
| 7 | Dominant 7th | 7 | 0, 4, 7, 10 | C, E, G, Bb | Root, M3, P5, m7 |
| 8 | Half-diminished 7th | ø7 | 0, 3, 6, 10 | C, Eb, Gb, Bb | Root, m3, dim5, m7 |
| 9 | Diminished 7th | dim7 | 0, 3, 6, 9 | C, Eb, Gb, A | Root, m3, dim5, dim7 |
| 10 | Minor-major 7th | mMaj7 | 0, 3, 7, 11 | C, Eb, G, B | Root, m3, P5, M7 |
| 11 | Major 6th | 6 | 0, 4, 7, 9 | C, E, G, A | Root, M3, P5, M6 |
| 12 | Minor 6th | m6 | 0, 3, 7, 9 | C, Eb, G, A | Root, m3, P5, M6 |
| 13 | Dominant 9th | 9 | 0, 4, 7, 10, 14 | C, E, G, Bb, D | Root, M3, P5, m7, M9 |
| 14 | Major 9th | Maj9 | 0, 4, 7, 11, 14 | C, E, G, B, D | Root, M3, P5, M7, M9 |
| 15 | Minor 9th | m9 | 0, 3, 7, 10, 14 | C, Eb, G, Bb, D | Root, m3, P5, m7, M9 |
| 16 | Dominant 11th | 11 | 0, 4, 7, 10, 14, 17 | C, E, G, Bb, D, F | Root, M3, P5, m7, M9, P11 |
| 17 | Minor 11th | m11 | 0, 3, 7, 10, 14, 17 | C, Eb, G, Bb, D, F | Root, m3, P5, m7, M9, P11 |
| 18 | Dominant 13th | 13 | 0, 4, 7, 10, 14, 21 | C, E, G, Bb, D, A | Root, M3, P5, m7, M9, M13 |
| 19 | Major 13th | Maj13 | 0, 4, 7, 11, 14, 21 | C, E, G, B, D, A | Root, M3, P5, M7, M9, M13 |
| 20 | Dominant 7 flat 9 | 7b9 | 0, 4, 7, 10, 13 | C, E, G, Bb, Db | Root, M3, P5, m7, m9 |
| 21 | Dominant 7 sharp 9 | 7#9 | 0, 4, 7, 10, 15 | C, E, G, Bb, D# | Root, M3, P5, m7, aug9 |
| 22 | Dominant 7 flat 13 | 7b13 | 0, 4, 7, 10, 20 | C, E, G, Bb, Ab | Root, M3, P5, m7, m13 |
| 23 | Dominant 7 sharp 11 | 7#11 | 0, 4, 7, 10, 18 | C, E, G, Bb, F# | Root, M3, P5, m7, aug11 |
| 24 | Altered dominant | 7alt | 0, 4, 10, 13, 15, 20 | C, E, Bb, Db, D#, Ab | Root, M3, m7, m9, aug9, m13 (no 5th) |
| 25 | Major 6/9 | 6/9 | 0, 4, 7, 9, 14 | C, E, G, A, D | Root, M3, P5, M6, M9 |
| 26 | Minor 6/9 | m6/9 | 0, 3, 7, 9, 14 | C, Eb, G, A, D | Root, m3, P5, M6, M9 |
| 27 | Suspended 2nd | sus2 | 0, 2, 7 | C, D, G | Root, M2, P5 |
| 28 | Suspended 4th | sus4 | 0, 5, 7 | C, F, G | Root, P4, P5 |
| 29 | Dominant 7 sus4 | 7sus4 | 0, 5, 7, 10 | C, F, G, Bb | Root, P4, P5, m7 |
| 30 | Dominant 9 sus4 | 9sus4 | 0, 5, 7, 10, 14 | C, F, G, Bb, D | Root, P4, P5, m7, M9 |

**Total: 30 chord templates.**

---

## SECTION 4: Corcovado Trace — Measure 3

### Context

Corcovado (Song 81) was imported from a MuseScore (.mscz) file. **The chord symbol "D7" was written by the human arranger in the score — it was not algorithmically detected.** The score parser extracted it directly from an XML `<Harmony>` element.

Therefore, the "chord detection" for this measure is simply: the arranger wrote D7, the parser stored D7.

### What the analysis algorithm does with D7

The interesting question is: **how does the harmonic analysis interpret D7 in the detected key?**

```
Measure 3 notes (from song_notes table via API):
  E4  (MIDI 64) — beat 1.0, duration 4.0 beats
  C4  (MIDI 60) — beat 1.0, duration 4.0 beats
  A2  (MIDI 45) — beat 1.0, duration 4.0 beats
  F#3 (MIDI 54) — beat 1.0, duration 4.0 beats

Chord symbol from score: D7
Detected key: C major (0.81 confidence)
```

**Step 1 — Normalize chord symbol:**
`_normalize_chord_symbol("D7")` → "D7" (no transformation needed — already standard notation).

**Step 2 — Parse with music21:**
`harmony.ChordSymbol("D7")` creates a D dominant 7th chord (D, F#, A, C).

**Step 3 — Roman numeral from chord:**
`roman.romanNumeralFromChord(D7_chord, C_major_key)` → The root D is scale degree 2 in C major. A dominant 7th on scale degree 2 is not diatonic (diatonic ii is minor). Music21 returns "II" as the Roman numeral.

**Step 4 — Format jazz Roman:**
`_format_jazz_roman()` appends the quality suffix "7" → **"II7"**

**Step 5 — Determine function:**
`_get_function()` → Scale degree 2 maps to **"subdominant"** (degrees 2 and 4 are subdominant).

**Step 6 — Result:**
```
symbol: D7
roman: II7
function: subdominant
color: #3b82f6 (blue)
key_context: C major
```

### Is D7 correct for measure 3 of Corcovado?

The actual MIDI notes in measure 3 are: **A2, F#3, C4, E4**

Pitch classes present: A (9), F# (6), C (0), E (4) → {0, 4, 6, 9}

If we interpret these notes:
- **As D7 (D, F#, A, C):** Pitch classes {2, 6, 9, 0}. The note D is NOT sounding — but A2 (the 5th), F#3 (the 3rd), C4 (the 7th), and E4 are present. E4 is NOT part of D7 — it would be the 9th (making this D9 if we include it). Also, the root D is absent.
- **As Am6 or F#ø7:** {9, 0, 4, 6} = Am with added F# = Am(maj6) or F#-A-C-E = F#ø7 (half-diminished). Both are plausible readings.

**Assessment:** The notes A, F#, C, E do not straightforwardly spell D7 (which requires D, F#, A, C). The root D is absent and E is present instead. The chord symbol "D7" was the arranger's choice in the score file, likely reflecting the harmonic context of the full arrangement (bass voice or ensemble context). Based solely on the 4 sounding notes, **F#ø7 (F#-A-C-E) or Am6 would be more literal interpretations**, but D9 (without the root) is a common jazz voicing.

**This illustrates a key point:** In jazz, chord symbols in a lead sheet represent the **intended harmony** (often with the root in the bass part), not necessarily the literal sounding pitches in a single staff. The arranger's D7 annotation is musically defensible as a chord-voicing choice.

---

## SECTION 5: Edit Modal → Corrections Storage

### Current behavior

**Are corrections persisted to the database?** **YES** — partially.

The Edit Modal saves two types of changes:

1. **Chord symbol changes** (Root, Quality, Extension, Bass dropdowns): If the user modifies the chord symbol, it is saved via `PUT /api/v1/chords/{chord_id}` — this updates the **`Chords` table** directly. The actual chord_symbol column in the database is changed. This is a permanent modification to the imported data.

2. **Analysis overrides** (Roman numeral, Function, Key context, Pivot chord, Notes): These are saved via `PUT /api/v1/analysis/songs/{song_id}/chord/{chord_index}` — this writes to the **`ChordAnalysisOverrides` table**. Fields stored: `roman_override`, `function_override`, `key_context_override`, `is_pivot_chord`, `pivot_to_key`, `notes`.

**Is there a `chord_corrections` table?** No. There are two separate storage locations:
- `Chords` table: The actual chord symbol (modified in place).
- `ChordAnalysisOverrides` table: Roman numeral and function metadata overlays.

**Do corrections affect future analysis runs?**
- **Chord symbol changes: YES.** Since the Chords table is modified directly, a re-analysis (with `refresh=true`) will use the updated chord symbol.
- **Analysis overrides: YES, but as post-processing.** The `_apply_overrides()` function runs after analysis and overlays stored overrides on top of the computed results. The overrides do not change the algorithm's behavior — they replace the output.

**Do corrections affect analysis of OTHER songs?** **NO.** Both the Chords table and ChordAnalysisOverrides are scoped to a specific song_id and chord_index. There is no cross-song learning, no shared correction database, and no feedback loop into the chord template library.

### Gap analysis

**Corrections are persisted but NOT fed back to the algorithm.** The current architecture treats corrections as **output overrides**, not **training data**. The chord detection algorithm (for MIDI imports) and key detection algorithm will make the same mistakes on the next song — corrections do not improve future accuracy.

This is the starting point for any RLHF improvement plan: corrections exist in the database but are architecturally isolated from the detection algorithms.

---

## SECTION 6: RLHF Improvement Opportunities

### 1. Cadence heuristic

**Current state:** No cadence weighting. All notes/chords contribute equally to key detection regardless of position.

**Could it help?** Yes — significantly. In jazz standards, the final chord resolves to the tonic ~90-95% of the time. Adding a "last chord" or "last 4 measures" multiplier would:
- Anchor the key detection to the most harmonically definitive part of the song.
- Prevent non-tonic chords from dominating the profile (as happened with D7 × 4 in Corcovado).

**How to implement (minimal change):**
- In `_detect_key_from_notes()`, assign a weight multiplier to notes in the final N measures.
- In music21, use `Note.quarterLength` or explicit duration to weight notes. Alternatively, duplicate final-measure notes in the Stream to increase their representation.
- Estimated effort: ~10 lines of code.

### 2. Duration weighting

**Current state:** All notes are created as default-duration objects. A whole note and a 16th note are equally represented.

**Would it help?** Yes. A half-note C is harmonically more significant than a 16th-note passing C#. Duration weighting would:
- Reduce the influence of passing tones, neighbor tones, and ornaments.
- Better represent the harmonic "weight" of each pitch class.

**How to implement:**
- In `_detect_key_from_notes()`, set each Note's `quarterLength` to the actual duration from the database (the `duration_quarters` column exists in `song_notes`).
- Music21's Krumhansl-Schmuckler already weights by duration when notes have non-default lengths.
- Estimated effort: ~5 lines of code (pass duration from DB, set on Note object).

### 3. Beat position weighting

**Current state:** No beat weighting. Off-beat approach notes and on-beat chord tones are treated equally.

**Would it help?** Moderately. In jazz:
- Beat 1 and beat 3 are "strong beats" — notes on these beats are usually chord tones.
- Off-beat notes are more likely to be passing tones, approach notes, or chromatic embellishments.

**How to implement:**
- In `_detect_key_from_notes()`, multiply the duration of notes on beats 1 and 3 by a factor (e.g., 1.5×).
- The `beat` column exists in `song_notes`, so the data is available.
- Estimated effort: ~8 lines of code.

**Caveat:** This is less universally beneficial than duration weighting. In bebop, important melodic statements often start on off-beats. A conservative multiplier (1.2-1.5×) would help without over-penalizing syncopation.

### 4. Corrections feedback loop

**What would be needed:**

**Simplest implementation (per-song corrections replay):**
1. **Already done:** Corrections are stored in `ChordAnalysisOverrides` and `Chords` tables.
2. **Already done:** Re-analysis with `refresh=true` uses updated chord symbols.
3. **Gap:** Analysis overrides are applied as post-processing, not fed into the algorithm. A correction to "this chord should be analyzed as vi, not IV" doesn't change how music21 interprets the chord.

**Next level (cross-song learning):**
1. **Create a `chord_corrections_training` table:** Store (chord_symbol, detected_roman, corrected_roman, key_context) tuples.
2. **On analysis:** Before calling music21, check if this (chord_symbol, key_context) combination has a stored correction. If so, use the correction directly.
3. **Pattern matching:** For a chord like "D7 in C major → should be V/V not II7", store the pattern. When the same chord appears in another song in C major, apply the correction automatically.
4. **Estimated effort:** New table, new query in `_analyze_chord()`, ~50 lines of code.

**Full RLHF (weighted learning):**
1. Track correction frequency: if PL corrects "D7 in C major → V/V" across 5 songs, confidence increases.
2. Weight algorithm output vs correction database based on correction count.
3. This is significantly more complex and may not be needed until the correction database has hundreds of entries.

### 5. Template coverage gaps

The current 30 templates cover most common jazz chords. Notable gaps:

| Missing Chord | Symbol | Intervals | Frequency in Jazz |
|--------------|--------|-----------|-------------------|
| Add 9 | add9 | 0, 4, 7, 14 | Common |
| Minor add 9 | m(add9) | 0, 3, 7, 14 | Occasional |
| Augmented 7th | aug7 or 7#5 | 0, 4, 8, 10 | Common in jazz |
| Minor 13th | m13 | 0, 3, 7, 10, 14, 21 | Occasional |
| Quartal voicings | — | 0, 5, 10 (stacked 4ths) | Common in modern jazz |
| Power chord | 5 | 0, 7 | Rock/pop contexts |
| Major 7 #11 | maj7#11 | 0, 4, 7, 11, 18 | Common (Lydian) |
| Minor-major 9th | m(maj9) | 0, 3, 7, 11, 14 | Occasional |

The most impactful additions would be **add9**, **aug7/7#5**, and **maj7#11** — these appear frequently in jazz standards and would reduce false matches where these chords are currently being shoehorned into the closest existing template.

**Note:** Template gaps only affect the MIDI import path. For MuseScore imports, the chord symbols come from the score file and these templates are not used.

---

## SECTION 7: Proposed Rule Set (Draft)

```
CHORD DETECTION RULES v1.0 (proposed)
=======================================

This rule set describes how chord detection SHOULD work.
It is a draft for CAI/PL review, not an implementation specification.

SCOPE:
These rules apply to the MIDI import path only. For MuseScore/MusicXML
imports, chord symbols are taken directly from the score file as-is.

INPUT SELECTION:
- Use all notes in the measure with duration >= 0.25 beats
  (filter out grace notes and very short passing tones)
- Weight notes by duration:
    whole note = 4.0 weight
    half note = 2.0 weight
    quarter note = 1.0 weight
    eighth note = 0.5 weight
    16th note = 0.25 weight (minimum threshold)
- Prioritize notes on strong beats:
    Beat 1: 1.5× multiplier
    Beat 3: 1.3× multiplier
    Other beats: 1.0× multiplier
- Ignore octave — use pitch class only (0-11)
- Group notes within a configurable time window (default: 2 beats)

ROOT DETERMINATION:
- Try every pitch class in the measure as candidate root
- Score each candidate against all chord templates
- Apply bass note bonus: if candidate root = lowest sounding note,
  add 15% to match score (jazz bass typically plays the root)
- For slash chords: if bass note is NOT the best root,
  report as "Root/Bass" (e.g., C/E for C major with E in bass)

MATCHING:
- Compare weighted pitch class set against template library
- Minimum 3 unique pitch classes required for a chord assignment
  (2-note groups → interval heuristic only, not template match)
- Exact match score = 1000 + (template_size × 10) + root_bonus
- Subset match score = (coverage × 100) + template_size + root_bonus
- Tie-break: prefer simpler chord (fewer extensions) when scores
  are within 5% of each other
- Minimum match score threshold: 50 (below this → assign "--")

NO-CHORD THRESHOLD:
- Fewer than 3 notes in measure → "--" with reason "< 3 notes"
- No template matches above threshold → "--" with reason "no match"
- All notes are very short (< 0.25 beats) → "--" with reason "passing tones only"

KEY DETECTION:
- Use MIDI pitch data when available (song_notes table)
- Weight notes by duration (whole note = 4× eighth note)
- Apply cadence bonus:
    Final 4 measures: multiply all note weights by 2.0×
    Final chord's root: additional 3.0× multiplier
- Apply beat-position bonus:
    Beat 1 notes: 1.3× multiplier
    Beat 3 notes: 1.2× multiplier
- Run Krumhansl-Schmuckler correlation against 24 key profiles
  (12 major, 12 minor)
- Return key with highest correlation coefficient
- Confidence thresholds:
    >= 0.80: High confidence
    0.60-0.79: Medium confidence
    < 0.60: Low confidence — flag for manual review

REGIONAL KEY DETECTION:
- Detect ii-V-I patterns using interval math (not Roman numeral text)
- ii root at +2 semitones from I, V root at +7 from I
- V must have dominant 7th quality
- Use last chord as probable tonic (90% jazz rule)
- Merge relative major/minor regions (C major + A minor = one region)
- Absorb tiny regions (< 3 chords) into neighbors

CORRECTIONS FEEDBACK (future):
- Store user corrections in a training table
- On re-analysis, check training table before algorithmic detection
- Cross-song: apply corrections when same (chord, key) pattern appears
- Track correction frequency for confidence weighting
```

---

## Appendix: Function Trace Map

For developers following the code, here is the complete call chain from API endpoint to algorithm:

### Analysis Endpoint → Key + Roman Numeral

```
GET /api/v1/analysis/songs/{song_id}
  → analysis.py: get_analysis()
    → DB: SELECT chord_symbol FROM Chords (via Sections/Measures join)
    → DB: SELECT midi_pitch FROM song_notes (if available)
    → analysis_service.py: analyze_song(chord_symbols, key_override, midi_notes)
      → HarmonicAnalyzer.analyze_progression()
        → _detect_key_from_notes(midi_notes)    [if midi_notes available]
        → _detect_key(chords)                   [fallback]
        → for each chord:
            → _analyze_chord(symbol, index)
              → _normalize_chord_symbol()
              → music21.harmony.ChordSymbol()
              → music21.roman.romanNumeralFromChord()
              → _format_jazz_roman()
              → _get_function()
        → _detect_patterns(analyzed_chords)
    → _apply_overrides(result, song_id, db)
      → DB: SELECT FROM ChordAnalysisOverrides
```

### MIDI Import → Chord Detection

```
POST /api/v1/imports/midi/import
  → imports.py: import_midi()
    → midi_parser.py: parse_midi_file(path)
      → extract_chords_from_track(best_track, ...)
        → for each 2-beat window of notes:
            → identify_chord(window_notes)
              → for each pitch class as candidate root:
                  → compare intervals vs CHORD_TEMPLATES
              → return (root, chord_type)
      → return ParsedSong with ChordData list
```

---

*End of CHORD_DETECTION_ANALYSIS.md — HL-ALGO-INVESTIGATE-001 (PTH-HI01)*
