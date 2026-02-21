# CC Task: Generate UAT Test Plan for HarmonyLab v1.8.1 MIDI Import Fix

**Date:** 2026-02-15
**Priority:** P1
**Type:** UAT Generation — JSON output
**Project:** HarmonyLab 🔵
**Handoff Under Test:** HO-P1Q2 (MIDI import chord extraction fix)

---

## PRE-WORK

1. **Read** `Harmony Lab PROJECT_KNOWLEDGE.md` in the project root
2. **Read** the handoff for this fix:
   ```bash
   gsutil cat gs://corey-handoff-bridge/harmonylab/outbox/20260215_v181-midi-import-fix.md
   ```
3. **Read** the master UAT template for structure reference:
   ```bash
   cat "G:\My Drive\Code\Python\project-methodology\templates\uat_template_v2.1.html"
   ```
   If not found locally, try:
   ```bash
   gsutil cat gs://corey-handoff-bridge/project-methodology/templates/uat_template_v2.1.html
   ```

---

## WHAT TO PRODUCE

Generate a **JSON file** containing the complete UAT test plan for this handoff. CAI will review
the JSON, make editorial adjustments, and render the final HTML. You do NOT produce HTML.

### Output File
```
G:\My Drive\Code\Python\harmonylab\uat\HO-P1Q2_UAT.json
```

Also upload to GCS alongside the handoff:
```bash
gsutil cp uat/HO-P1Q2_UAT.json gs://corey-handoff-bridge/harmonylab/outbox/HO-P1Q2_UAT.json
```

---

## JSON SCHEMA

Follow this schema exactly. CAI and the UAT template consume this structure.

```json
{
  "uat_version": "2.2",
  "generated_by": "cc",
  "generated_at": "2026-02-15T__:__:__Z",
  "handoff_id": "HO-P1Q2",
  "project": {
    "name": "HarmonyLab",
    "emoji": "🔵",
    "version": "1.8.1",
    "app_url": "https://harmonylab.rentyourcio.com",
    "health_url": "https://harmonylab.rentyourcio.com/health",
    "deployed_revision": "harmonylab-00077-fvs"
  },
  "context": {
    "summary": "Brief description of what was fixed and why",
    "root_cause": "One-line root cause from the handoff",
    "files_modified": ["app/services/midi_parser.py", "main.py"],
    "commit": "54bbe82",
    "risk_areas": [
      "Chord extraction for non-arpeggiated songs (regression)",
      "Any other areas CC identifies as risk"
    ]
  },
  "sections": [
    {
      "id": "section-1",
      "title": "Section Title",
      "tests": [
        {
          "id": "HL01-01",
          "title": "Short test name",
          "description": "What to do step by step",
          "expected": "What the correct outcome looks like",
          "category": "fix_verification | regression | exploratory",
          "priority": "critical | high | medium",
          "requires_midi_file": true,
          "test_data": "Specific data needed, e.g., which MIDI file, which URL to visit"
        }
      ]
    }
  ],
  "test_data_notes": "Any setup instructions, test files needed, preconditions",
  "cc_observations": "Anything CC noticed during the fix that might affect testing"
}
```

---

## TEST PLAN GUIDANCE

Build test cases by analyzing three sources:

### Source 1: The Handoff (what changed)
Read the handoff and create tests that verify every claim:
- MIDI import produces chords for arpeggiated music (the fix)
- Time-window grouping algorithm works correctly
- Track selection uses "most total note events" instead of "highest simultaneous polyphony"

### Source 2: The Code Changes (what could break)
Read the modified files (`app/services/midi_parser.py`, `main.py`) and identify:
- What functions were changed?
- What parameters were added or modified?
- What edge cases exist in the new logic?
- What existing behavior might be affected?

### Source 3: Existing Working Features (regression)
The following features are CONFIRMED WORKING as of 2026-02-15. Include regression tests:
- Audio playback (Tone.js) — test that Corcovado still plays
- Quiz system — test that quiz still functions
- Roman numeral display — test that chord symbols render correctly
- Corcovado song — 45 chords, must be unchanged

### Section Structure (suggested — adjust based on what you find in the code)

**Section 1: MIDI Import Fix Verification**
- Import a MIDI file through the UI (if UI import exists) or API
- Verify chords appear for imported song
- Verify chord symbols are musically reasonable
- Verify chord count is non-zero

**Section 2: Regression — Existing Song Data**
- Corcovado still has 45 chords
- Corcovado audio playback still works
- Corcovado chord display renders correctly
- Quiz functionality still works with Corcovado

**Section 3: UI & Health**
- Health endpoint returns v1.8.1
- Song list shows both Corcovado and Bach Prelude
- Navigation between features works

### What NOT to test
- Auth (not enforced, not part of this fix)
- Frontend git tracking (known issue, separate task)
- Branch mismatch (known issue, separate task)

---

## IMPORTANT RULES

1. **Be specific in `description` fields** — write steps a human can follow without guessing
2. **Be specific in `expected` fields** — state observable outcomes, not vague "works correctly"
3. **Include `test_data`** — if a test needs a specific URL, file, or input, say exactly what
4. **Use outcome-based criteria** — test what the user SEES, not what the DOM contains
5. **ID format**: `HL01-XX` (HL = HarmonyLab, 01 = first UAT for this handoff, XX = sequential)
6. **Keep it practical** — target 8-15 tests total. Don't pad with trivial items.
7. **Flag uncertainty** — if you're unsure whether a feature exists or how it works, say so in
   `cc_observations` rather than writing a test that might not apply

---

## DEFINITION OF DONE

- [ ] Handoff read and understood
- [ ] Code changes in `midi_parser.py` and `main.py` reviewed
- [ ] JSON file generated at `uat/HO-P1Q2_UAT.json`
- [ ] JSON uploaded to `gs://corey-handoff-bridge/harmonylab/outbox/HO-P1Q2_UAT.json`
- [ ] JSON validates against the schema above (all required fields present)
- [ ] Committed: `docs: generate UAT test plan for HO-P1Q2 MIDI import fix`
- [ ] Pushed

Report: "UAT JSON delivered to GCS. Ready for CAI review."

---

*Task created: 2026-02-15*
*This is a pilot of the CC→JSON→CAI→HTML UAT workflow.*
