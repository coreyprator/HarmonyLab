-- =============================================
-- HARMONYLAB DATABASE SCHEMA v1.0
-- Sprint 1 - Foundation
-- Run this after creating the HarmonyLab database
-- =============================================

USE HarmonyLab;
GO

-- =============================================
-- CORE TABLES
-- =============================================

-- Songs: Core metadata
CREATE TABLE Songs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    title NVARCHAR(200) NOT NULL,
    composer NVARCHAR(200),
    arranger NVARCHAR(200),
    original_key VARCHAR(10),
    tempo_marking VARCHAR(50),
    genre VARCHAR(50),
    time_signature VARCHAR(10) DEFAULT '4/4',
    year_composed INT,
    notes NVARCHAR(MAX),
    source_file_name NVARCHAR(255),      -- Original import filename
    source_file_type VARCHAR(20),         -- 'midi', 'musicxml', 'musescore'
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);
GO

-- Sections: Song structure (Intro, A, B, Bridge, Coda)
CREATE TABLE Sections (
    id INT IDENTITY(1,1) PRIMARY KEY,
    song_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    section_order INT NOT NULL,
    repeat_count INT DEFAULT 1,
    notes NVARCHAR(500),
    CONSTRAINT FK_Sections_Songs FOREIGN KEY (song_id) 
        REFERENCES Songs(id) ON DELETE CASCADE,
    CONSTRAINT UQ_Section_Order UNIQUE (song_id, section_order)
);
GO

-- Measures: Container for chords within sections
CREATE TABLE Measures (
    id INT IDENTITY(1,1) PRIMARY KEY,
    section_id INT NOT NULL,
    measure_number INT NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT FK_Measures_Sections FOREIGN KEY (section_id) 
        REFERENCES Sections(id) ON DELETE CASCADE,
    CONSTRAINT UQ_Measure_Number UNIQUE (section_id, measure_number)
);
GO

-- Chords: The core learning content
CREATE TABLE Chords (
    id INT IDENTITY(1,1) PRIMARY KEY,
    measure_id INT NOT NULL,
    beat_position DECIMAL(3,2) DEFAULT 1.0,   -- 1.0, 2.0, 3.0, 4.0 or 1.5 for offbeats
    chord_symbol VARCHAR(20) NOT NULL,         -- 'Am7', 'Abdim7', 'CMaj9'
    roman_numeral VARCHAR(20),                 -- 'i7', 'bVIIdim7', 'Imaj7'
    key_center VARCHAR(20),                    -- 'A minor', 'F Major'
    function_label VARCHAR(50),                -- 'tonic', 'dominant', 'pre-dominant'
    comments NVARCHAR(500),
    chord_order INT NOT NULL,                  -- Ordering within measure
    CONSTRAINT FK_Chords_Measures FOREIGN KEY (measure_id) 
        REFERENCES Measures(id) ON DELETE CASCADE,
    CONSTRAINT UQ_Chord_Order UNIQUE (measure_id, chord_order)
);
GO

-- =============================================
-- VOCABULARY TABLES (for dropdowns)
-- =============================================

-- ChordVocabulary: Standardized notation lookup
CREATE TABLE ChordVocabulary (
    id INT IDENTITY(1,1) PRIMARY KEY,
    canonical_symbol VARCHAR(20) NOT NULL UNIQUE,
    display_name VARCHAR(30),
    chord_type VARCHAR(30),                    -- 'major7', 'minor7', 'dominant7'
    intervals VARCHAR(50),                     -- '1 3 5 7' or '1 b3 5 b7'
    aliases NVARCHAR(200)                      -- JSON array: ["CM7", "CΔ7", "Cmaj7"]
);
GO

-- RomanNumeralVocabulary: Standardized Roman numeral lookup
CREATE TABLE RomanNumeralVocabulary (
    id INT IDENTITY(1,1) PRIMARY KEY,
    canonical_symbol VARCHAR(20) NOT NULL UNIQUE,
    scale_degree INT,
    quality VARCHAR(30),
    function_type VARCHAR(30)                  -- 'tonic', 'dominant', 'subdominant'
);
GO

-- =============================================
-- MELODY & PLAYBACK
-- =============================================

-- MelodyNotes: For Tone.js playback and timing reference
CREATE TABLE MelodyNotes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    song_id INT NOT NULL,
    measure_number INT,
    beat_position DECIMAL(5,3),                -- Precise timing for syncopation
    midi_note INT,                             -- MIDI note number (60 = middle C)
    duration DECIMAL(5,3),                     -- In beats
    velocity INT,                              -- Dynamics (0-127)
    CONSTRAINT FK_MelodyNotes_Songs FOREIGN KEY (song_id) 
        REFERENCES Songs(id) ON DELETE CASCADE
);
GO

-- =============================================
-- USER PROGRESS & QUIZ TRACKING
-- =============================================

-- UserSongProgress: Track learning progress per song
CREATE TABLE UserSongProgress (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,                      -- Will link to auth system
    song_id INT NOT NULL,
    last_practiced DATETIME2,
    times_practiced INT DEFAULT 0,
    accuracy_rate DECIMAL(5,2),                -- Percentage (0.00 - 100.00)
    mastery_level INT DEFAULT 0,               -- 0-5 scale
    notes NVARCHAR(500),
    CONSTRAINT FK_UserProgress_Songs FOREIGN KEY (song_id) 
        REFERENCES Songs(id) ON DELETE CASCADE,
    CONSTRAINT UQ_User_Song UNIQUE (user_id, song_id)
);
GO

-- QuizAttempts: Detailed quiz history
CREATE TABLE QuizAttempts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    song_id INT NOT NULL,
    quiz_type VARCHAR(30),                     -- 'sequential', 'fill_blank', 'full_progression'
    section_id INT NULL,                       -- NULL if whole song quiz
    started_at DATETIME2 DEFAULT GETDATE(),
    completed_at DATETIME2,
    total_questions INT,
    correct_answers INT,
    details NVARCHAR(MAX),                     -- JSON with question-by-question results
    CONSTRAINT FK_QuizAttempts_Songs FOREIGN KEY (song_id) 
        REFERENCES Songs(id),
    CONSTRAINT FK_QuizAttempts_Sections FOREIGN KEY (section_id) 
        REFERENCES Sections(id)
);
GO

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

CREATE INDEX IX_Sections_SongId ON Sections(song_id);
CREATE INDEX IX_Measures_SectionId ON Measures(section_id);
CREATE INDEX IX_Chords_MeasureId ON Chords(measure_id);
CREATE INDEX IX_Chords_Symbol ON Chords(chord_symbol);
CREATE INDEX IX_MelodyNotes_SongId ON MelodyNotes(song_id);
CREATE INDEX IX_MelodyNotes_Measure ON MelodyNotes(song_id, measure_number);
CREATE INDEX IX_UserProgress_UserId ON UserSongProgress(user_id);
CREATE INDEX IX_UserProgress_LastPracticed ON UserSongProgress(last_practiced DESC);
CREATE INDEX IX_QuizAttempts_UserId ON QuizAttempts(user_id);
CREATE INDEX IX_QuizAttempts_SongId ON QuizAttempts(song_id);
CREATE INDEX IX_QuizAttempts_StartedAt ON QuizAttempts(started_at DESC);
GO

-- =============================================
-- SEED DATA: Chord Vocabulary
-- =============================================

INSERT INTO ChordVocabulary (canonical_symbol, display_name, chord_type, intervals, aliases) VALUES
-- Triads
('Maj', 'Major', 'major', '1 3 5', '["M", ""]'),
('m', 'Minor', 'minor', '1 b3 5', '["min", "-"]'),
('dim', 'Diminished', 'diminished', '1 b3 b5', '["°"]'),
('aug', 'Augmented', 'augmented', '1 3 #5', '["+"]'),
-- Seventh chords
('Maj7', 'Major 7', 'major7', '1 3 5 7', '["M7", "Δ7", "maj7"]'),
('m7', 'Minor 7', 'minor7', '1 b3 5 b7', '["min7", "-7", "mi7"]'),
('7', 'Dominant 7', 'dominant7', '1 3 5 b7', '["dom7"]'),
('ø7', 'Half-diminished 7', 'half_diminished', '1 b3 b5 b7', '["m7b5", "-7b5", "ø"]'),
('dim7', 'Diminished 7', 'diminished7', '1 b3 b5 bb7', '["°7", "º7"]'),
('mMaj7', 'Minor-Major 7', 'minor_major7', '1 b3 5 7', '["m(Maj7)", "-(Δ7)"]'),
-- Sixth chords
('6', 'Major 6', 'major6', '1 3 5 6', '["M6", "add6"]'),
('m6', 'Minor 6', 'minor6', '1 b3 5 6', '["min6", "-6"]'),
-- Extended chords
('9', 'Dominant 9', 'dominant9', '1 3 5 b7 9', '["dom9"]'),
('Maj9', 'Major 9', 'major9', '1 3 5 7 9', '["M9", "Δ9"]'),
('m9', 'Minor 9', 'minor9', '1 b3 5 b7 9', '["min9", "-9"]'),
('11', 'Dominant 11', 'dominant11', '1 3 5 b7 9 11', '["dom11"]'),
('m11', 'Minor 11', 'minor11', '1 b3 5 b7 9 11', '["min11", "-11"]'),
('13', 'Dominant 13', 'dominant13', '1 3 5 b7 9 13', '["dom13"]'),
('Maj13', 'Major 13', 'major13', '1 3 5 7 9 13', '["M13", "Δ13"]'),
('m13', 'Minor 13', 'minor13', '1 b3 5 b7 9 13', '["min13", "-13"]'),
-- Add chords
('add9', 'Add 9', 'add9', '1 3 5 9', '["(add9)", "add2"]'),
('add11', 'Add 11', 'add11', '1 3 5 11', '["(add11)", "add4"]'),
-- Suspended chords
('sus2', 'Suspended 2', 'suspended2', '1 2 5', '[]'),
('sus4', 'Suspended 4', 'suspended4', '1 4 5', '["sus"]'),
('7sus4', 'Dominant 7 sus4', 'dominant7sus4', '1 4 5 b7', '["7sus"]'),
-- Altered chords
('7alt', 'Altered', 'altered', '1 3 #5 b7 b9 #9', '["7#9", "7b9#5"]'),
('7#9', 'Dominant 7 #9', 'dominant7sharp9', '1 3 5 b7 #9', '["7(#9)"]'),
('7b9', 'Dominant 7 b9', 'dominant7flat9', '1 3 5 b7 b9', '["7(b9)"]'),
('7#11', 'Dominant 7 #11', 'dominant7sharp11', '1 3 5 b7 #11', '["7(#11)"]'),
('7b13', 'Dominant 7 b13', 'dominant7flat13', '1 3 5 b7 b13', '["7(b13)"]');
GO

-- =============================================
-- SEED DATA: Roman Numeral Vocabulary
-- =============================================

INSERT INTO RomanNumeralVocabulary (canonical_symbol, scale_degree, quality, function_type) VALUES
-- Major key diatonic
('I', 1, 'major', 'tonic'),
('Imaj7', 1, 'major7', 'tonic'),
('I6', 1, 'major6', 'tonic'),
('ii', 2, 'minor', 'pre_dominant'),
('ii7', 2, 'minor7', 'pre_dominant'),
('iii', 3, 'minor', 'tonic'),
('iii7', 3, 'minor7', 'tonic'),
('IV', 4, 'major', 'subdominant'),
('IVmaj7', 4, 'major7', 'subdominant'),
('V', 5, 'major', 'dominant'),
('V7', 5, 'dominant7', 'dominant'),
('V9', 5, 'dominant9', 'dominant'),
('V13', 5, 'dominant13', 'dominant'),
('vi', 6, 'minor', 'tonic'),
('vi7', 6, 'minor7', 'tonic'),
('vii°', 7, 'diminished', 'dominant'),
('viiø7', 7, 'half_diminished', 'dominant'),
-- Minor key diatonic
('i', 1, 'minor', 'tonic'),
('i7', 1, 'minor7', 'tonic'),
('ii°', 2, 'diminished', 'pre_dominant'),
('iiø7', 2, 'half_diminished', 'pre_dominant'),
('III', 3, 'major', 'tonic'),
('IIImaj7', 3, 'major7', 'tonic'),
('iv', 4, 'minor', 'subdominant'),
('iv7', 4, 'minor7', 'subdominant'),
('v', 5, 'minor', 'dominant'),
('V/i', 5, 'major', 'dominant'),      -- Major V in minor key
('V7/i', 5, 'dominant7', 'dominant'),
('VI', 6, 'major', 'subdominant'),
('VImaj7', 6, 'major7', 'subdominant'),
('VII', 7, 'major', 'subtonic'),
('VII7', 7, 'dominant7', 'subtonic'),
-- Secondary dominants
('V/ii', 6, 'major', 'secondary_dominant'),
('V7/ii', 6, 'dominant7', 'secondary_dominant'),
('V/iii', 7, 'major', 'secondary_dominant'),
('V7/iii', 7, 'dominant7', 'secondary_dominant'),
('V/IV', 1, 'major', 'secondary_dominant'),
('V7/IV', 1, 'dominant7', 'secondary_dominant'),
('V/V', 2, 'major', 'secondary_dominant'),
('V7/V', 2, 'dominant7', 'secondary_dominant'),
('V/vi', 3, 'major', 'secondary_dominant'),
('V7/vi', 3, 'dominant7', 'secondary_dominant'),
-- Modal interchange / borrowed chords
('bII', 2, 'major', 'borrowed'),       -- Neapolitan
('bIImaj7', 2, 'major7', 'borrowed'),
('bIII', 3, 'major', 'borrowed'),
('bVI', 6, 'major', 'borrowed'),
('bVII', 7, 'major', 'borrowed'),
('bVII7', 7, 'dominant7', 'borrowed'),
('#iv°', 4, 'diminished', 'borrowed'), -- Common passing chord
('#ivø7', 4, 'half_diminished', 'borrowed'),
-- Tritone substitutions
('bV7', 5, 'dominant7', 'tritone_sub'),
('bII7', 2, 'dominant7', 'tritone_sub');
GO

-- =============================================
-- HELPER VIEW: Full Chord Progression
-- =============================================

CREATE VIEW vw_SongProgression AS
SELECT 
    s.id AS song_id,
    s.title,
    s.original_key,
    s.time_signature,
    sec.name AS section_name,
    sec.section_order,
    m.measure_number,
    c.beat_position,
    c.chord_symbol,
    c.roman_numeral,
    c.key_center,
    c.function_label,
    c.chord_order
FROM Songs s
JOIN Sections sec ON s.id = sec.song_id
JOIN Measures m ON sec.id = m.section_id
JOIN Chords c ON m.id = c.measure_id
GO

-- =============================================
-- HELPER STORED PROCEDURE: Get Song With Full Progression
-- =============================================

CREATE PROCEDURE sp_GetSongProgression
    @SongId INT
AS
BEGIN
    SET NOCOUNT ON;
    
    SELECT 
        section_name,
        section_order,
        measure_number,
        beat_position,
        chord_symbol,
        roman_numeral,
        key_center,
        function_label,
        chord_order
    FROM vw_SongProgression
    WHERE song_id = @SongId
    ORDER BY section_order, measure_number, chord_order;
END
GO

-- =============================================
-- VERIFICATION
-- =============================================

PRINT '=========================================='
PRINT 'HarmonyLab Schema Creation Complete!'
PRINT '=========================================='
PRINT ''
PRINT 'Tables created:'
SELECT name FROM sys.tables ORDER BY name;

PRINT ''
PRINT 'Chord vocabulary entries: ' + CAST((SELECT COUNT(*) FROM ChordVocabulary) AS VARCHAR);
PRINT 'Roman numeral entries: ' + CAST((SELECT COUNT(*) FROM RomanNumeralVocabulary) AS VARCHAR);
GO
