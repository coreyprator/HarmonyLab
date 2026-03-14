# Corcovado — Analysis Review for Darren

**Prepared:** March 2026
**Source:** Corcovado.mid (Song ID 87, Version 3)
**Key Detection:** A minor
**Tempo:** 113 BPM | Time Signature: 2/2
**Total Chords:** 72 | **Total Notes:** 272 (from note data) | **Measures:** 93

---

## Algorithm Version

Roman numeral analysis: HarmonyLab v2.13.0 (music21-based, algorithm v1.1)
All chords below are algorithm-generated — no RLHF corrections applied to this version.

---

## Full Chord List with Roman Numerals

| Measure | Chord Symbol | Roman Numeral | Function | Notes |
|--------:|:-------------|:--------------|:---------|------:|
| 1 | A | I | tonic | 2 |
| 2 | B | II | subdominant | 3 |
| 4 | D9 | IV9 | subdominant | 2 |
| 7 | Db7#9 | bIV7#9 | subdominant | 5 |
| 8 | EbMaj9 | bVMaj9 | dominant | 2 |
| 9 | A | I | tonic | 6 |
| 10 | C13 | III13 | tonic | 2 |
| 12 | FMaj9 | VIMaj9 | tonic | 1 |
| 13 | D | IV | subdominant | 6 |
| 14 | Bb13 | bII13 | subdominant | 2 |
| 16 | CMaj9 | IIIMaj9 | tonic | 1 |
| 18 | E | V | dominant | 2 |
| 19 | A | I | tonic | 3 |
| 20 | C | III | tonic | 2 |
| 21 | D7 | IV7 | subdominant | 4 |
| 22 | B | II | subdominant | 3 |
| 23 | Db7 | bIV7 | subdominant | 3 |
| 24 | D9 | IV9 | subdominant | 1 |
| 25 | D | IV | subdominant | 5 |
| 26 | D9 | IV9 | subdominant | 2 |
| 27 | C | III | tonic | 6 |
| 29 | E7b9 | V7b9 | dominant | 5 |
| 30 | D | IV | subdominant | 2 |
| 31 | E7b9 | V7b9 | dominant | 6 |
| 32 | G7#9 | VII7#9 | dominant | 1 |
| 33 | C | III | tonic | 5 |
| 34 | C9 | III9 | tonic | 2 |
| 35 | E | V | dominant | 6 |
| 36 | E7b9 | V7b9 | dominant | 2 |
| 39 | F6/9 | vi6/9 | secondary | 5 |
| 41 | Fm9 | vim9 | tonic | 5 |
| 42 | F | VI | tonic | 2 |
| 43 | Bb | bII | subdominant | 7 |
| 45 | E7b9 | V7b9 | dominant | 5 |
| 46 | E | V | dominant | 2 |
| 47 | A | I | tonic | 7 |
| 49 | D13 | IV13 | subdominant | 6 |
| 50 | D | IV | subdominant | 2 |
| 51 | D13 | IV13 | subdominant | 4 |
| 52 | D | IV | subdominant | 3 |
| 53 | Dm7 | ivm7 | subdominant | 4 |
| 54 | E | V | dominant | 3 |
| 55 | E7b9 | V7b9 | dominant | 6 |
| 56 | Gbm | bviim | dominant | 4 |
| 57 | D | IV | subdominant | 5 |
| 58 | D9 | IV9 | subdominant | 2 |
| 59 | C | III | tonic | 6 |
| 61 | E7b9 | V7b9 | dominant | 5 |
| 62 | D | IV | subdominant | 2 |
| 63 | E7b9 | V7b9 | dominant | 6 |
| 64 | G7#9 | VII7#9 | dominant | 2 |
| 66 | C | III | tonic | 3 |
| 67 | C11 | III11 | tonic | 6 |
| 68 | Gb9 | bVII9 | dominant | 2 |
| 71 | F6/9 | vi6/9 | secondary | 6 |
| 73 | Fm7 | vim7 | tonic | 4 |
| 74 | Fm11 | vim11 | tonic | 4 |
| 75 | E7alt | V7alt | chromatic | 5 |
| 77 | Em7 | vm7 | dominant | 4 |
| 78 | FMaj9 | VIMaj9 | tonic | 4 |
| 79 | Am11 | im11 | tonic | 5 |
| 81 | Dm7 | ivm7 | subdominant | 5 |
| 82 | Dm11 | ivm11 | subdominant | 4 |
| 83 | Fm9 | vim9 | tonic | 4 |
| 84 | B7alt | II7alt | chromatic | 3 |
| 85 | Eø7 | vm7b5 | dominant | 4 |
| 87 | A7 | I7 | tonic | 4 |
| 89 | Dm7 | ivm7 | subdominant | 4 |
| 90 | Dm11 | ivm11 | subdominant | 4 |
| 91 | Fm9 | vim9 | tonic | 4 |
| 92 | B7alt | II7alt | chromatic | 3 |
| 93 | Am7 | im7 | tonic | 5 |

---

## Questions for Darren

### Q1: Measure 21 — D7 as IV7

The algorithm labels D7 as **IV7** (subdominant function). In jazz analysis of a Jobim tune in A minor, is D7 better understood as:
- **IV7** (D Mixolydian, subdominant) — as the algorithm suggests
- **V7/V** (secondary dominant resolving to E) — which would be more conventional if it resolves to the V chord

The algorithm does not currently detect secondary dominants. If D7 → E is a V/V resolution, should we flag these systematically?

### Q2: Measures 41, 83, 91 — Fm9 as vim9

Fm9 appears three times, labeled **vim9** (tonic function). In A minor context:
- F is the bVI degree — should this be **bVIMaj9** or **bVI9** rather than "vi" (which implies the 6th degree of the major scale)?
- The lowercase "vi" suggests minor quality, which Fm9 is — but the degree labeling relative to A minor may be confusing
- Originally flagged as AbMaj13 in an earlier version — is Fm9 the correct chord identification here, or is the voicing actually an Ab chord with F in the bass?

### Q3: Measures 32, 64 — G7#9 as VII7#9

G7#9 is labeled **VII7#9** (dominant function). Questions:
- In A minor, G is bVII — should this be **bVII7#9** instead of VII7#9?
- Is G7#9 functioning as a tritone substitution, a passing dominant, or a bVII blues chord in this context?
- The #9 voicing (G-B-D-F-A#) has strong blues/funk character — is this idiomatic for Corcovado's bossa nova style, or is the algorithm misidentifying the chord?

### Q4: Measure 56 — Gbm as bviim

Gbm (F#m enharmonic) labeled **bviim** — this is unusual:
- Is F#m/Gbm correct here, or should this be F#dim7 or some other chord?
- bviim is extremely rare in jazz harmony — what function does this serve in the progression?

### Q5: Measures 84, 92 — B7alt as II7alt

B7alt labeled **II7alt** (chromatic function):
- B7 in A minor is more commonly analyzed as **V7/V** (secondary dominant to E)
- The "alt" voicing (altered dominant) strongly suggests dominant function — is II7alt the right label, or should this be V7alt/V?

### Q6: General — Roman numeral conventions for jazz

Several numerals use extensions directly on the roman numeral (IV9, III13, VIMaj9, etc.). Darren's preference:
- Should extensions appear on the roman numeral (IV9) or only on the chord symbol (D9)?
- For jazz lead sheets, is there a preferred notation standard?

---

## RLHF Correction Count

**0 corrections** applied to Corcovado (Version 3, Song ID 87).
All analysis is algorithm-generated. Any corrections from Darren's review can be submitted via the RLHF override system.

---

## Notes

- Song 81 (MuseScore import, 48 measures, 327 notes) provides an alternative analysis from the .mscz file — compare if needed
- Song 23 (original MIDI import, pre-v2.5.0) has no note data — would need re-import for note counts
- The algorithm classifies "function" broadly as tonic/subdominant/dominant/chromatic/secondary — Darren may want finer-grained functional labels
