-- Add midi_notes column to Chords table for storing MIDI note analysis
-- Run this migration on Cloud SQL

USE HarmonyLab;

-- Add midi_notes column to store JSON array of MIDI note numbers
ALTER TABLE Chords
ADD midi_notes NVARCHAR(500);

PRINT 'midi_notes column added to Chords table';
