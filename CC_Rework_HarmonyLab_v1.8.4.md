# CC Rework Sprint: HarmonyLab — UAT Failures (IMP-01, CHD-02) + Error Logging

## 🚨 BOOTSTRAP GATE
**Read Bootstrap v1.1 FIRST** — located at:
`G:\My Drive\Code\Python\project-methodology\templates\CC_Bootstrap_v1.md`

Complete ALL pre-work gates before writing any code:
1. Read `PROJECT_KNOWLEDGE.md`
2. Read `CLAUDE.md`
3. Activate service account
4. State project identity
5. `git pull origin main`
6. Read previous `SESSION_CLOSEOUT.md`

---

## 🔐 Auth Check

```powershell
# Verify service account is active
gcloud auth list
# Expected: cc-deploy@super-flashcards-475210.iam.gserviceaccount.com (active)

# If not active:
gcloud auth activate-service-account cc-deploy@super-flashcards-475210.iam.gserviceaccount.com --key-file=C:\venvs\cc-deploy-key.json

# DEPLOY WORKAROUND: cc-deploy SA cannot deploy. Switch for deploy only:
# gcloud config set account cprator@cbsware.com
# (switch back after deploy)
```

---

## 📋 Context

**Project**: HarmonyLab (separate BE + FE repos, separate Cloud Run services)
**Current Version**: v1.8.3
**BE Revision**: harmonylab-00084-4mz
**FE Revision**: harmonylab-frontend-00058-wp7
**Production URLs**: (check PROJECT_KNOWLEDGE.md)

### What Happened
Sprint HL-008/HL-009/HL-014/HL-018 delivered v1.8.3 with MuseScore import, jazz standards seeding, batch import, and chord editing. 12 of 15 UAT tests passed. Two failures and one skipped test need rework.

### UAT Handoff Reference
- Handoff ID: `6BD41E97-CCA3-48EE-B065-4FCB1010544D`
- URL: https://metapm.rentyourcio.com/mcp/handoffs/6BD41E97-CCA3-48EE-B065-4FCB1010544D/content

### What Failed

**[IMP-01] FAIL — MIDI import crashes the app (session logout)**
PL imported a .mid file. The app showed "No chord symbols detected. The song will be imported with empty measures." Then the app **logged out** — indicating an unhandled exception that killed the session. This is likely an uncaught error in the import pipeline that crashes the backend request, which the frontend interprets as an auth failure and redirects to login.

**[CHD-02] FAIL — Chord editing has free-text input, not standardized dropdowns**
The chord edit modal opens (CHD-01 passed), but editing requires typing chord names freehand. HL-009 requirements specify standardized chord selection: dropdown menus for root note, chord quality (maj, min, dim, aug, dom7, maj7, min7, etc.), and optional extensions/alterations. Jazz chord vocabulary must be structured, not free-text.

**[IMP-02] SKIPPED — MIDI import blocked by IMP-01 crash**
Could not verify whether .mid files produce chord data because the import crashes the app.

### PL Observations (address these too)
- **SM-01 note**: PL asked "How do I know BE vs FE version? Shouldn't that be machine tested?" — The `/health` endpoint should clearly distinguish backend and frontend versions.
- **IMP-01 note**: PL asked for troubleshooting capabilities — error logging visible to the user or admin, not just Cloud Run logs.

---

## 🔧 Requirements (Priority Order)

### P0: Fix MIDI Import Crash [IMP-01]
- **Root cause**: Find why .mid file import causes session logout. Check the import endpoint for unhandled exceptions. Likely the MIDI parser throws when no chord symbols are found, and the error propagates up without a try/catch.
- **Fix**: Wrap the import pipeline in proper error handling. When a .mid file has no chord symbols, the import should still succeed — create the song with empty measures and return a clear message: "Imported successfully. No chord symbols found in MIDI data — add chords manually on the analysis page."
- **No crash, no logout**: The app must remain stable regardless of input file content.
- **Acceptance criteria**:
  - Import a .mid file with no chord data → song created with empty measures, user stays logged in, clear message displayed
  - Import a .mid file with chord data (if available) → song created with chords populated
  - Import a corrupt/invalid .mid file → clear error message, app stays stable

### P1: Chord Editing Dropdowns [CHD-02]
- **Current state**: Edit modal has free-text input for chord name
- **Required state**: Structured chord selection with dropdown menus:
  - **Root note**: C, C#/Db, D, D#/Eb, E, F, F#/Gb, G, G#/Ab, A, A#/Bb, B
  - **Quality**: maj, min, dim, aug, dom7, maj7, min7, dim7, m7b5 (half-dim), aug7, minMaj7, 6, min6, sus2, sus4
  - **Extensions** (optional): 9, b9, #9, 11, #11, 13, b13, add9, add11
  - **Bass note** (optional, for slash chords): same root note dropdown
- **Display**: Compose the chord symbol from selections (e.g., Root=C, Quality=maj7, Extension=#11 → "Cmaj7#11")
- **Persist**: Edited chord saves to DB and survives page reload
- **Acceptance criteria**:
  - Click a chord → modal shows dropdowns, not free-text
  - Select root=D, quality=min7 → displays "Dm7"
  - Save → reload page → chord still shows "Dm7"
  - Slash chord: root=C, quality=maj7, bass=E → displays "Cmaj7/E"

### P2: Fix Harmonic Analysis Bug — "Almost Like Being in Love" Returns 0 Chords [IMP-03 Observation]
- **Problem**: "Almost Like Being in Love" (.mscz) imports successfully but returns 0 chords. This is NOT a missing-chord-symbols issue — HarmonyLab performs harmonic analysis from note data. BWV846 (Bach Prelude in C) has no chord symbols but correctly derived harmony from arpeggiated notes. Corcovado MIDI with chord symbols suppressed also correctly calculated chords per measure. The analysis pipeline is failing silently for this specific file.
- **Investigate**: Why does the note extraction or harmonic analysis fail for this file? Possible causes: multi-voice layout, linked staves, different MuseScore version structure, transposing instruments, or edge cases in the note parser that return zero notes for certain file structures.
- **Add analysis logging**: When a file is imported, log (and return in the API response) the note extraction results per measure — how many notes were found, what they are, and whether harmonic analysis was attempted. This is the diagnostic visibility PL needs to evaluate whether failures are parser bugs or genuinely empty measures.
- **Acceptance criteria**:
  - Import "Almost Like Being in Love" (.mscz) → chords derived from note data (non-zero), OR clear diagnostic showing exactly which measures had zero notes extracted and why
  - Import BWV846 → still works correctly (regression check)
  - Import API response includes note extraction summary: `{"measures_parsed": N, "measures_with_notes": M, "chords_derived": K}`
  - If the root cause is a file structure the parser doesn't handle, document what's unsupported in PK.md and add a user-facing message identifying the issue
- **DEFERRED (Requirement B)**: If this diagnostic logging does not provide sufficient visibility into the analysis pipeline, PL may escalate in a follow-up sprint: store raw note data per measure in DB, display notes in chord edit modal (pitch, duration, beat position). This is the foundation for a future MuseScore score output requirement. Do NOT implement B in this sprint — just ensure analysis logging is detailed enough to evaluate whether B is needed.

### P3: Error Logging / Troubleshooting [PL Request]
- Add a visible error indicator in the UI when backend calls fail. At minimum:
  - Toast/notification showing the error message (not a silent fail or logout)
  - Console logging with structured error details (endpoint, status code, response body)
- If feasible: Add an `/admin/logs` or `/api/errors/recent` endpoint that returns the last N errors for troubleshooting without needing Cloud Run console access

### P4: Health Endpoint — Distinguish BE vs FE [SM-01 Note]
- Backend `/health` should return: `{"status":"healthy","version":"1.8.4","component":"backend"}`
- Frontend should display both BE and FE versions somewhere accessible (footer, health page, or about page)
- This enables machine testing: curl BE health, curl FE health, compare versions

### P5: Version Bump
- Bump to v1.8.4 in both backend and frontend
- Ensure both `/health` endpoints reflect the new version

---

## ✅ Test Commands (CC Self-Verification)

Run these after fix, before deploy. **Report pass/fail per test in the handoff.**

```bash
# 1. Backend health
curl -s https://<HL_BACKEND_URL>/health | python -m json.tool
# Expected: version 1.8.4, status healthy

# 2. Frontend health
curl -s https://<HL_FRONTEND_URL>/health
# Expected: version 1.8.4

# 3. MIDI import — no crash (requires auth token, do what you can)
# At minimum: verify the import endpoint doesn't return 500 for a .mid file
# If you can construct a test: POST a .mid file to the import endpoint
# Expected: 200 with song data (empty chords OK), NOT 500

# 4. Chord editing endpoint
# Verify PUT/PATCH chord endpoint accepts structured chord data
# Expected: 200, chord persisted

# 5. Error handling — bad file import
# POST an invalid file to import endpoint
# Expected: 400 with clear error message, NOT 500

# 6. Analysis logging — import response includes note extraction summary
# POST "Almost Like Being in Love" .mscz to import endpoint
# Expected: response includes measures_parsed, measures_with_notes, chords_derived
# If chords_derived > 0: bug fixed. If 0: diagnostic must explain why.

# 7. Regression — BWV846 still analyzes correctly
# Verify Bach Prelude in C still derives correct harmonies after any parser changes

# 8. Verify all 15 original UAT tests where possible:
# [SM-01] health returns version ✓
# [SM-02] app loads (browser) — note if you can verify
# [STD-01] jazz standards in DB — query DB or API
# [STD-02] Autumn Leaves has chord data — query API
# [STD-03] quiz endpoint responds — curl
# [IMP-01] MIDI import no crash — POST test file
# [IMP-02] MIDI import produces song — verify response
# [IMP-03] .musicxml import works — POST test file
# [IMP-04] bad file rejected — POST .pdf
# [BAT-01] batch import endpoint exists — curl
# [BAT-02] duplicate handling — POST same file twice
# [CHD-01] chord edit modal — browser/API test
# [CHD-02] chord edit persists — PUT chord, GET verify
# [REG-01] existing songs accessible — query API
# [REG-02] analysis default view — browser test
```

Replace `<HL_BACKEND_URL>` and `<HL_FRONTEND_URL>` with production URLs from PROJECT_KNOWLEDGE.md.

---

## 📮 Handoff Instructions

After fixing and deploying, POST handoff to MetaPM:

```bash
curl -X POST https://metapm.rentyourcio.com/api/uat/submit \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "HarmonyLab",
    "version": "1.8.4",
    "feature_description": "Rework: MIDI import crash fix, chord editing dropdowns, error logging, health versioning",
    "linked_requirements": "HL-009, HL-014",
    "test_results_summary": "X passed, Y failed out of 15",
    "test_results_detail": "<per-test pass/fail with notes>",
    "commit_hash": "<commit>",
    "revision": "<cloud-run-revision>",
    "notes": "Rework of v1.8.3 UAT failures. IMP-01: <root cause>. CHD-02: <what changed>."
  }'
```

Record the returned `handoff_id` and URL.

---

## 🔒 Session Close-Out

Before ending the session:
1. Commit `SESSION_CLOSEOUT.md` to both BE and FE repos
2. Update `PROJECT_KNOWLEDGE.md` with:
   - What was fixed (MIDI crash, chord dropdowns)
   - New endpoints/features (error logging, health versioning)
   - Current version (1.8.4)
   - Any new known issues
3. `git push` all changes (both repos)
4. Verify both deploys via `/health`

---

## ⚠️ Rules
- **Deploy to Cloud Run and test against production.** Do NOT run local validation or create virtual environments.
- **Both repos must be deployed** — backend AND frontend. Version must match in both.
- **Report honestly** — if a test fails, say so. PL will create another rework prompt if needed.
- **Do NOT add the playback feature** (PL noted "play chords at tempo" as a future requirement — log it in PK.md as a backlog item, do not implement).
