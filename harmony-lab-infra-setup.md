# HarmonyLab - GCP Infrastructure Setup (Sprint 1)

## Overview

Setting up GCP infrastructure using proven patterns from Super-Flashcards and Etymython.

**Target Stack:**
- Cloud Run (FastAPI backend)
- Cloud SQL (MS SQL Server - reuse existing instance)
- Cloud Storage (MIDI/MXL file uploads)
- Secret Manager (connection strings, future API keys)

---

## Step 1: GCP Project Creation

```bash
# Create new project
gcloud projects create harmony-lab --name="HarmonyLab"

# Set as active project
gcloud config set project harmony-lab

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

# Link billing account (get ID from: gcloud billing accounts list)
gcloud billing projects link harmony-lab --billing-account=YOUR_BILLING_ACCOUNT_ID
```

---

## Step 2: Cloud SQL - Reuse Existing Instance

Since you have an existing MS SQL Server instance, create a new database on it rather than spinning up a new $50+/month instance.

### Option A: Add Database to Existing Instance (Recommended)

```bash
# Connect to existing instance and create database
# Replace YOUR_INSTANCE with your Cloud SQL instance name
gcloud sql connect YOUR_INSTANCE --user=sqlserver

# In SQL Server:
CREATE DATABASE HarmonyLab;
GO
USE HarmonyLab;
GO
```

### Option B: New Instance (if isolation needed)

```bash
# Only if you need separate instance - adds ~$50/month
gcloud sql instances create harmony-lab-sql \
  --database-version=SQLSERVER_2019_EXPRESS \
  --tier=db-custom-1-3840 \
  --region=us-central1 \
  --root-password=YOUR_SECURE_PASSWORD
```

---

## Step 3: Database Schema Creation

Run this after connecting to the HarmonyLab database:

```sql
-- =============================================
-- HARMONYLAB DATABASE SCHEMA v1.0
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

-- Sections: Song structure (Intro, A, B, Bridge, Coda)
CREATE TABLE Sections (
    id INT IDENTITY(1,1) PRIMARY KEY,
    song_id INT NOT NULL FOREIGN KEY REFERENCES Songs(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    section_order INT NOT NULL,
    repeat_count INT DEFAULT 1,
    notes NVARCHAR(500),
    CONSTRAINT UQ_Section_Order UNIQUE (song_id, section_order)
);

-- Measures: Container for chords within sections
CREATE TABLE Measures (
    id INT IDENTITY(1,1) PRIMARY KEY,
    section_id INT NOT NULL FOREIGN KEY REFERENCES Sections(id) ON DELETE CASCADE,
    measure_number INT NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT UQ_Measure_Number UNIQUE (section_id, measure_number)
);

-- Chords: The core learning content
CREATE TABLE Chords (
    id INT IDENTITY(1,1) PRIMARY KEY,
    measure_id INT NOT NULL FOREIGN KEY REFERENCES Measures(id) ON DELETE CASCADE,
    beat_position DECIMAL(3,2) DEFAULT 1.0,   -- 1.0, 2.0, 3.0, 4.0 or 1.5 for offbeats
    chord_symbol VARCHAR(20) NOT NULL,         -- 'Am7', 'Abdim7', 'CMaj9'
    roman_numeral VARCHAR(20),                 -- 'i7', 'bVIIdim7', 'Imaj7'
    key_center VARCHAR(20),                    -- 'A minor', 'F Major'
    function_label VARCHAR(50),                -- 'tonic', 'dominant', 'pre-dominant'
    comments NVARCHAR(500),
    chord_order INT NOT NULL,                  -- Ordering within measure
    CONSTRAINT UQ_Chord_Order UNIQUE (measure_id, chord_order)
);

-- ChordVocabulary: Standardized notation lookup (for dropdowns)
CREATE TABLE ChordVocabulary (
    id INT IDENTITY(1,1) PRIMARY KEY,
    canonical_symbol VARCHAR(20) NOT NULL UNIQUE,
    display_name VARCHAR(30),
    chord_type VARCHAR(30),                    -- 'major7', 'minor7', 'dominant7'
    intervals VARCHAR(50),                     -- '1 3 5 7' or '1 b3 5 b7'
    aliases NVARCHAR(200)                      -- JSON array: ["CM7", "CΔ7", "Cmaj7"]
);

-- RomanNumeralVocabulary: Standardized Roman numeral lookup
CREATE TABLE RomanNumeralVocabulary (
    id INT IDENTITY(1,1) PRIMARY KEY,
    canonical_symbol VARCHAR(20) NOT NULL UNIQUE,
    scale_degree INT,
    quality VARCHAR(30),
    function_type VARCHAR(30)                  -- 'tonic', 'dominant', 'subdominant'
);

-- MelodyNotes: For playback and timing reference
CREATE TABLE MelodyNotes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    song_id INT NOT NULL FOREIGN KEY REFERENCES Songs(id) ON DELETE CASCADE,
    measure_number INT,
    beat_position DECIMAL(5,3),                -- Precise timing for syncopation
    midi_note INT,                             -- MIDI note number (60 = middle C)
    duration DECIMAL(5,3),                     -- In beats
    velocity INT                               -- Dynamics
);

-- UserSongProgress: Track learning progress
CREATE TABLE UserSongProgress (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,                      -- Will link to auth system
    song_id INT NOT NULL FOREIGN KEY REFERENCES Songs(id) ON DELETE CASCADE,
    last_practiced DATETIME2,
    times_practiced INT DEFAULT 0,
    accuracy_rate DECIMAL(5,2),                -- Percentage
    mastery_level INT DEFAULT 0,               -- 0-5 scale
    notes NVARCHAR(500),
    CONSTRAINT UQ_User_Song UNIQUE (user_id, song_id)
);

-- QuizAttempts: Detailed quiz history
CREATE TABLE QuizAttempts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    song_id INT NOT NULL FOREIGN KEY REFERENCES Songs(id),
    quiz_type VARCHAR(30),                     -- 'sequential', 'fill_blank', 'full_progression'
    section_id INT FOREIGN KEY REFERENCES Sections(id),
    started_at DATETIME2 DEFAULT GETDATE(),
    completed_at DATETIME2,
    total_questions INT,
    correct_answers INT,
    details NVARCHAR(MAX)                      -- JSON with question-by-question results
);

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================
CREATE INDEX IX_Sections_SongId ON Sections(song_id);
CREATE INDEX IX_Measures_SectionId ON Measures(section_id);
CREATE INDEX IX_Chords_MeasureId ON Chords(measure_id);
CREATE INDEX IX_MelodyNotes_SongId ON MelodyNotes(song_id);
CREATE INDEX IX_UserProgress_UserId ON UserSongProgress(user_id);
CREATE INDEX IX_QuizAttempts_UserId ON QuizAttempts(user_id);
CREATE INDEX IX_QuizAttempts_SongId ON QuizAttempts(song_id);

-- =============================================
-- SEED DATA: Chord Vocabulary
-- =============================================
INSERT INTO ChordVocabulary (canonical_symbol, display_name, chord_type, intervals, aliases) VALUES
('Maj7', 'Major 7', 'major7', '1 3 5 7', '["M7", "Δ7", "maj7"]'),
('m7', 'Minor 7', 'minor7', '1 b3 5 b7', '["min7", "-7", "mi7"]'),
('7', 'Dominant 7', 'dominant7', '1 3 5 b7', '["dom7"]'),
('ø7', 'Half-diminished', 'half_diminished', '1 b3 b5 b7', '["m7b5", "-7b5"]'),
('dim7', 'Diminished 7', 'diminished', '1 b3 b5 bb7', '["°7", "º7"]'),
('m9', 'Minor 9', 'minor9', '1 b3 5 b7 9', '["min9", "-9"]'),
('Maj9', 'Major 9', 'major9', '1 3 5 7 9', '["M9", "Δ9"]'),
('9', 'Dominant 9', 'dominant9', '1 3 5 b7 9', '["dom9"]'),
('add9', 'Add 9', 'add9', '1 3 5 9', '["(add9)"]'),
('aug', 'Augmented', 'augmented', '1 3 #5', '["+", "+7"]'),
('sus4', 'Suspended 4', 'suspended', '1 4 5', '["sus"]'),
('7alt', 'Altered', 'altered', '1 3 b5/#5 b7 b9/#9', '["7#9#5"]'),
('6', 'Major 6', 'major6', '1 3 5 6', '["M6"]'),
('m6', 'Minor 6', 'minor6', '1 b3 5 6', '["min6", "-6"]'),
('13', 'Dominant 13', 'dominant13', '1 3 5 b7 9 13', '["dom13"]'),
('Maj', 'Major triad', 'major', '1 3 5', '["M", ""]'),
('m', 'Minor triad', 'minor', '1 b3 5', '["min", "-"]');

-- =============================================
-- SEED DATA: Roman Numeral Vocabulary  
-- =============================================
INSERT INTO RomanNumeralVocabulary (canonical_symbol, scale_degree, quality, function_type) VALUES
-- Major key
('I', 1, 'major', 'tonic'),
('Imaj7', 1, 'major7', 'tonic'),
('ii', 2, 'minor', 'pre_dominant'),
('ii7', 2, 'minor7', 'pre_dominant'),
('iii', 3, 'minor', 'tonic'),
('iii7', 3, 'minor7', 'tonic'),
('IV', 4, 'major', 'subdominant'),
('IVmaj7', 4, 'major7', 'subdominant'),
('V', 5, 'major', 'dominant'),
('V7', 5, 'dominant7', 'dominant'),
('vi', 6, 'minor', 'tonic'),
('vi7', 6, 'minor7', 'tonic'),
('vii°', 7, 'diminished', 'dominant'),
('viiø7', 7, 'half_diminished', 'dominant'),
-- Minor key
('i', 1, 'minor', 'tonic'),
('i7', 1, 'minor7', 'tonic'),
('ii°', 2, 'diminished', 'pre_dominant'),
('iiø7', 2, 'half_diminished', 'pre_dominant'),
('III', 3, 'major', 'tonic'),
('IIImaj7', 3, 'major7', 'tonic'),
('iv', 4, 'minor', 'subdominant'),
('iv7', 4, 'minor7', 'subdominant'),
('v', 5, 'minor', 'dominant'),
('VI', 6, 'major', 'subdominant'),
('VImaj7', 6, 'major7', 'subdominant'),
('VII', 7, 'major', 'subtonic'),
('VII7', 7, 'dominant7', 'subtonic'),
-- Secondary dominants
('V/V', 5, 'major', 'secondary_dominant'),
('V7/V', 5, 'dominant7', 'secondary_dominant'),
('V/ii', 5, 'major', 'secondary_dominant'),
('V7/ii', 5, 'dominant7', 'secondary_dominant'),
-- Borrowed chords
('bVII', 7, 'major', 'borrowed'),
('bVI', 6, 'major', 'borrowed'),
('iv', 4, 'minor', 'borrowed');

GO
PRINT 'HarmonyLab schema created successfully!';
```

---

## Step 4: Cloud Storage Bucket

```bash
# Create bucket for uploaded music files
gsutil mb -l us-central1 gs://harmony-lab-uploads

# Set lifecycle rule: delete temp files after 30 days
cat > lifecycle.json << 'EOF'
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {
        "age": 30,
        "matchesPrefix": ["temp/"]
      }
    }
  ]
}
EOF

gsutil lifecycle set lifecycle.json gs://harmony-lab-uploads

# CORS configuration for browser uploads
cat > cors.json << 'EOF'
[
  {
    "origin": ["https://harmony-lab.web.app", "http://localhost:3000"],
    "method": ["GET", "POST", "PUT"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

gsutil cors set cors.json gs://harmony-lab-uploads
```

---

## Step 5: Secret Manager Setup

```bash
# Store database connection string
echo -n "Server=YOUR_CLOUD_SQL_IP;Database=HarmonyLab;User Id=sqlserver;Password=YOUR_PASSWORD;Encrypt=True;TrustServerCertificate=True;" | \
  gcloud secrets create harmony-lab-db-connection --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding harmony-lab-db-connection \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Step 6: Service Account & IAM

```bash
# Create dedicated service account for Cloud Run
gcloud iam service-accounts create harmony-lab-backend \
  --display-name="HarmonyLab Backend Service"

# Grant necessary permissions
gcloud projects add-iam-policy-binding harmony-lab \
  --member="serviceAccount:harmony-lab-backend@harmony-lab.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding harmony-lab \
  --member="serviceAccount:harmony-lab-backend@harmony-lab.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## Step 7: Initial Cloud Run Deployment (Placeholder)

Create a minimal FastAPI app to verify infrastructure:

```bash
# We'll scaffold this properly in the next step
# For now, verify the project is set up correctly:

gcloud run services list
gcloud sql instances list
gsutil ls
```

---

## Cost Estimate (Monthly)

| Service | Estimate | Notes |
|---------|----------|-------|
| Cloud SQL (shared instance) | $0 | Using existing instance |
| Cloud Run | $5-15 | Scale-to-zero, pay per request |
| Cloud Storage | $1-2 | Small music files |
| Secret Manager | $0.06 | Per secret version |
| **Total** | **~$6-18/mo** | |

If new SQL instance needed: add ~$50/month for Express tier.

---

## Verification Checklist

- [ ] Project `harmony-lab` created and billing linked
- [ ] All APIs enabled (run, sqladmin, storage, secretmanager, cloudbuild)
- [ ] `HarmonyLab` database created on Cloud SQL instance
- [ ] Schema executed successfully (all tables, indexes, seed data)
- [ ] Storage bucket `harmony-lab-uploads` created with CORS
- [ ] Connection string secret stored in Secret Manager
- [ ] Service account created with proper IAM roles

---

## Next Steps (After Infrastructure)

1. **Scaffold FastAPI project** - models, routes, database connection
2. **MIDI parser** - Use `mido` library for Python
3. **Basic API endpoints** - Songs CRUD, upload endpoint
4. **Simple React frontend** - Song list, import modal

---

*Created: 2025-12-26 | Sprint 1*
