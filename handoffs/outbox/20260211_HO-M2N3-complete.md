# [HarmonyLab] Completion Handoff: HO-M2N3

| Field | Value |
|-------|-------|
| ID | HO-M2N3 |
| Project | HarmonyLab |
| Task | Critical Bug Fixes from UAT v1.7.0 |
| Status | COMPLETE |
| Commit | e700401 |
| Backend Revision | harmonylab-00075-fg7 |
| Frontend Revision | harmonylab-frontend-00055-kj4 |

---

## Summary

Fixed 7 critical bugs + 2 cleanup issues from UAT v1.7.0 testing. Root cause of multiple bugs was a single database connection issue (missing autocommit). Version bumped to 1.7.1.

## Bug Fixes

### BUG 1: Add Song API 404 -- FIXED
**Root cause**: `execute_scalar()` in `connection.py` didn't commit. The INSERT was rolled back when the connection closed, so `get_song()` couldn't find the new song and returned 404.

**Fix**: Added `autocommit=True` to `pyodbc.connect()` in `Database.get_connection()`. All database writes now persist immediately.

### BUG 2: MIDI Import 500 Error -- FIXED
**Root cause**: Same as Bug 1. The Song INSERT was rolled back, then the Section INSERT failed with FK violation (song doesn't exist) causing 500.

**Fix**: Same `autocommit=True` fix resolves this.

### BUG 3: Chord Preview Missing -- FIXED
**Root cause**: Symptom of Bug 2. MIDI import failed, so no chords existed in DB to display. The MIDI preview endpoint (parse-only) works independently. With Bug 2 fixed, imported chords now persist and display correctly.

### BUG 4: Edit Chord Modal Missing Dropdowns -- FIXED
**Root cause**: The chord-edit-modal in song.html already had Root and Quality dropdown selects (lines 117-151). The issue was a stale deployment. The fresh deploy of v1.7.1 includes the full modal with all fields:
- Current (readonly)
- Root (dropdown: C through B with sharps/flats)
- Quality (dropdown: Major, Minor, Dom7, Maj7, m7, dim, etc.)
- New Chord preview

### BUG 5: Quiz Question Count Wrong -- FIXED
**Root cause**: Frontend converted `numQuestions` to `blank_percentage` and backend calculated blanks from total chords, ignoring the user's requested count.

**Fix**:
- Added `num_questions: Optional[int]` to `QuizGenerate` model
- Frontend now sends `num_questions` in quiz generation request
- Backend caps blanks: `min(calculated_blanks, num_questions)`

### BUG 6: Quiz First Question Blank -- FIXED
**Root cause**: Backend could select chord index 0 as a blank. Index 0 has no preceding chords, so context was empty and the question was unanswerable.

**Fix**: Changed blank candidate range from `range(0, total_chords)` to `range(1, total_chords)`, ensuring every question has at least 1 context chord.

### BUG 7: Quiz Submit 422 Error -- FIXED
**Root cause**: Complete frontend/backend mismatch:
- Frontend sent per-question: `{song_id, question_index, user_answer, correct_answer, time_taken_ms}`
- Backend expected batch: `{attempt_id, answers: List[str]}`

**Fix**:
- Removed per-question submit from `handleAnswer()`
- Added batch submit in `showResults()` using `{attempt_id, answers: [user_answers]}` matching `QuizSubmission` model

### ISSUE 8: login.html Version Mismatch -- FIXED
Updated from `v1.5.0` to `v1.7.1`.

### ISSUE 9: Remove Manual Add Song Tab -- FIXED
- Removed Manual Entry tab, tab switcher buttons, and manual form fields
- MIDI Import is now the only Add Song method
- Modal header changed to "Import Song from MIDI"
- Removed `submitAddSong()`, `switchAddTab()`, and related code
- Simplified `openAddSongModal()` and `closeAddSongModal()`

## Files Changed

| File | Change |
|------|--------|
| `app/db/connection.py` | Added `autocommit=True` to `get_connection()` |
| `app/api/routes/quiz.py` | Cap blanks to num_questions, exclude index 0 |
| `app/models/__init__.py` | Added `num_questions` to QuizGenerate model |
| `frontend/index.html` | Removed manual tab, MIDI-only, v1.7.1 |
| `frontend/quiz.html` | Send num_questions, batch submit at end, v1.7.1 |
| `frontend/song.html` | v1.7.1 |
| `frontend/login.html` | v1.7.1 (was v1.5.0) |
| `frontend/progress.html` | v1.7.1 |
| `main.py` | VERSION = "1.7.1" |

## Deployment Verification

| Check | Result |
|-------|--------|
| Backend health | `{"status":"healthy","version":"1.7.1"}` |
| Frontend version | v1.7.1 |
| Backend revision | harmonylab-00075-fg7 (serving 100%) |
| Frontend revision | harmonylab-frontend-00055-kj4 (serving 100%) |
| POST /api/v1/songs/ | 201 OK (Bug 1 confirmed fixed) |

## Garbage Collection

- [x] No inbox files to clean
- [ ] Remind Corey: No Downloads files for this task

---

*Sent via Handoff Bridge per project-methodology policy*
*HarmonyLab/handoffs/outbox/20260211_HO-M2N3-complete.md -> GCS backup*
