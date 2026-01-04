# Database Migration Instructions

## Add midi_notes column to Chords table

**Date:** January 4, 2026  
**Version:** 1.1.0

### Migration File
Run `migrations/add_midi_notes_column.sql` on Cloud SQL

### Steps:
1. Open Cloud SQL Studio
2. Connect to HarmonyLab database
3. Execute the migration SQL:
   ```sql
   ALTER TABLE Chords ADD midi_notes NVARCHAR(500);
   ```

### Verification:
```sql
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'Chords' AND COLUMN_NAME = 'midi_notes';
```

### Note:
- Existing chords will have NULL for midi_notes
- New MIDI imports will populate this field with JSON array of MIDI note numbers
- Format: `[60, 64, 67]` (JSON array of integers)
