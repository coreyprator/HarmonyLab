# CC Task: Fix HarmonyLab MIDI Import — P0 Bug
**Date:** 2026-02-15
**Priority:** P0 — Blocking all HarmonyLab vision development
**Project:** HarmonyLab 🔵
**Type:** Bug Fix — Chord Extraction from MIDI

---

## PRE-WORK (Do these FIRST, in order)

1. **Read** `Harmony Lab PROJECT_KNOWLEDGE.md` in the project root — this is the canonical reference
2. **Read** `CLAUDE.md` in the project root — these are your directives
3. **Verify GCP project:**
   ```bash
   gcloud config get-value project
   # MUST return: super-flashcards-475210
   ```
4. **State project identity before any code changes:**
   - Service name: `harmonylab`
   - Database: `HarmonyLab`
   - DB user: `harmonylab_user`
   - Secret Manager key: `harmonylab-db-password`
   - Cloud SQL instance: `flashcards-db` at `35.224.242.223`
   - Domain: `harmonylab.rentyourcio.com`

---

## BUG DESCRIPTION

**Symptom:** MIDI file import completes without error, but the imported song shows **"No chords found"** in the UI.

**Reproduction:**
- File used: "Prelude I in C major BWV 846" (Bach) — standard MIDI file
- The file imports successfully (a song record is created in the database)
- But zero chords are extracted/associated with the song
- One working song already exists in the database: **Corcovado** — use this as your reference for what correct data looks like

**Root Cause Hypothesis:** The chord extraction/analysis logic that runs during or after MIDI import is either failing silently, applying filters that discard all results, or not being triggered at all.

---

## DIAGNOSTIC PLAN

Execute these steps **in order** and report findings at each stage before proceeding.

### Phase 1: Understand the Working Case
1. Query the database for the Corcovado song and its associated chords:
   ```sql
   -- Find the song
   SELECT * FROM songs WHERE name LIKE '%Corcovado%';
   
   -- Find its chords (adjust table/column names based on what you find in schema)
   SELECT * FROM chords WHERE song_id = <corcovado_id> ORDER BY position;
   -- or: SELECT * FROM song_chords WHERE song_id = <corcovado_id>;
   ```
2. Document: How many chords does Corcovado have? What do the chord records look like (columns, data types, sample values)?
3. This is your **golden reference** — the MIDI import fix must produce comparable output.

### Phase 2: Understand the Broken Case
1. Query the database for the Bach Prelude import:
   ```sql
   SELECT * FROM songs WHERE name LIKE '%Bach%' OR name LIKE '%Prelude%' OR name LIKE '%BWV%';
   ```
2. Check if ANY chord records exist for this song (even malformed ones)
3. Check if there are any error logs, import logs, or status fields that indicate what happened

### Phase 3: Trace the MIDI Import Code Path
1. Find the MIDI import endpoint (likely in a router file — check `/routers/`, `/api/`, or similar)
2. Trace the full pipeline from HTTP request to database insert:
   - **MIDI parsing** — what library is used? (e.g., `mido`, `pretty_midi`, `music21`)
   - **Chord extraction/analysis** — where does note data get converted into chord symbols?
   - **Database insertion** — what gets written to which tables?
3. Identify every point where data could be lost or filtered out:
   - Are there minimum note thresholds?
   - Time window/quantization settings that might be too narrow or too wide?
   - Key detection that fails and causes downstream abort?
   - Exception handling that swallows errors silently?
   - Chord recognition algorithms that don't match the musical content?

### Phase 4: Identify the Specific Failure
Based on Phase 3, determine exactly WHERE in the pipeline chords are lost. Common failure modes to check:

- **Silent exception:** A try/except block catches an error during chord analysis and returns empty results
- **Quantization mismatch:** The Bach Prelude is arpeggiated (notes played sequentially, not simultaneously) — if the chord detector only looks for notes sounding at the exact same time, it will find zero chords. This is the MOST LIKELY cause for a Bach prelude.
- **Channel/track filtering:** MIDI channels or tracks being excluded
- **Velocity or duration thresholds:** Filtering out notes that don't meet minimum criteria
- **Empty result handling:** The import "succeeds" but writes zero chord records without raising an error

> **CRITICAL MUSICAL CONTEXT:** Bach's Prelude in C (BWV 846) is an **arpeggiated** piece — each chord is broken into individual notes played in sequence, NOT struck simultaneously. A naive chord detector that only groups simultaneously-sounding notes will find nothing. The chord extraction MUST use a time-window approach to group notes that fall within the same beat or measure into chords.

---

## FIX REQUIREMENTS

1. **The fix must handle arpeggiated passages** — group notes within a configurable time window into chords
2. **The fix must not break Corcovado** — verify Corcovado's chord data is unchanged after the fix
3. **The fix must produce chords for the Bach Prelude** — re-import and verify chords appear
4. **No silent failures** — if chord extraction produces zero results, log a warning (don't just silently succeed)
5. **The chord extraction parameters should be reasonable defaults** but configurable where practical

---

## TESTING & VERIFICATION

### Required Tests
1. **Database before/after for Corcovado:**
   ```sql
   -- Run BEFORE any changes and AFTER to confirm no regression
   SELECT COUNT(*) as chord_count FROM chords WHERE song_id = <corcovado_id>;
   ```
2. **Re-import Bach Prelude and verify chords:**
   - Delete the existing broken Bach import
   - Re-import the MIDI file through the API/UI
   - Query the database to confirm chords were created:
   ```sql
   SELECT COUNT(*) as chord_count FROM chords WHERE song_id = <bach_id>;
   SELECT TOP 10 * FROM chords WHERE song_id = <bach_id> ORDER BY position;
   ```
3. **Sanity check the extracted chords:**
   - BWV 846 opens with C major, moves to Dm7, G7, etc.
   - The first several extracted chords should be recognizable jazz/classical harmony
   - If the chord symbols look like garbage, the extraction logic needs more work

### Health Check
```bash
curl https://harmonylab.rentyourcio.com/health
# Verify version number matches your bump
```

---

## DEFINITION OF DONE (Hard Gates — ALL required)

- [ ] Version bumped in canonical location (check PROJECT_KNOWLEDGE.md for where version lives)
- [ ] Root cause identified and documented in handoff
- [ ] Fix implemented and tested locally
- [ ] Corcovado chord data unchanged (no regression)
- [ ] Bach Prelude re-imported with chords successfully extracted (include count and sample)
- [ ] All changes committed: `fix: MIDI import chord extraction for arpeggiated passages (HO-XXXX)`
- [ ] Pushed to remote (stage specific files — NO `git add -A`)
- [ ] Deployed to Cloud Run
- [ ] Health check passes with new version
- [ ] Handoff created, uploaded to GCS (`gs://corey-handoff-bridge/harmonylab/outbox/`), URL provided

---

## VOCABULARY LOCKDOWN

Do NOT say "Fixed", "Done", "Working", "Complete", or "Implemented" unless you can show:
- Deployed Cloud Run revision URL
- Health check output with matching version
- Database query output showing chords exist for Bach Prelude
- Database query output showing Corcovado unchanged

Without all of the above, say: **"Code written. Pending deployment and testing."**

---

## KNOWN CONTEXT (from Knowledge Recovery review)

- Audio playback IS working (CC doc said it wasn't — it is)
- Quiz feature IS working (CC doc said it wasn't — it is)
- Roman numeral display IS fixed (CC doc said it wasn't — it is)
- Branch mismatch exists (master vs main) — CI/CD may not auto-fire. Note this in handoff but do NOT attempt to fix the branch issue in this task.
- Frontend directory may be untracked in git — note but do NOT fix in this task
- Auth is built but not enforced — do NOT touch auth in this task

**SCOPE:** Fix MIDI import chord extraction ONLY. Do not touch anything else.

---

## HANDOFF TEMPLATE

Your handoff must include:
```
## What Was Done
- Root cause: [specific description]
- Fix: [what you changed and why]
- Files modified: [list]

## Verification
- Corcovado before: [X] chords → after: [X] chords (unchanged)
- Bach Prelude: [X] chords extracted, sample: [first 5 chord symbols]
- Health check: [URL and version]
- Deployed revision: [revision name]

## What's Next
- [Any follow-up items discovered]
```

---

*Task created: 2026-02-15*
*Bug tracking: Add to MetaPM as HarmonyLab bug (MetaPM is SOT for bugs)*
