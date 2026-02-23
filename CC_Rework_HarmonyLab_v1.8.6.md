# CC Rework: HarmonyLab v1.8.6 — Chord Dropdowns + .mscz Parser

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
gcloud auth list
# Expected: cc-deploy@super-flashcards-475210.iam.gserviceaccount.com (active)
# If not: gcloud auth activate-service-account cc-deploy@super-flashcards-475210.iam.gserviceaccount.com --key-file=C:\venvs\cc-deploy-key.json
# DEPLOY WORKAROUND: gcloud config set account cprator@cbsware.com (for deploy only, switch back after)
```

---

## 📋 Context

**Project**: HarmonyLab
**Current Version**: v1.8.5 (error logging sprint)
**Production URLs**:
- Backend: https://harmonylab-57478301787.us-central1.run.app
- Frontend: https://harmonylab.rentyourcio.com

### What Happened
PL ran UAT v1.8.4 on 2/22/2026. Results: 10 passed, 2 failed, 4 skipped.

**Two critical failures:**

1. **CHD-01 — Chord dropdowns NOT implemented.** CC claimed done in v1.8.4 handoff (50EDE487). PL tested: the chord edit modal still has a **free text input** for chord symbol, not structured dropdowns. The v1.8.4 rework prompt explicitly required: Root dropdown (C, C#/Db, D, etc.), Quality dropdown (maj, min, dim, aug, dom7, etc.), Extension dropdown (b9, #9, #11, 13, etc.), Bass note dropdown for slash chords. None of these exist. What PL sees:

```
Edit Chord Analysis
×
Chord Symbol: [CMaj]          ← FREE TEXT, not dropdowns
Roman Numeral (auto): IMaj
Roman Numeral Override: [    ]
Function Override: [Auto]
Key Context Override: [C major]
Pivot Chord: [ ]
Notes: [                    ]
```

**What PL should see:**
```
Edit Chord Analysis
×
Root:      [C     ▼]
Quality:   [maj   ▼]
Extension: [none  ▼]
Bass Note: [none  ▼]
Preview:   Cmaj
---
Roman Numeral (auto): IMaj
Roman Numeral Override: [    ]
Function Override: [Auto]
Key Context Override: [C major]
Pivot Chord: [ ]
Notes: [                    ]
```

2. **IMP-03 — .mscz parser returns 0 chords.** The MuseScore format (.mscz) consistently shows "No chord symbols detected" for every file tested. The import reads the header correctly (key, time signature, tempo) but derives zero chords from note data. This works for .mid files — the harmonic analysis pipeline runs and produces chords. For .mscz, the note extraction step appears to fail silently. Previous analysis: the issue is likely in how the .mscz parser extracts note data — it may be reading a different internal structure than expected.

---

## 🔧 Requirements

### P0: Chord Editing — Structured Dropdowns (CHD-01 REWORK)

**This was required in v1.8.4 and was NOT delivered. It is the #1 priority.**

Replace the free-text "Chord Symbol" input in the chord edit modal with structured dropdowns:

1. **Root dropdown**: C, C#/Db, D, D#/Eb, E, F, F#/Gb, G, G#/Ab, A, A#/Bb, B
2. **Quality dropdown**: maj, min, dim, aug, dom7, maj7, min7, dim7, m7b5 (half-dim), aug7, minMaj7, 6, min6, sus2, sus4
3. **Extension dropdown** (optional): none, b9, #9, 9, #11, 11, 13, b13, add9, add11
4. **Bass note dropdown** (optional, for slash chords): none, C, C#/Db, D, D#/Eb, E, F, F#/Gb, G, G#/Ab, A, A#/Bb, B

**Behavior:**
- Dropdowns compose the chord symbol in real-time: Root + Quality + Extension + /Bass = display
- Example: Root=D, Quality=min7 → preview shows "Dm7"
- Example: Root=C, Quality=maj7, Bass=E → preview shows "Cmaj7/E"
- The composed chord symbol is what gets saved to the database
- Existing fields below (Roman Numeral, Function Override, Key Context, Pivot, Notes) remain unchanged

**When opening the edit modal for an existing chord:**
- Parse the existing chord symbol (e.g., "Cmaj7/E") back into Root=C, Quality=maj7, Extension=none, Bass=E
- Pre-populate the dropdowns with the parsed values
- Implement `parseChordSymbol(symbol)` function: greedy-match quality from longest to shortest, extract bass after "/", remainder is extensions

**Frontend location:** The chord edit modal is in the analysis view. Find it — likely in index.html or a dedicated JS file. The existing free-text input for "Chord Symbol" must be REPLACED, not supplemented.

**Acceptance Criteria:**
- [ ] Chord edit modal has 4 dropdowns (Root, Quality, Extension, Bass)
- [ ] No free-text chord symbol input remains
- [ ] Selecting Root=D, Quality=min7 shows preview "Dm7"
- [ ] Saving persists to database, survives page reload
- [ ] Slash chord: Root=C, Quality=maj7, Bass=E → "Cmaj7/E" persists
- [ ] Opening edit on existing "Cmaj" → Root=C, Quality=maj pre-populated
- [ ] All 12 root notes available
- [ ] All 14+ quality types available
- [ ] All extensions available

### P1: .mscz Parser — Investigate and Fix (IMP-03)

.mscz files import with correct metadata (key, time sig, tempo) but extract 0 notes, so harmonic analysis produces 0 chords. .mid files work correctly.

1. **Investigate the .mscz parser.** Find where note extraction happens for MuseScore files.
2. **Add diagnostic logging:** When parsing .mscz, log: total measures found, notes per measure, note extraction method used.
3. **Test with a known .mscz file.** Import a simple MuseScore file and trace where note extraction fails.
4. **Possible causes:**
   - .mscz is a ZIP containing .mscx XML — is the ZIP being extracted properly?
   - MuseScore 4 uses a different internal XML schema than MuseScore 3
   - Multi-voice or multi-staff layouts may confuse the parser
   - Notes may be stored under `<chord><note>` elements, not flat `<note>` elements
5. **Fix or document:** Either fix the parser to extract notes from .mscz, or document exactly what's unsupported and show a clear user message: "MuseScore format partially supported: metadata imported, harmonic analysis requires MIDI export. Export as .mid from MuseScore for full chord analysis."

**Acceptance Criteria:**
- [ ] Import a .mscz file → either chords are derived OR a clear message explains why not
- [ ] Diagnostic logging shows note extraction results per measure
- [ ] Root cause documented in PROJECT_KNOWLEDGE.md
- [ ] If fixed: import "Amor em Paz" .mscz → non-zero chords derived
- [ ] If not fixable: user message guides them to export as .mid instead

### P2: Version Bump → v1.8.6

Bump both backend and frontend versions to v1.8.6.

---

## ✅ Test Commands

```bash
# Backend health
curl -s https://harmonylab-57478301787.us-central1.run.app/health | python -m json.tool
# Expected: v1.8.6, component: backend

# Frontend health
curl -s https://harmonylab.rentyourcio.com/health | python -m json.tool
# Expected: v1.8.6, component: frontend

# Test chord edit — open a song in browser, click a chord, verify dropdowns appear
# This is a VISUAL test — CC cannot fully verify. At minimum:
# - Grep the frontend code for the dropdown HTML elements
# - Confirm the parseChordSymbol function exists
# - Confirm the free-text input is gone
```

---

## 📮 Handoff Instructions

```bash
curl -X POST https://metapm.rentyourcio.com/api/uat/submit \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "HarmonyLab",
    "version": "1.8.6",
    "results_text": "<include test results: dropdown grep, parseChordSymbol function, .mscz diagnostic output>",
    "total_tests": 8,
    "linked_requirements": "HL-009",
    "notes": "Rework: CHD-01 chord dropdowns (was claimed done in v1.8.4, PL proved otherwise). IMP-03 .mscz parser investigation."
  }'
```

---

## 🔒 Session Close-Out

1. Create `SESSION_CLOSEOUT.md`
2. Update `PROJECT_KNOWLEDGE.md`:
   - Chord edit modal: dropdowns (Root/Quality/Extension/Bass), not free text
   - .mscz parser status: fixed or documented limitation
   - Current version: v1.8.6
3. `git add -A && git commit -m "rework: chord editing dropdowns + .mscz parser investigation [v1.8.6]"`
4. `git push origin main`
5. Verify deploy via `/health`

---

## ⚠️ Rules
- **Deploy to Cloud Run and test against production.** Do NOT run local.
- **The chord dropdowns are NON-NEGOTIABLE.** This was required in v1.8.4, claimed done, and PL proved it wasn't. Do not claim done without verifying the modal HTML contains `<select>` elements, not `<input type="text">`.
- **Screenshot or grep evidence required.** In the handoff, include grep output showing the dropdown HTML elements exist in the deployed frontend code.
- **Do NOT touch analysis logic, quiz mode, or import pipeline** (except .mscz parser for P1).
