# Version 1.1.0 Release Notes

**Release Date:** January 4, 2026  
**Status:** Deployed to Cloud Run

---

## 🎉 New Features

### 1. Version Display
- **Version v1.1.0** now displayed in footer
- Helps ensure everyone is testing the same version
- Updated in `package.json` and Layout component

### 2. MIDI Notes Analysis
- **Shows actual MIDI notes** used in chord detection (e.g., "C4, E4, G4")
- **Displays root note** detected from MIDI data (e.g., "C4")
- **Shows intervals** calculated from root in semitones
- Stored in database as JSON array: `[60, 64, 67]`

### 3. Chord Editing
- **✏️ Edit button** on every chord in analysis view
- **Inline editing** with input field
- **Supports slash chords** (e.g., Dm7/G, BbMaj7/D)
- **Save/Cancel buttons** for editing workflow
- Updates via PUT `/api/v1/chords/{id}` endpoint

### 4. Improved Analysis Display
Analysis now shows **on EVERY measure** with accurate information:

**Method:**
- "MIDI Analysis" - chord detected from MIDI file
- "Manual Override" - chord manually edited by user

**Root Note:**
- Shows actual detected note (e.g., "G3")
- Instead of generic text

**Intervals:**
- Shows actual calculated intervals (e.g., "0, 4, 7 semitones from root")
- Instead of hardcoded template descriptions

**Notes in analysis:**
- Lists all MIDI notes used (e.g., "F4, A4, C5, E5")
- Allows verification of parser accuracy

### 5. Removed Non-Valuable Info
- ❌ Removed "Template matching from MIDI note intervals" (too generic)
- ❌ Removed "Extracted from simultaneous notes in MIDI track" (static text)
- ✅ Replaced with dynamic, actual data

---

## 🔧 Technical Changes

### Database Migration
**New Column:** `Chords.midi_notes NVARCHAR(500)`
- Stores JSON array of MIDI note numbers
- Format: `[60, 64, 67, 70]`
- Migration SQL in `migrations/add_midi_notes_column.sql`

### Backend Updates
1. **imports.py** - Now stores `midi_notes` during MIDI import
   ```python
   midi_notes_json = json.dumps(chord_data.midi_notes)
   INSERT INTO Chords (..., midi_notes) VALUES (..., ?)
   ```

2. **songs.py** - Added `midi_notes` to progression query
   ```sql
   SELECT id, chord_symbol, beat_position, chord_order, midi_notes
   FROM Chords
   ```

3. **chords.py** - Already had PUT endpoint for chord updates

### Frontend Updates
1. **package.json** - Version bumped to 1.1.0
2. **Layout.jsx** - Shows "v1.1.0" in footer
3. **SongPage.jsx** - Major rewrite:
   - Added edit state management
   - Added MIDI note parsing functions:
     - `midiNoteToName()` - Converts 60 → "C4"
     - `parseIntervals()` - Shows semitones from root
     - `getRootNote()` - Extracts lowest note
     - `getMidiNotesList()` - Formats all notes
   - Added edit UI with inline form
4. **client.js** - Added `updateChord()` API method

---

## 📊 Before vs After

### Analysis Display (Before)
```
Measure 1
  BbMaj
  Beat 1
  
  Parsing Algorithm:
  • Method: Template matching from MIDI note intervals
  • Root Detection: Lowest MIDI note in chord voicing  
  • Intervals: Major triad (root, M3, P5)
  • Source: Extracted from simultaneous notes in MIDI track
```

### Analysis Display (After)
```
Measure 1
  BbMaj  Beat 1  ✏️ Edit
  
  Analysis:
  • Method: MIDI Analysis
  • Root Note: Bb3
  • Intervals: 0, 4, 7 semitones from root
  • Notes in analysis: Bb3, D4, F4
```

---

## 🐛 Bug Fixes

### Fixed: Analysis Only Showing 4 Measures
**Issue:** Analysis view was only displaying first 4 chords  
**Cause:** Grid layout with `grid-cols-4` was confusing  
**Fix:** Analysis now loops through ALL measures in every section

---

## 🔄 Migration Required

**Action:** Run database migration before testing new imports

```sql
USE HarmonyLab;
ALTER TABLE Chords ADD midi_notes NVARCHAR(500);
```

**Impact:**
- ✅ Existing chords will have `NULL` for midi_notes (shows "No MIDI data")
- ✅ New imports will populate midi_notes automatically
- ✅ Manual edits will show "Manual Override" method

---

## 📝 Usage Instructions

### Viewing Analysis
1. Navigate to any song (e.g., Corcovado)
2. Click **"🔍 Show Analysis"** button
3. See detailed breakdown for EVERY measure

### Editing Chords
1. Click **"🔍 Show Analysis"** to expand view
2. Find the chord you want to edit
3. Click **✏️ Edit** button
4. Type new chord symbol (supports slash chords: `Dm7/G`)
5. Click **✓ Save** or **✕ Cancel**
6. Chord updates immediately

### Verifying Parser Accuracy
1. Look at "Notes in analysis" field
2. Compare with sheet music or MIDI file
3. If incorrect, use **✏️ Edit** to override
4. Edited chords will show "Manual Override" method

---

## 🎯 Addressing Your Comments

### 1. ✅ Version Number
- v1.1.0 displayed in footer

### 2. ✅ Analysis on Every Measure
- Fixed - now shows ALL measures, not just 4

### 3. ✅ Review Notes Used
- Shows: "Notes in analysis: C4, E4, G4, B4"

### 4. ✅ Edit Chords with Slash Chords
- ✏️ Edit button on each chord
- Input supports any format (including Dm7/G)

### 5. ✅ Improved Analysis Comments

**Method:**
- ✅ Changed to "MIDI Analysis" or "Manual Override"
- ❌ Removed generic template matching text

**Root Detection:**
- ✅ Shows actual note from MIDI (e.g., "Bb3")
- ❌ Removed generic description

**Intervals:**
- ✅ Shows actual calculated intervals (0, 4, 7 semitones)
- ❌ Removed hardcoded templates

**Source:**
- ❌ Removed static text
- ✅ Added "Notes in analysis" with actual MIDI notes

---

## 🚀 Deployment Status

**Commit:** 59c4cbe  
**Branch:** main  
**Deployed:** Yes (3-5 minutes after push)

**URLs:**
- Frontend: https://harmonylab-frontend-wmrla7fhwa-uc.a.run.app
- Custom Domain: https://harmonylab.rentyourcio.com
- Backend: https://harmonylab-wmrla7fhwa-uc.a.run.app

---

## ⚠️ Known Limitations

1. **Existing songs** won't have MIDI notes (imported before this update)
   - Will show "No MIDI data" in analysis
   - Solution: Re-import MIDI files OR manually edit chords

2. **Parser limitations** (as noted in Corcovado example):
   - Doesn't detect slash chords automatically
   - Doesn't detect alterations (♭5, ♭9, #11)
   - May simplify complex voicings
   - **Solution:** Use ✏️ Edit to correct any misidentified chords

3. **Database migration** required:
   - Must run `ALTER TABLE` before new imports work correctly
   - See `migrations/add_midi_notes_column.sql`

---

## 📈 Next Steps

### Recommended Testing
1. ✅ Verify version shows "v1.1.0" in footer
2. ✅ Check Corcovado - analysis should show on ALL measures
3. ✅ Try editing a chord symbol
4. ⚠️ Run database migration
5. 🆕 Import a new MIDI file
6. ✅ Verify MIDI notes appear in analysis

### Future Enhancements
- [ ] Enhanced parser to detect slash chords
- [ ] Detect chord alterations (♭5, ♭9, #11)
- [ ] Bulk edit multiple chords
- [ ] Export analysis to PDF
- [ ] Compare analysis with sheet music overlay

---

**Questions or Issues?** Check the analysis view to verify parser accuracy!
