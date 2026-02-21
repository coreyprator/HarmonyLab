# CC Sprint: HarmonyLab — Audit + Bug Fixes

## BOOTSTRAP GATE
**STOP. Read this file first:**
`G:\My Drive\Code\Python\project-methodology\templates\CC_Bootstrap_v1.md`

Follow its instructions. Read `HarmonyLab PROJECT_KNOWLEDGE.md`. Then return here.

## AUTH CHECK — RUN FIRST
```powershell
gcloud auth list
```
**Verify the ACTIVE account is `cc-deploy@super-flashcards-475210.iam.gserviceaccount.com`.** If it's not:
```powershell
gcloud auth activate-service-account --key-file="C:\venvs\cc-deploy-key.json"
gcloud config set project super-flashcards-475210
```
**NEVER prompt the user for passwords or credentials.**
**Deploy to GCloud and test against production. No local validation. No virtual environments.**

---

## CONTEXT

HarmonyLab is a jazz chord analysis and training app. Song list → Analysis (default) → Quiz. It parses MIDI/MuseScore files, analyzes harmonic content, and quizzes users on chord identification.

Production URL: https://harmonylab-57478301787.us-central1.run.app

Several items are in_progress or backlog bug status. PL has not received UAT for the in-progress items. This sprint audits current state, fixes bugs, and completes small UX items.

---

## PHASE 1: AUDIT — What Actually Works?

Before writing ANY code, test the following against production. For each item, document: works / partially works / broken / stub code / not implemented.

### HL-014: MuseScore Direct Import (P2, in_progress)
**Description:** Import .mscz/.mscx files directly without manual MIDI conversion. music21 library likely supports this.

**Test:**
- Is there an upload UI for MuseScore files?
- If you upload a .mscz file, does it parse?
- Does it produce the same analysis output as a MIDI file would?
- Is music21 installed and accessible?

```
HL-014 MuseScore Import:
  Upload UI: [exists/missing]
  .mscz parsing: [works/broken/stub]
  music21 integration: [yes/no]
  End-to-end import: [works/broken]
```

### HL-018: Batch Import from MuseScore Library (P2, in_progress)
**Description:** Bulk ingestion workflow for hundreds of MuseScore files. Depends on HL-014.

**Test:**
- Is there a batch import UI or endpoint?
- Can you point it at a directory/list of files?
- Status tracking, error handling, deduplication?

```
HL-018 Batch Import:
  Batch UI/endpoint: [exists/missing]
  Directory import: [works/broken/stub]
  Status tracking: [exists/missing]
  Depends on HL-014: [HL-014 works: yes/no]
```

### General App Health
**Test:**
- Does the app load? Login page?
- Can you see the song list?
- Pick a song → does Analysis page render with chord data?
- Does the Quiz work?
- What version is displayed?

```
General Health:
  App loads: [yes/no]
  Login: [works/broken/not required]
  Song list: [populated/empty/broken]
  Analysis page: [works/broken]
  Quiz: [works/broken]
  Version displayed: [version or 'none']
```

---

## PHASE 2: BUG FIXES

### HL-007: Branch Fix master→main (P1)

**What:** Git default branch is still 'master'. All other portfolio projects use 'main'.

**Acceptance criteria:**
- Default branch renamed from master to main
- All references updated (CI configs, README, any deploy scripts)
- `git branch` shows main as default
- Remote tracks main

### HL-010: Default to Analysis Page (P2)

**What:** Landing page should be Analysis, not the current default. App flow: Song list → Analysis (default) → Quiz.

**Acceptance criteria:**
- After login (or app load), user lands on the Analysis page (or Song list that leads to Analysis)
- Not Quiz, not a blank page, not Settings

### HL-011: Login Page Version Mismatch (P2)

**What:** Login page shows wrong version number.

**Acceptance criteria:**
- Login page version matches /health version
- Version pulled from config, not hardcoded

### HL-013: Verify MIDI Storage Location (P2)

**What:** Where are MIDI files stored — local filesystem or GCS? Needs to be consistent with Cloud Run deployment.

**Acceptance criteria:**
- Document where MIDI files are currently stored
- If local filesystem: this won't persist across Cloud Run deployments — flag this as a problem and recommend GCS migration
- If GCS: verify the bucket name and access pattern
- Report findings in handoff

---

## PHASE 3: DO NOT TOUCH

These are future features. Do NOT implement:
- HL-008 (import jazz standards — depends on HL-014/018)
- HL-009 (edit chord dropdowns)
- HL-012 (chord granularity)
- HL-015 (annotated MuseScore export)
- HL-016 (melody analysis)
- HL-017 (rhythm analysis)

---

## DEPLOY & TEST

```bash
BASE="https://harmonylab-57478301787.us-central1.run.app"

echo "=== Health ==="
curl -s "$BASE/health" 2>/dev/null || curl -s "$BASE/" -o /dev/null -w "HTTP %{http_code}"

echo "=== Version check ==="
curl -s "$BASE/" | grep -i "version" || echo "No version in HTML"

echo "=== Git branch ==="
git branch -a
git remote show origin | grep "HEAD branch"
```

### Browser verification:
1. App loads, login works (or skips if no auth)
2. Song list shows songs
3. Click a song → Analysis renders with chords
4. Version on login matches /health
5. If MuseScore import exists: upload a test .mscz file

---

## HANDOFF

POST to MetaPM: `https://metapm.rentyourcio.com/api/uat/submit`

```json
{
  "project": "HarmonyLab",
  "version": "[new version]",
  "feature": "HL Audit + Bug Fixes (HL-007, HL-010, HL-011, HL-013, HL-014, HL-018)",
  "linked_requirements": ["HL-007", "HL-010", "HL-011", "HL-013", "HL-014", "HL-018"]
}
```

Include full audit results in handoff.

---

## SESSION CLOSE-OUT

Per Bootstrap v1.1:
1. SESSION_CLOSEOUT committed
2. PROJECT_KNOWLEDGE.md updated with audit findings and version
3. POST handoff with URL
4. Git push all changes
