# Chord Editing Feature - Setup Instructions

## Database Migration Required

Before using the chord editing feature, you must run the database migration to add the new columns.

### Run Migration

```powershell
# Connect to your Cloud SQL database and run:
sqlcmd -S your-server.database.windows.net -d HarmonyLab -U your-username -P your-password -i migrations/add_chord_editing_columns.sql
```

Or manually execute the SQL:

```sql
-- Add chord editing columns
ALTER TABLE Chords ADD chord_symbol_override NVARCHAR(20) NULL;
ALTER TABLE Chords ADD inversion INT DEFAULT 0;
ALTER TABLE Chords ADD playback_octave INT DEFAULT 3;
ALTER TABLE Chords ADD is_manual_edit BIT DEFAULT 0;
ALTER TABLE Chords ADD confidence DECIMAL(3,2) NULL;

-- Update existing records
UPDATE Chords SET inversion = 0 WHERE inversion IS NULL;
UPDATE Chords SET playback_octave = 3 WHERE playback_octave IS NULL;
UPDATE Chords SET is_manual_edit = 0 WHERE is_manual_edit IS NULL;
```

## Feature Overview

### 1. Manual Chord Symbol Editing
- Click any chord to open the edit modal
- Select root note and chord quality from dropdowns
- Original symbol is preserved, override is stored separately
- Manual edits are marked with 100% confidence

### 2. Inversion Control
- Choose from: Root position, 1st, 2nd, or 3rd inversion
- Changes the bass note and voicing order
- Example: Cmaj7 in 1st inversion → E, G, B, C (E in bass)

### 3. Octave Control
- Shift chord voicing to different octave (range: 1-5)
- Default is octave 3 (middle range)
- Useful for avoiding clashes with melody

### 4. Visual Indicators
- **⚠️ Yellow border** = Low confidence (<50%), needs review
- **✎ Blue border** = Manually edited by user
- **No indicator** = High confidence auto-detection

### 5. Preview Functionality
- Click "Preview" button to hear the chord before saving
- Uses Salamander Grand Piano sampler
- Shows exact notes that will be played

## API Endpoints

### Update Chord
```
PUT /api/v1/chords/{chord_id}
Content-Type: application/json

{
  "chord_symbol_override": "Abdim7",
  "inversion": 1,
  "playback_octave": 3,
  "is_manual_edit": true,
  "confidence": 1.0
}
```

**Response**: Updated Chord object with all fields

## Usage Examples

### Fix Parser Mistake
**Problem**: Parser detected "Ab" with 20% confidence  
**Solution**: Click chord → Select "Ab" + "dim7" → Save  
**Result**: Displays "Abdim7" with blue edit indicator

### Improve Playback Voicing
**Problem**: Cmaj7 sounds too low  
**Solution**: Click chord → Change octave to 4 → Save  
**Result**: Chord plays one octave higher

### Create Better Voice Leading
**Problem**: G7 to C sounds jumpy  
**Solution**: Click G7 → Set to 2nd inversion (D in bass) → Save  
**Result**: Smoother bass line (D → C instead of G → C)

## Testing Checklist

- [ ] Click chord cell opens edit modal
- [ ] Root and quality dropdowns work
- [ ] Preview button plays correct notes
- [ ] Inversion changes bass note
- [ ] Octave changes pitch range
- [ ] Save persists changes to database
- [ ] Refresh page shows saved changes
- [ ] Low-confidence chords show ⚠️ indicator
- [ ] Manual edits show ✎ indicator
- [ ] Playback uses new settings

## Troubleshooting

**Modal doesn't open**:
- Check browser console for errors
- Ensure ChordEditModal.jsx is imported
- Verify chord object has required fields

**Changes don't save**:
- Check database migration was run
- Verify API endpoint returns 200 status
- Check network tab for API errors

**Preview doesn't play**:
- Click anywhere on page to start Tone.js audio context
- Check browser allows audio playback
- Verify Salamander samples load (check Network tab)

## Next Steps

After deployment:
1. Run database migration
2. Re-import test songs to get confidence scores
3. Test editing low-confidence chords
4. Verify playback uses new inversions/octaves
