-- Add chord editing columns for manual corrections, inversions, and octave control

-- Add new columns to Chords table
ALTER TABLE Chords ADD chord_symbol_override NVARCHAR(20) NULL;
ALTER TABLE Chords ADD inversion INT DEFAULT 0;  -- 0=root, 1=1st, 2=2nd, 3=3rd
ALTER TABLE Chords ADD playback_octave INT DEFAULT 3;  -- Range: 1-5
ALTER TABLE Chords ADD is_manual_edit BIT DEFAULT 0;
ALTER TABLE Chords ADD confidence DECIMAL(3,2) NULL;  -- 0.00 to 1.00

-- Update existing records to have default values
UPDATE Chords SET inversion = 0 WHERE inversion IS NULL;
UPDATE Chords SET playback_octave = 3 WHERE playback_octave IS NULL;
UPDATE Chords SET is_manual_edit = 0 WHERE is_manual_edit IS NULL;

PRINT 'Successfully added chord editing columns';
