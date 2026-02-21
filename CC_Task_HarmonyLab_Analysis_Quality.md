# CC Task: HarmonyLab Analysis Quality Fixes — 4 UAT Findings

**Date:** 2026-02-15
**Priority:** P1
**Project:** HarmonyLab 🔵
**Type:** Bug Fix — Analysis Quality
**Predecessor:** HO-P1Q2 (MIDI import fix, v1.8.1, 8/10 UAT pass)
**UAT Results:** https://metapm.rentyourcio.com/mcp/handoffs/C006814B-4155-4D0F-B38D-E19B5958A9A2/content

---

## PRE-WORK (Do these FIRST, in order)

1. **Read** `Harmony Lab PROJECT_KNOWLEDGE.md` in the project root
2. **Read** `CLAUDE.md` in the project root
3. **Fetch and read** the UAT results that generated these findings:
   ```bash
   curl https://metapm.rentyourcio.com/mcp/handoffs/C006814B-4155-4D0F-B38D-E19B5958A9A2/content
   ```
4. **Verify GCP project:**
   ```bash
   gcloud config get-value project
   # MUST return: super-flashcards-475210
   ```
5. **State project identity:**
   - Service: `harmonylab`
   - Database: `HarmonyLab`
   - DB user: `harmonylab_user`
   - Secret: `harmonylab-db-password`
   - Cloud SQL: `flashcards-db` at `35.224.242.223`
   - Domain: `harmonylab.rentyourcio.com`
   - Backend direct URL: `harmonylab-57478301787.us-central1.run.app`

---

## CONTEXT

The MIDI import P0 was fixed in v1.8.1 — chord extraction now works for arpeggiated music.
However, UAT revealed 4 quality issues in the analysis and data layers. All 4 must be fixed
in this task.

**Reference data in the database:**
- **Corcovado** — song_id 23, jazz standard, block chords
- **Bach Prelude I in C major BWV 846** — song_id 32, classical, arpeggiated, imported via v1.8.1 fix

---

## FINDING 1: Key Detection is Wrong

**Severity:** High
**Location:** Harmonic analysis engine (likely `app/services/analysis_service.py` or similar)

**Problem:** Bach's Prelude I in C major (BWV 846) is detected as **B minor**. This is incorrect.
The piece is unambiguously in C major — it's one of the most famous C major pieces in the
classical repertoire. B minor is not even the relative minor of C major (that would be A minor).

**Investigation steps:**
1. Find the key detection algorithm — likely in the analysis service
2. Understand how it determines key:
   - Is it using note frequency distribution (Krumhansl-Schmuckler or similar)?
   - Is it looking at first/last chord?
   - Is it using a fixed lookup?
3. Test the algorithm against both songs:
   - Corcovado should detect as a jazz key (F major or A minor are common analyses)
   - Bach BWV 846 should detect as C major
4. Determine why B minor is being selected — is it a bug in the algorithm, or is the input
   data (the extracted chords) misleading the detector?

**Fix requirement:** BWV 846 must detect as C major with reasonable confidence. The detection
algorithm should handle both jazz and classical idioms. If the algorithm is fundamentally
broken, document what would be needed to fix it properly and implement the best available
improvement.

---

## FINDING 2: Chord Naming is Questionable

**Severity:** High
**Location:** Chord identification logic in `app/services/midi_parser.py` (the code modified in HO-P1Q2)

**Problem:** The first chords extracted from BWV 846 are: CMaj, Gsus4, CMaj, Gdim7, C.
While CMaj is correct for beat 1, the subsequent names are musically questionable:

- **Gsus4** — Beat 2 of BWV 846 contains the notes C, E, G, which is still C major (or
  possibly C/E). "Gsus4" would require G, C, D — there's no D in this beat.
- **Gdim7** — This would require G, Bb, Db, Fb. The actual notes in measure 1 of BWV 846
  are all diatonic to C major. A diminished 7th chord shouldn't appear.

**Investigation steps:**
1. Examine the chord identification function — how does it go from a set of MIDI note numbers
   to a chord symbol?
2. Check if notes are being correctly mapped to pitch classes
3. Check if the time-window grouping from HO-P1Q2 is capturing the right notes for each beat
4. Print/log the actual MIDI notes captured for the first 4 beats and compare to what the
   chord namer outputs
5. Cross-reference with the actual score: Measure 1 of BWV 846 arpeggiates C-E-G-C-E (C major)

**Fix requirement:**
- Chord naming must correctly identify the notes being grouped
- Standard chord naming conventions: C (not CMaj for a simple triad unless that's your
  convention — be consistent), Dm7, G7, Am, etc.
- If a set of notes doesn't clearly map to a known chord, the symbol should reflect
  uncertainty (e.g., "C/E" for an inversion, or flag as ambiguous) rather than producing
  a confidently wrong name like Gdim7

**Musical reference for validation:**
BWV 846 measure-by-measure harmony (first 8 measures):
1. C major
2. Dm7 (or Dm9)
3. G7 (or G/B)
4. C major (or Am7)
5. Am (or Am/E)
6. D7 (or D/F#)
7. G major
8. Cmaj7 (or C/E)

---

## FINDING 3: Corcovado Chord Count Drifted (45 → 47)

**Severity:** Medium
**Location:** Database / chord extraction pipeline

**Problem:** The HO-P1Q2 handoff stated: "Corcovado: 45 chords before → 45 chords after."
UAT found 47 chords. Either:
- CC miscounted during verification (most likely)
- The algorithm rewrite subtly changed how Corcovado's chords are stored or counted
- Additional chords were created during testing/re-import

**Investigation steps:**
1. Count Corcovado's chords definitively:
   ```sql
   -- Adjust table/column names based on actual schema
   SELECT COUNT(*) FROM chords WHERE song_id = 23;
   ```
2. Check if any duplicate chords exist:
   ```sql
   SELECT measure_id, beat, COUNT(*) as cnt
   FROM chords WHERE song_id = 23
   GROUP BY measure_id, beat
   HAVING COUNT(*) > 1;
   ```
3. Check the git history — did the v1.8.1 migration or code change affect existing data?
4. If the count is now correctly 47 and was always 47 (CC just miscounted), document this
   as the actual count. If duplicates exist, remove them.

**Fix requirement:** Establish the correct chord count and ensure no duplicates. Update any
documentation that references the count.

---

## FINDING 4: Measure Numbering is Sequential Instead of by Bar

**Severity:** Medium
**Location:** MIDI import or measure creation logic

**Problem:** Measures are labeled sequentially as 1, 2, 3, 4 instead of by actual bar number
from the score (1, 5, 9, 13 for groups of 4 bars). The UAT noted measures are grouped in
sets of 4 bars, each labeled 1, 2, 3, 4.

**Investigation steps:**
1. Query the measures for Bach Prelude:
   ```sql
   SELECT * FROM measures WHERE song_id = 32 ORDER BY position;
   -- or: via section → measures
   ```
2. Understand the data model:
   - Is `measure_number` auto-incremented during import?
   - Does the MIDI parser calculate bar numbers from MIDI tick positions?
   - Is there a `section` → `measure` hierarchy that resets numbering per section?
3. Determine what "4 bars grouped" means — are sections being created with 4 measures each,
   resetting the measure counter?

**Fix requirement:**
- Measure numbers should represent actual bar numbers in the piece (1, 2, 3, 4, 5, 6, ...)
  running sequentially through the entire song, NOT resetting per section
- If sections exist, measure numbers should still be globally sequential
- Verify this fix doesn't break Corcovado's existing measure numbering

---

## TESTING & VERIFICATION

### For Each Finding:

**Finding 1 — Key Detection:**
```bash
# After fix, call analysis endpoint and confirm key
curl https://harmonylab-57478301787.us-central1.run.app/api/v1/analysis/songs/32
# Expected: detected_key contains "C major" (not B minor)
```

**Finding 2 — Chord Naming:**
```sql
-- Query first 8 chords for Bach Prelude, report symbols
SELECT TOP 8 c.* FROM chords c
JOIN measures m ON c.measure_id = m.id
WHERE m.song_id = 32
ORDER BY m.position, c.beat;
-- Symbols should be recognizable harmony: C, Dm7, G7, Am, etc.
```

**Finding 3 — Corcovado Count:**
```sql
SELECT COUNT(*) as chord_count FROM chords WHERE song_id = 23;
-- Document the actual correct count
-- Confirm no duplicates exist
```

**Finding 4 — Measure Numbers:**
```sql
SELECT m.measure_number, m.position FROM measures m
WHERE m.song_id = 32 ORDER BY m.position;
-- Numbers should run 1, 2, 3, 4, 5... not restart at 1
```

### Regression:
- Corcovado audio playback still works
- Corcovado chord display unchanged (symbols, order)
- Quiz still generates questions for Corcovado
- Bach Prelude still shows chords (no regression from P0 fix)

### Health Check:
```bash
curl https://harmonylab.rentyourcio.com/health
# Version must be bumped (1.8.2 or whatever is appropriate)
```

---

## DEFINITION OF DONE (Hard Gates)

- [ ] Version bumped in canonical location
- [ ] All 4 findings addressed with root cause documented
- [ ] Changes committed: `fix: analysis quality — key detection, chord naming, measure numbering (HO-XXXX)`
- [ ] Pushed to remote (stage specific files — NO `git add -A`)
- [ ] Deployed to Cloud Run
- [ ] Health check passes with new version
- [ ] Key detection returns C major for BWV 846
- [ ] First 8 chord symbols for BWV 846 are musically reasonable
- [ ] Corcovado chord count documented (no duplicates)
- [ ] Measure numbers run sequentially across entire song
- [ ] Corcovado regression checks pass (audio, display, quiz)
- [ ] Handoff created, uploaded to GCS
- [ ] **UAT JSON delivered** (see below)

---

## VOCABULARY LOCKDOWN

Do NOT say "Fixed", "Done", "Working", "Complete", or "Implemented" unless you can show:
- Deployed Cloud Run revision URL
- Health check output with matching version
- Database query output proving each finding is resolved
- Corcovado regression evidence

Without all of the above: **"Code written. Pending deployment and testing."**

---

## UAT JSON DELIVERABLE (Required)

As part of your handoff, generate a UAT JSON file following the schema below. Upload it to GCS
and **include the readable URL in your handoff summary** so CAI can fetch it directly without
file uploads.

### File location:
```bash
# Save locally
G:\My Drive\Code\Python\harmonylab\uat\HO-XXXX_UAT.json

# Upload to GCS (use your assigned handoff ID)
gsutil cp uat/HO-XXXX_UAT.json gs://corey-handoff-bridge/harmonylab/outbox/HO-XXXX_UAT.json
```

### Provide the readable URL in your handoff summary:
```
UAT JSON: https://storage.googleapis.com/corey-handoff-bridge/harmonylab/outbox/HO-XXXX_UAT.json
```
If the bucket is not public, provide the gsutil URI and a signed URL:
```bash
gsutil signurl -d 7d <key-file> gs://corey-handoff-bridge/harmonylab/outbox/HO-XXXX_UAT.json
```

### JSON Schema:
```json
{
  "uat_version": "2.2",
  "generated_by": "cc",
  "generated_at": "ISO-8601 timestamp",
  "handoff_id": "HO-XXXX",
  "project": {
    "name": "HarmonyLab",
    "emoji": "🔵",
    "version": "new version number",
    "app_url": "https://harmonylab.rentyourcio.com",
    "health_url": "https://harmonylab-57478301787.us-central1.run.app/health",
    "deployed_revision": "revision name from deploy"
  },
  "context": {
    "summary": "Brief description of what was fixed",
    "root_cause": "One-line root cause per finding",
    "files_modified": ["list of files"],
    "commit": "commit hash",
    "risk_areas": ["regression risks identified"]
  },
  "sections": [
    {
      "id": "section-N",
      "title": "Section Title",
      "tests": [
        {
          "id": "HL02-XX",
          "title": "Short test name",
          "description": "Step-by-step instructions a human can follow",
          "expected": "Observable outcome — what the user SEES, not code-level assertions",
          "category": "fix_verification | regression | exploratory",
          "priority": "critical | high | medium"
        }
      ]
    }
  ],
  "test_data_notes": "Setup instructions, preconditions, test files needed",
  "cc_observations": "Things CC noticed that might affect testing — uncertainties, caveats, edge cases"
}
```

### Test Writing Rules:
- **ID format**: `HL02-XX` (HL = HarmonyLab, 02 = second UAT, XX = sequential)
- **8–15 tests total** — don't pad with trivial items
- **Outcome-based**: test what the user SEES, not DOM elements or internal state
- **Be specific**: "Open harmonylab.rentyourcio.com, click Corcovado" not "verify the song works"
- **Flag uncertainty**: if you don't know whether a feature exists in the UI, say so in
  `cc_observations` — don't write a test that might not apply
- **Include regression tests** for Corcovado (audio, display, quiz) and the P0 fix (Bach chords still visible)

---

## SCOPE BOUNDARIES

**DO:**
- Fix the 4 findings listed above
- Investigate root causes thoroughly before coding
- Document what you find even if you can't fully fix it
- Deliver UAT JSON with readable URL

**DO NOT:**
- Touch auth (known issue, separate task)
- Fix the branch mismatch (master vs main — separate task)
- Add the frontend to git tracking (separate task)
- Re-import or modify the Bach Prelude MIDI data unless necessary for chord naming fix
- Run `git add -A` — stage specific files only

---

## HANDOFF TEMPLATE

Your handoff must include:

```
## Summary
- Finding 1 (Key Detection): [status + root cause]
- Finding 2 (Chord Naming): [status + root cause]
- Finding 3 (Corcovado Count): [status + root cause]
- Finding 4 (Measure Numbers): [status + root cause]

## Verification
- BWV 846 detected key: [result]
- BWV 846 first 8 chords: [symbols]
- Corcovado chord count: [number, duplicates Y/N]
- Measure numbering: [sample output]
- Health check: [URL, version]
- Deployed revision: [name]

## Regression
- Corcovado audio: [pass/fail]
- Corcovado display: [pass/fail]
- Quiz: [pass/fail]
- Bach chords still visible: [pass/fail]

## UAT
- JSON: [readable URL]
- File: uat/HO-XXXX_UAT.json

## What's Next
- [Follow-up items discovered]
```

Upload handoff to: `gs://corey-handoff-bridge/harmonylab/outbox/`

---

*Task created: 2026-02-15*
*Predecessor: HO-P1Q2 (MIDI import fix, 8/10 UAT)*
*Track in MetaPM as HarmonyLab bug — analysis quality*
