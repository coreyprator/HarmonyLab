# Session Close-Out: HL-REGRESSIONS-001 (PTH-HM03)

## Session Overview
- **Date:** 2026-03-14
- **Project:** HarmonyLab
- **Branch:** main
- **Agent:** CC
- **Sprint:** HL-REGRESSIONS-001 (PTH-HM03)
- **Version:** v2.11.0 → v2.12.0
- **Commits:** 50e827e (fixes), 6875ef1 (PK)
- **Backend Revision:** harmonylab-00161-xh5
- **Frontend Revision:** harmonylab-frontend-00079-wz4

---

## What Was Done

### Fix 1 — Note count badge regression
- **Root cause:** Badge only rendered when `currentView === 'analysis'`. PL viewing in "chords" mode couldn't see badges.
- **Fix:** Removed view gate — badges now show in both analysis and chords views.
- **File:** frontend/song.html line 782

### Fix 2 — Transpose chord symbol spelling
- **Root cause:** `transpose_chord_symbol()` in analysis.py used `use_flats = accidental == 'b' or semitones < 0`. Natural-root chords transposed up got sharp names (D# instead of Eb), causing music21 to produce `#II` instead of `III`.
- **Fix:** `use_flats = new_pc in (1, 3, 6, 8, 10)` — always use flat spelling for black-key pitch classes.
- **Result:** Eb13=III13 (was D#13=#II13), AbMaj9=VIMaj9 (was G#Maj9=#VMaj9)
- **File:** app/api/routes/analysis.py line 50

### Fix 3 — Score playback rework
- **Root cause:** `togglePlayPause()` only reloaded chord `part` after `stop()`, ignoring `scoreMode`/`scorePart`. In score mode, Play after Stop produced silence.
- **Fix:** `togglePlayPause()` now checks `scoreMode` and reloads `scorePart` via `loadScoreNotes()` when disposed. Play button shows "Score" label in score mode.
- **File:** frontend/song.html lines 2371-2389, 2421-2428

---

## What Was NOT Done
- No new features — regression fixes only per intent boundaries.
- MetaPM HL-035 already at cc_complete from HC01, not re-walked.

---

## Gotchas / Rediscovery Traps
- GitHub Actions CI/CD auto-deploys on push to main — my manual `gcloud run deploy` competed with it and lost the revision race. The GA revision (00161) is the active one. Both contain the same code.
- `E7#9 → #III7#9` in C minor is CORRECT (E natural is raised 3rd in C minor). Only D#/G#/A# spellings were wrong.
- The `packed-refs.lock` warning in git is persistent on this repo but commits still succeed.
- `harmony.rentyourcio.com` DNS does not resolve from this machine — use `harmonylab-frontend-wmrla7fhwa-uc.a.run.app` for curl tests.

---

## Environment State at End
- **Backend:** v2.12.0, revision harmonylab-00161-xh5
- **Frontend:** v2.12.0, revision harmonylab-frontend-00079-wz4
- **GCP Project:** super-flashcards-475210

---

## Files Modified
| File | Changes |
|------|---------|
| app/api/routes/analysis.py | transpose_chord_symbol flat spelling fix |
| frontend/song.html | Note count badge view gate removed, togglePlayPause score reload, play button label |
| frontend/index.html | v2.12.0 |
| frontend/quiz.html | v2.12.0 |
| frontend/progress.html | v2.12.0 |
| frontend/audit.html | v2.12.0 |
| frontend/riffs.html | v2.12.0 |
| main.py | v2.12.0 |
| PROJECT_KNOWLEDGE.md | v2.12.0 history entry |

---

## MetaPM Handoff
- **UAT ID:** 16747974-8919-4378-B87A-228AF4FA2D04
- **Handoff ID:** F5420FB7-8354-4BCD-8151-2476114EF7D4
- **HL-035:** cc_complete (reworked)
