# CC Sprint: HarmonyLab — MuseScore Import + Jazz Standards Pipeline

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

**DEPLOY NOTE:** If `cc-deploy` cannot deploy to Cloud Run, switch to `cprator@cbsware.com` for the deploy step ONLY:
```powershell
gcloud config set account cprator@cbsware.com
gcloud run deploy harmonylab --source . --region=us-central1
gcloud config set account cc-deploy@super-flashcards-475210.iam.gserviceaccount.com
```

**Deploy to GCloud and test against production. No local validation. No virtual environments.**

---

## CONTEXT

HarmonyLab is a jazz chord analysis and training app. The previous audit sprint confirmed:
- ✅ App healthy — login, song list, analysis page, quiz all working
- ✅ HL-007 branch fix (master→main) done
- ✅ HL-010 default to Analysis page done
- ✅ HL-011 version display fixed
- ✅ HL-013 MIDI storage confirmed safe (temp-only, chord data in Cloud SQL)
- ❌ HL-014 MuseScore import: NOT IMPLEMENTED — no upload UI, no .mscz parsing, MusicXML returns 501
- ❌ HL-018 Batch import: NOT IMPLEMENTED — blocked on HL-014

**This sprint builds the MuseScore import pipeline end-to-end**, then uses it to batch-import jazz standards. This is the critical path: HL-014 → HL-018 → HL-008.

App flow: Song list → Analysis (default) → Quiz
Production URL: https://harmonylab-57478301787.us-central1.run.app

---

## REQUIREMENTS — IN DEPENDENCY ORDER

### HL-014: MuseScore Direct Import (P1)

**What:** Import .mscz and .mscx files directly. Currently the app only handles MIDI. MusicXML endpoint exists but returns 501.

**Acceptance criteria:**
- Upload UI on the Song List page: drag-and-drop zone or file picker that accepts .mscz, .mscx, .musicxml, and .mid files
- Backend parsing:
  - .mscz files: unzip (they're ZIP archives), extract the .mscx XML inside
  - .mscx files: parse directly (XML format)
  - .musicxml files: parse directly
  - .mid files: existing MIDI parsing continues to work (regression guard)
- Use `music21` library for parsing — it handles all these formats natively:
  ```python
  from music21 import converter
  score = converter.parse(uploaded_file)  # handles .mscz, .mscx, .musicxml, .mid
  ```
- After parsing: extract chord symbols, key signature, time signature, tempo
- Store in Cloud SQL: song name, key, time signature, chord progression (same schema as MIDI imports)
- After successful import: song appears in the Song List, user can click to see Analysis
- Error handling: if file is corrupt or unsupported format, show clear error message
- File NOT stored permanently — parse, extract data, discard file (same pattern as existing MIDI flow per HL-013 audit)

**Key constraint:** music21 must be in requirements.txt. It's a large library (~30MB) but it's the standard for music notation parsing. If it's already installed, verify the version supports .mscz.

### HL-018: Batch Import from MuseScore Library (P1)

**What:** Bulk ingestion workflow for importing many songs at once. Depends on HL-014's parsing engine.

**Acceptance criteria:**
- Batch import endpoint: `POST /api/songs/batch-import`
- Accepts: ZIP file containing multiple .mscz/.mscx/.musicxml/.mid files
- Or: multi-file upload (multiple files selected at once)
- Processing:
  - Parse each file using the HL-014 engine
  - Track progress: "Importing 3 of 47..."
  - Skip duplicates (match on song name + key signature)
  - Log errors per file without stopping the batch
- Results summary:
  - "Imported: 42, Skipped (duplicate): 3, Failed: 2"
  - List of failures with file names and error messages
- UI: batch import button on Song List page (separate from single-file upload)
- Rate limiting: process files sequentially, not in parallel (avoid memory spikes on Cloud Run)

### HL-008: Import Jazz Standards (P2)

**What:** Use the batch import pipeline to populate the app with jazz standards.

**Acceptance criteria:**
- Create a curated seed list of common jazz standards that are freely available:
  - Search for public domain / Creative Commons MuseScore files
  - Focus on the Real Book standards: Autumn Leaves, All The Things You Are, Blue Bossa, Fly Me To The Moon, Take The A Train, etc.
  - At minimum: 10-20 standards to start
- Import via the batch import endpoint
- Each imported standard should be playable in Analysis and Quiz modes
- If MuseScore files aren't freely available for specific tunes, create them programmatically:
  - Use music21 to create Score objects from known chord progressions
  - Common jazz standards have well-known chord changes
  - Generate .mscz or .musicxml files from the chord data
  - Import those generated files through the pipeline

**Fallback:** If copyright concerns block real MuseScore files, generate synthetic jazz progressions (ii-V-I patterns in all keys, rhythm changes, blues in various keys) as practice material. Label them clearly as "Practice Progressions" not as named standards.

### HL-009: Chord Dropdown Editing (P2)

**What:** Allow users to manually edit/correct chord analysis in the Analysis view.

**Acceptance criteria:**
- Each chord in the Analysis view is clickable
- Clicking opens a dropdown with:
  - Common chord types: Maj7, min7, dom7, dim7, half-dim, aug, sus4, sus2
  - Root note selector: C through B (all 12)
  - Optional: bass note for slash chords
- Selecting a new chord updates the analysis in real-time
- Changes persist to the database
- "Reset to original" button to revert manual edits
- This is critical for fixing AI/algorithm mistakes in chord detection

---

## PRIORITY ORDER

If you run out of time:
1. **HL-014** (single file import) — the foundation
2. **HL-018** (batch import) — scales it up
3. **HL-008** (jazz standards) — content
4. **HL-009** (chord editing) — UX polish

Items 1-2 give PL a working import pipeline. Item 3 fills the app with content. Item 4 lets users fix mistakes.

---

## ARCHITECTURE NOTES

### music21 Integration
```python
from music21 import converter, harmony, key, meter

def parse_music_file(file_bytes, filename):
    """Parse any supported music file format."""
    score = converter.parse(file_bytes)
    
    # Extract metadata
    song_key = score.analyze('key')
    time_sig = score.recurse().getElementsByClass(meter.TimeSignature)[0]
    
    # Extract chord symbols
    chords = []
    for cs in score.recurse().getElementsByClass(harmony.ChordSymbol):
        chords.append({
            'beat': cs.offset,
            'symbol': cs.figure,
            'root': cs.root().name,
            'quality': cs.quality
        })
    
    return {
        'title': score.metadata.title or filename,
        'key': str(song_key),
        'time_signature': str(time_sig),
        'chords': chords
    }
```

### File Format Handling
- `.mscz` → ZIP containing `.mscx` XML → music21 handles automatically
- `.mscx` → raw XML → music21 parses directly
- `.musicxml` → standard MusicXML → music21 native support
- `.mid` → existing parser + music21 as fallback

### Storage
No file storage needed. Parse → extract → store structured data in Cloud SQL → discard file. Same ephemeral pattern confirmed by HL-013 audit.

---

## DEPLOY & TEST

```bash
# Determine which service to test (frontend vs backend)
BASE_BE="https://harmonylab-57478301787.us-central1.run.app"

echo "=== Health ==="
curl -s "$BASE_BE/health" | python3 -m json.tool

echo "=== Single file import test ==="
# Create a minimal test MusicXML file
cat > /tmp/test_song.musicxml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
      <harmony><root><root-step>C</root-step></root><kind>major-seventh</kind></harmony>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
</score-partwise>
EOF

curl -s -X POST "$BASE_BE/api/songs/import" \
  -F "file=@/tmp/test_song.musicxml" \
  -w "\nHTTP %{http_code}\n"

echo "=== Song list check ==="
curl -s "$BASE_BE/api/songs" | python3 -c "import json,sys; songs=json.load(sys.stdin); print(f'Songs: {len(songs)}'); [print(f'  {s.get(\"title\",\"?\")}') for s in songs[:5]]"
```

### Browser verification:
1. Open Song List page
2. **Single import:** Upload a .musicxml or .mscz file → song appears in list
3. **Click imported song** → Analysis page renders with chord data
4. **Quiz** → imported song available in quiz
5. **Batch import:** Upload a ZIP with multiple files → progress shown → results summary
6. **Jazz standards** → verify seed songs appear and are analyzable
7. **Chord editing** (if implemented) → click a chord in Analysis → dropdown → change → persists

---

## HANDOFF

POST to MetaPM: `https://metapm.rentyourcio.com/api/uat/submit`

```json
{
  "project": "HarmonyLab",
  "version": "[new version]",
  "feature": "MuseScore Import Pipeline + Jazz Standards + Chord Editing",
  "linked_requirements": ["HL-014", "HL-018", "HL-008", "HL-009"]
}
```

Include:
1. Which formats parse successfully (.mscz, .mscx, .musicxml, .mid)
2. How many jazz standards were imported and from where
3. music21 version installed
4. Any parsing edge cases discovered

---

## SESSION CLOSE-OUT

Per Bootstrap v1.1:
1. SESSION_CLOSEOUT committed
2. PROJECT_KNOWLEDGE.md updated with import pipeline details, music21 version, jazz standards count
3. POST handoff with URL
4. Git push all changes
