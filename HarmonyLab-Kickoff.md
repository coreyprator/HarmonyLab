# Harmony Lab - Project Kickoff Document

## Project Vision

**Harmony Lab** is a harmonic progression training system designed to help musicians internalize the chord progressions of jazz standards and popular songs. The goal is to enable spontaneous performance—sitting down at a piano and playing from memory without sheet music.

**Core Value Proposition**: Transform the challenge of memorizing 30+ songs' chord progressions into an engaging, quiz-based learning system with standardized notation and multiple practice modes.

---

## Owner Context

### Musical Background
- Can play most melodies by heart
- Understands standard jazz voicings well
- Gap: Harmonic progressions not well-ingrained
- Goal: Spontaneous performance from memory

### Technical Background
- **20 years MS SQL Server expertise** - leverage this rather than learning PostgreSQL
- **18 months AI-assisted language learning** - proven methodology from Super-Flashcards project
- **GCP deployment experience** - Cloud Run, Cloud SQL, Cloud Storage patterns established
- **Proven development methodology** - Sprint-based planning with AI collaboration (Claude for architecture, VS Code AI for implementation)

### Existing Repertoire (37 Songs)
Source document: https://docs.google.com/document/d/1jnhevykL-3-dgkBR1Q-JYaB9ndtEMuVZnymIV-XoAPo/

| # | Title | Genre |
|---|-------|-------|
| 1 | Prelude No. 1 BWV 846 in C Major | Classical |
| 2 | Girl from Ipanema | Standard |
| 3 | As Time Goes By | Standard |
| 4 | One Note Samba | Bossa Nova |
| 5 | Take 5 | Bossa Nova |
| 6 | Blue Bossa | Bossa Nova |
| 7 | Wave | Standard |
| 8 | Fly Me to the Moon | Standard |
| 9 | How Insensitive | Bossa Nova |
| 10 | Desafinado | Bossa Nova |
| 11 | Watch What Happens | Standard |
| 12 | Corcovado | Standard |
| 13 | I've Got You Under My Skin | Standard |
| 14 | I Love Paris | Standard |
| 15 | La Vie en Rose | Bossa Nova |
| 16 | Manha de Carnaval | Standard |
| 17 | My Funny Valentine | Standard |
| 18 | Once I Loved | Standard |
| 19 | Stardust | Standard |
| 20 | Summer Samba | Standard |
| 21 | Summertime | Bossa Nova |
| 22 | The Look of Love | Bossa Nova |
| 23 | The Way You Look Tonight | Latin |
| 24 | The Windmills Of Your Mind | Standard |
| 25 | Tres Palabras | Bossa Nova |
| 26 | Triste | Standard |
| 27 | What Are You Doing For the Rest of Your Life? | Standard |
| 28 | Sabor a Mi | Standard |
| 29 | Night and Day | Standard |
| 30 | Midnight Sun | Latin |
| 31 | Moonglow | Bossa Nova |
| 32 | Love for Sale | Standard |
| 33 | I'm In The Mood For Love | Standard |
| 34 | Baubles, Bangles and Beads | Standard |
| 35 | Besame Mucho | Standard |
| 36 | Bewitched | Bossa Nova |
| 37 | Moonlight Serenade | Standard |

---

## Data Architecture

### Core Paradigm: Hierarchical Sequential Data
Unlike flashcards (flat) or etymology (graph), harmonic progressions are **ordered sequences within hierarchical structures**.

```
Song
├── Metadata (title, composer, key, tempo, genre)
├── Section[]
│   ├── name (Intro, A, B, Bridge, Coda, etc.)
│   ├── order
│   └── Measure[]
│       ├── measure_number
│       ├── beat_position (for multiple chords per measure)
│       └── Chord
│           ├── symbol (Am7, Abdim7, CMaj9)
│           ├── roman_numeral (i7, bVIIdim7, Imaj9)
│           ├── key_center (A minor, F Major)
│           └── comment/explanation
└── Tags (ballad, bossa, uptempo, etc.)
```

### Data Model Detail

Reference spreadsheet: https://docs.google.com/spreadsheets/d/1sjOUWVRw3oehUKhw4tmRpRGHqCiu_wM8jQ0J6mpwTTk/

```sql
-- Core entities
CREATE TABLE Songs (
    id INT IDENTITY PRIMARY KEY,
    title NVARCHAR(200) NOT NULL,
    composer NVARCHAR(200),
    arranger NVARCHAR(200),
    original_key VARCHAR(10),
    tempo_marking VARCHAR(50),
    genre VARCHAR(50),
    time_signature VARCHAR(10) DEFAULT '4/4',
    year_composed INT,
    notes NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);

CREATE TABLE Sections (
    id INT IDENTITY PRIMARY KEY,
    song_id INT FOREIGN KEY REFERENCES Songs(id),
    name VARCHAR(50) NOT NULL, -- 'Intro', 'A', 'B', 'Bridge', 'Coda', etc.
    section_order INT NOT NULL,
    repeat_count INT DEFAULT 1,
    notes NVARCHAR(500)
);

CREATE TABLE Measures (
    id INT IDENTITY PRIMARY KEY,
    section_id INT FOREIGN KEY REFERENCES Sections(id),
    measure_number INT NOT NULL,
    -- Some measures have multiple chords; beat_position handles this
    created_at DATETIME2 DEFAULT GETDATE()
);

CREATE TABLE Chords (
    id INT IDENTITY PRIMARY KEY,
    measure_id INT FOREIGN KEY REFERENCES Measures(id),
    beat_position DECIMAL(3,2) DEFAULT 1.0, -- 1.0, 2.0, 3.0, 4.0 or 1.5 for offbeats
    chord_symbol VARCHAR(20) NOT NULL, -- 'Am7', 'Abdim7', 'CMaj9'
    roman_numeral VARCHAR(20), -- 'i7', 'bVIIdim7', 'Imaj7'
    key_center VARCHAR(20), -- 'A minor', 'F Major'
    function_label VARCHAR(50), -- 'tonic', 'dominant', 'pre-dominant', 'passing'
    comments NVARCHAR(500),
    chord_order INT NOT NULL -- for ordering within measure
);

-- Standardized chord notation lookup (for dropdowns)
CREATE TABLE ChordVocabulary (
    id INT IDENTITY PRIMARY KEY,
    canonical_symbol VARCHAR(20) NOT NULL, -- The standard form
    display_name VARCHAR(30), -- How to display
    chord_type VARCHAR(30), -- 'major7', 'minor7', 'dominant7', 'diminished', etc.
    intervals VARCHAR(50), -- '1 3 5 7' or '1 b3 5 b7'
    aliases NVARCHAR(200) -- JSON array of alternative notations
);

-- Roman numeral vocabulary (for dropdowns)
CREATE TABLE RomanNumeralVocabulary (
    id INT IDENTITY PRIMARY KEY,
    canonical_symbol VARCHAR(20) NOT NULL,
    scale_degree INT,
    quality VARCHAR(30),
    function_type VARCHAR(30) -- 'tonic', 'dominant', 'subdominant', 'secondary_dominant'
);

-- User progress tracking
CREATE TABLE UserSongProgress (
    id INT IDENTITY PRIMARY KEY,
    user_id INT FOREIGN KEY,
    song_id INT FOREIGN KEY REFERENCES Songs(id),
    last_practiced DATETIME2,
    times_practiced INT DEFAULT 0,
    accuracy_rate DECIMAL(5,2), -- percentage
    mastery_level INT DEFAULT 0, -- 0-5 scale
    notes NVARCHAR(500)
);

CREATE TABLE QuizAttempts (
    id INT IDENTITY PRIMARY KEY,
    user_id INT FOREIGN KEY,
    song_id INT FOREIGN KEY REFERENCES Songs(id),
    quiz_type VARCHAR(30), -- 'sequential', 'fill_blank', 'full_progression'
    section_id INT FOREIGN KEY REFERENCES Sections(id), -- NULL if whole song
    started_at DATETIME2,
    completed_at DATETIME2,
    total_questions INT,
    correct_answers INT,
    details NVARCHAR(MAX) -- JSON with question-by-question results
);
```

### Standardized Notation System

Critical for quiz functionality—avoid misspellings like "Gmin9" vs "G-9":

**Chord Symbol Standards:**

| Type | Canonical | Aliases |
|------|-----------|---------|
| Major 7 | CMaj7 | CM7, CΔ7, Cmaj7 |
| Minor 7 | Cm7 | Cmin7, C-7, Cmi7 |
| Dominant 7 | C7 | Cdom7 |
| Half-diminished | Cø7 | Cm7b5, Cø, C-7b5 |
| Diminished 7 | Cdim7 | C°7, Cº7 |
| Minor 9 | Cm9 | Cmin9, C-9 |
| Major 9 | CMaj9 | CM9, CΔ9 |
| Add 9 | Cadd9 | C(add9) |
| Augmented | Caug | C+, C+7 |
| Suspended 4 | Csus4 | Csus |
| Altered | C7alt | C7#9#5 |

**Roman Numeral Standards:**

| Function | Major Key | Minor Key |
|----------|-----------|-----------|
| Tonic | I, Imaj7 | i, i7 |
| Supertonic | ii, ii7 | ii°, iiø7 |
| Mediant | iii, iii7 | III, IIImaj7 |
| Subdominant | IV, IVmaj7 | iv, iv7 |
| Dominant | V, V7 | V, V7 (often major) |
| Submediant | vi, vi7 | VI, VImaj7 |
| Leading tone | vii°, viiø7 | VII, VII7 |
| Secondary dom | V7/V, V7/ii, etc. | |
| Borrowed | bVII, bVI, bIII | |

---

## UI/UX Design

### Primary Interface: Song View with Progression Display

```
┌─────────────────────────────────────────────────────────────────┐
│  HARMONY LAB                    [My Songs ▼] [Practice] [Quiz]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🎵 As Time Goes By                                             │
│  Key: F Major | Tempo: Moderate Ballad | 4/4                    │
│                                                                 │
│  ┌─ INTRO ─────────────────────────────────────────────────┐    │
│  │  1        2        3        4        5        6    7    │    │
│  │  Am7      │        │ Abdim7 │ Gm7    │ C7     │Fmaj9│   │    │
│  │  i7       │        │bVIIdim │ ii7    │ V7     │Imaj7│   │    │
│  │  [A min]  │        │        │[F Maj] │        │     │   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─ A SECTION ─────────────────────────────────────────────┐    │
│  │  8        9        10       11       12       13   14   │    │
│  │  Dm7      │ G7     │ CMaj7  │ Am7    │ Dm7    │ G7 │... │    │
│  │  vi7      │ V7/V   │ Vmaj7  │ iii7   │ vi7    │V7/V│    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  [◀ Prev Section]                          [Next Section ▶]     │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  💡 Measure 4: Abdim7 is a passing diminished chord,            │
│  creating chromatic bass movement: A → Ab → G                    │
│                                                                 │
│  [▶ Play Section]  [🎯 Quiz This Section]  [📝 Edit]            │
└─────────────────────────────────────────────────────────────────┘
```

### Quiz Modes

#### Mode 1: Sequential ("What Comes Next?")

```
┌─────────────────────────────────────────────────────────────────┐
│  QUIZ: As Time Goes By - Intro                    [Exit Quiz]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Measure 5: After Abdim7, what chord comes next?                │
│                                                                 │
│  Previous context:                                              │
│  │ Am7 │ - │ - │ Abdim7 │ [?] │                                 │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Select chord:  [Gm7          ▼]                         │   │
│  │                                                          │   │
│  │  Common choices:                                         │   │
│  │  ○ Gm7    ○ G7    ○ Dm7    ○ CMaj7                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Submit Answer]                                                │
│                                                                 │
│  Progress: ████████░░ 8/10                                      │
└─────────────────────────────────────────────────────────────────┘
```

#### Mode 2: Fill in the Blank

```
┌─────────────────────────────────────────────────────────────────┐
│  QUIZ: As Time Goes By - Full Song               [Exit Quiz]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Fill in the missing chords:                                    │
│                                                                 │
│  INTRO:                                                         │
│  │ Am7 │ - │ - │ [___▼] │ Gm7 │ [___▼] │ Fmaj9 │               │
│                                                                 │
│  A SECTION:                                                     │
│  │ Dm7 │ [___▼] │ CMaj7 │ Am7 │ Dm7 │ G7 │ ...                 │
│                                                                 │
│  [Check Answers]                                                │
│                                                                 │
│  Score: ___/10                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Entry Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  EDIT: Girl from Ipanema                          [Save] [×]    │
├─────────────────────────────────────────────────────────────────┤
│  Title: [Girl from Ipanema        ]                             │
│  Key: [F Major ▼]  Tempo: [Moderate Bossa ▼]  Time: [4/4 ▼]     │
│                                                                 │
│  Section: [A ▼]  [+ Add Section]                                │
│                                                                 │
│  ┌─ Measures ───────────────────────────────────────────────┐   │
│  │ #  │ Chord      │ Roman    │ Key Center │ Notes          │   │
│  ├────┼────────────┼──────────┼────────────┼────────────────┤   │
│  │ 1  │ [FMaj7 ▼]  │ [Imaj7▼] │ [F Major▼] │ [____________] │   │
│  │ 2  │ [G7   ▼]   │ [V7/V ▼] │ [C Major▼] │ [Secondary V ] │   │
│  │ 3  │ [Gm7  ▼]   │ [ii7  ▼] │ [F Major▼] │ [____________] │   │
│  │ 4  │ [Gb7  ▼]   │ [bII7 ▼] │ [F Major▼] │ [Tritone sub ] │   │
│  │ [+ Add Measure]                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  💡 Tip: Use dropdowns to avoid notation inconsistencies        │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile Considerations
- Swipe through measures
- Large touch targets for dropdowns
- Portrait mode optimized for chord charts
- Offline practice mode

---

## Technical Architecture

### Stack (Inherited from Super-Flashcards)

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend | FastAPI | Same patterns as Super-Flashcards |
| Database | MS SQL Server (Cloud SQL) | Hierarchical data queries |
| Frontend | Vanilla JavaScript | Clean chord chart rendering |
| Hosting | Google Cloud Run | Scale-to-zero |
| Storage | Google Cloud Storage | MIDI files, audio samples |
| Auth | Same as Super-Flashcards | User progress tracking |
| **Playback** | **Tone.js** | Web Audio synthesis, MIDI scheduling |
| **MIDI parsing** | **Mido (Python)** | Server-side MIDI file parsing |
| **MusicXML parsing** | **music21 (Python)** | Comprehensive music notation library |

### API Structure

```
/api/v1/
├── songs/
│   ├── GET / (list with filters)
│   ├── GET /{id} (full song with all sections/measures/chords)
│   ├── POST / (create new song)
│   ├── PUT /{id} (update song)
│   └── DELETE /{id}
├── import/
│   ├── POST /midi (upload and parse MIDI file)
│   ├── POST /musicxml (upload and parse MXL file)
│   ├── POST /musescore (upload and parse .mscz file)
│   └── GET /preview/{import_id} (review parsed data before saving)
├── sections/
│   ├── GET /{song_id}/sections
│   ├── POST /{song_id}/sections
│   └── PUT /{section_id}
├── measures/
│   ├── POST /{section_id}/measures
│   ├── PUT /{measure_id}
│   └── DELETE /{measure_id}
├── chords/
│   ├── POST /{measure_id}/chords
│   ├── PUT /{chord_id}
│   └── DELETE /{chord_id}
├── melody/
│   ├── GET /{song_id}/melody (get melody notes for playback)
│   └── PUT /{song_id}/melody (update melody data)
├── vocabulary/
│   ├── GET /chord-symbols (for dropdowns)
│   └── GET /roman-numerals (for dropdowns)
├── playback/
│   ├── GET /{song_id}/data (get all data needed for Tone.js playback)
│   └── POST /{song_id}/transpose (transpose by N semitones)
├── quiz/
│   ├── POST /start (song_id, quiz_type, section_id?)
│   ├── POST /answer (attempt_id, question_index, answer)
│   ├── GET /results/{attempt_id}
│   └── GET /history (user's quiz history)
└── progress/
    ├── GET /songs (user's progress on all songs)
    ├── GET /songs/{song_id} (detailed progress)
    └── POST /practice/{song_id} (log practice session)
```

---

## Playback System

### Priority: Sprint 1-2 Feature

Playback is essential—users need to hear progressions to internalize them. Both harmony and melody playback are required.

### Library Evaluation

| Library | Pros | Cons | Recommendation |
|---------|------|------|----------------|
| **Tone.js** | Full-featured Web Audio, built-in synths, MIDI support, scheduling | Larger bundle size | ✓ **Primary choice** |
| **MIDI.js** | Lightweight, SoundFont support | Less maintained | Backup option |
| **Magenta.js** | Google-backed, ML features | Overkill for playback | Not needed |
| **MuseScore/Ableton integration** | Professional sound | External app dependency, complex integration | Avoid |

**Recommendation: Tone.js**

Tone.js provides everything needed without external app dependencies:
- Built-in synthesizers (Piano, FM, AM synths)
- MIDI file playback
- Precise timing/scheduling (critical for syncopation)
- Transport controls (play, pause, seek, loop)
- Can load SoundFonts for realistic piano sounds

### Playback Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  PLAYBACK CONTROLS                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🎵 Blue Bossa                          Key: [C minor ▼]        │
│                                                                 │
│  [▶ Play] [⏸ Pause] [⏹ Stop]  Tempo: [120 ▼] BPM               │
│                                                                 │
│  ┌─ Playback Options ─────────────────────────────────────┐     │
│  │  ☑ Harmony    ☑ Melody    ☐ Metronome                  │     │
│  │  Harmony voice: [Piano ▼]   Melody voice: [Vibes ▼]    │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
│  Section: [Intro ▼] [A ▼] [B ▼] [A ▼]    [Loop Section ☑]      │
│                                                                 │
│  ─────────●─────────────────────────────────── 0:24 / 1:32     │
│                                                                 │
│  ┌─ Current Position ─────────────────────────────────────┐     │
│  │  Measure 5  │  Cm7  │  i7  │  C minor                  │     │
│  │             ▲                                          │     │
│  │         [melody note highlighted]                      │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tone.js Implementation Sketch

```javascript
import * as Tone from 'tone';

class HarmonyPlayer {
    constructor() {
        // Piano for chords
        this.chordSynth = new Tone.PolySynth(Tone.Synth).toDestination();
        // Lead synth for melody
        this.melodySynth = new Tone.Synth().toDestination();
        // Transport for timing
        this.transport = Tone.Transport;
    }

    loadSong(song) {
        this.transport.cancel(); // Clear previous
        
        // Schedule chord changes
        song.chords.forEach(chord => {
            const time = this.beatsToTime(chord.measure, chord.beat);
            this.transport.schedule((t) => {
                const notes = chordToNotes(chord.symbol); // ['C4', 'E4', 'G4', 'B4']
                this.chordSynth.triggerAttackRelease(notes, chord.duration, t);
            }, time);
        });

        // Schedule melody notes
        song.melodyNotes.forEach(note => {
            const time = this.beatsToTime(note.measure, note.beat);
            this.transport.schedule((t) => {
                const pitch = midiToPitch(note.midi_note); // 60 → 'C4'
                this.melodySynth.triggerAttackRelease(pitch, note.duration, t);
            }, time);
        });
    }

    play() { this.transport.start(); }
    pause() { this.transport.pause(); }
    stop() { this.transport.stop(); this.transport.position = 0; }
    
    setTempo(bpm) { this.transport.bpm.value = bpm; }
    
    // Transpose all chords
    transpose(semitones) {
        // Recalculate chord symbols and melody notes
    }
}
```

### Syncopation & Timing

Bossa Nova and Latin styles have syncopated rhythms where chords don't land on downbeats. The system must:

1. **Store precise beat positions** - `beat_position DECIMAL(5,3)` allows 1.5, 2.75, etc.
2. **Visual alignment** - Show melody notes above chord chart with timing alignment
3. **Playback accuracy** - Tone.js Transport handles sub-beat scheduling

```
Standard 4/4:     | 1   2   3   4   |
Bossa pattern:    | 1 . 2 . 3 . 4 . |
Chord hits:       | X     X   X   X | (syncopated)
Melody:           |   X X   X   X   |
```

### Transposition

Simple modal math—shift all notes by N semitones:

```python
def transpose_song(song_id: int, semitones: int):
    """
    Transpose all chords and melody notes by N semitones.
    """
    # Chord symbols: Cm7 + 5 semitones = Fm7
    for chord in get_chords(song_id):
        root = extract_root(chord.symbol)  # 'C'
        new_root = transpose_note(root, semitones)  # 'F'
        chord.symbol = new_root + extract_quality(chord.symbol)  # 'Fm7'
        chord.save()
    
    # Melody: MIDI note + semitones
    for note in get_melody_notes(song_id):
        note.midi_note += semitones
        note.save()
    
    # Update song key
    song = get_song(song_id)
    song.original_key = transpose_key(song.original_key, semitones)
    song.save()
```

**UI**: Simple dropdown or +/- buttons to shift key. Display both original and transposed key.

---

## Quiz Algorithm

### Sequential Quiz Logic

```python
def generate_sequential_quiz(song_id, section_id=None, num_questions=10):
    """
    Generate "what comes next" questions.
    Shows N measures of context, asks for next chord.
    """
    chords = get_chords_for_section_or_song(song_id, section_id)
    
    questions = []
    for i in range(num_questions):
        # Random starting point, ensuring we have a "next" chord
        start_idx = random.randint(0, len(chords) - 2)
        
        # Context: previous 2-4 chords
        context_start = max(0, start_idx - 3)
        context = chords[context_start:start_idx + 1]
        
        # Answer: the next chord
        correct_answer = chords[start_idx + 1]
        
        # Distractors: other chords from the song + common jazz chords
        distractors = generate_plausible_distractors(correct_answer, chords)
        
        questions.append({
            "context": context,
            "correct_answer": correct_answer,
            "options": shuffle([correct_answer] + distractors[:3])
        })
    
    return questions
```

### Fill-in-the-Blank Logic

```python
def generate_fill_blank_quiz(song_id, section_id=None, blank_percentage=0.3):
    """
    Show progression with some chords blanked out.
    User fills in missing chords from dropdowns.
    """
    chords = get_chords_for_section_or_song(song_id, section_id)
    
    # Select ~30% of chords to blank (avoid consecutive blanks)
    num_blanks = int(len(chords) * blank_percentage)
    blank_indices = select_non_consecutive(range(len(chords)), num_blanks)
    
    quiz = []
    for i, chord in enumerate(chords):
        quiz.append({
            "measure": chord.measure_number,
            "is_blank": i in blank_indices,
            "correct_answer": chord.chord_symbol if i in blank_indices else None,
            "displayed": None if i in blank_indices else chord.chord_symbol
        })
    
    return quiz
```

---

## Data Entry Strategy

### Primary Method: File Import

AI is not mature enough to reliably read lead sheets, especially image-based formats. Instead, leverage existing digital formats that most music is already available in.

**Supported Import Formats:**

| Format | Extension | Description | Parser |
|--------|-----------|-------------|--------|
| MIDI | .mid, .midi | Standard music interchange | Mido (Python), Tone.js (JS) |
| MusicXML | .mxl, .xml | Sheet music interchange | music21 (Python), opensheetmusic |
| MuseScore | .mscz | MuseScore native format | Compressed XML, parse after unzip |
| iReal Pro | via MIDI export | Users can export from iReal to MIDI | Handled by MIDI parser |

**Note**: iReal Pro is Apple-only with limited reach. Since it exports to MIDI, no special iReal support needed—MIDI import covers it.

### Import Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  IMPORT WORKFLOW                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User uploads: song.mid / song.mxl / song.mscz                  │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  PARSER                                                 │    │
│  │  • Extract tempo, time signature, key                   │    │
│  │  • Separate melody track from chord track               │    │
│  │  • Map MIDI notes to chord symbols                      │    │
│  │  • Preserve timing (critical for syncopation)           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  REVIEW & ENRICH                                        │    │
│  │  • Auto-detected: Dm7 | G7 | CMaj7 | ...                │    │
│  │  • User adds: Roman numerals, key centers, comments     │    │
│  │  • Verify section boundaries (Intro, A, B, etc.)        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                        │                                        │
│                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  SAVE TO DATABASE                                       │    │
│  │  • Song metadata                                        │    │
│  │  • Chord progression with timing                        │    │
│  │  • Melody data for playback                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Chord Detection from MIDI

MIDI contains raw notes, not chord symbols. The parser must:

1. **Identify chord voicings** - Group simultaneous notes
2. **Map to chord symbols** - C-E-G-B → CMaj7
3. **Handle inversions** - E-G-B-C still → CMaj7
4. **Detect extensions** - 9ths, 11ths, 13ths
5. **Flag ambiguous chords** - For user review

```python
def midi_notes_to_chord(notes: List[int]) -> str:
    """
    Convert MIDI note numbers to chord symbol.
    Returns best match with confidence score.
    """
    # Normalize to pitch classes (0-11)
    pitch_classes = sorted(set(n % 12 for n in notes))
    
    # Match against chord templates
    matches = []
    for root in range(12):
        for chord_type, intervals in CHORD_TEMPLATES.items():
            template = sorted((root + i) % 12 for i in intervals)
            if pitch_classes == template:
                matches.append((NOTE_NAMES[root] + chord_type, 1.0))
    
    # Handle partial matches, inversions, extensions...
    return best_match(matches)
```

### Melody Extraction

Melody is typically the highest voice or a dedicated track. Store melody data for:
- **Playback** - Hear melody alongside harmony
- **Timing reference** - See where chords align with melodic phrases
- **Syncopation** - Critical for Bossa Nova, Latin styles

```sql
CREATE TABLE MelodyNotes (
    id INT IDENTITY PRIMARY KEY,
    song_id INT FOREIGN KEY REFERENCES Songs(id),
    measure_number INT,
    beat_position DECIMAL(5,3),  -- Precise timing for syncopation
    midi_note INT,               -- MIDI note number (60 = middle C)
    duration DECIMAL(5,3),       -- In beats
    velocity INT                 -- Optional: dynamics
);
```

---

## Development Phases

### Phase 1: Foundation & Import (Sprint 1-2)
- [ ] Database schema creation
- [ ] **Simple text-grid UI** (iterate based on user feedback)
- [ ] MIDI file parser and import
- [ ] MusicXML (.mxl) parser and import
- [ ] MuseScore (.mscz) parser and import
- [ ] Chord detection from MIDI notes
- [ ] Basic song list and detail views
- [ ] Import 5 songs for testing

### Phase 2: Playback & Melody (Sprint 3-4)
- [ ] **Tone.js integration** (priority feature)
- [ ] Chord playback with piano voice
- [ ] Melody playback from imported data
- [ ] Transport controls (play, pause, stop, seek)
- [ ] Tempo control
- [ ] **Transposition feature** (shift by semitones)
- [ ] Visual sync: highlight current chord during playback

### Phase 3: Quiz System (Sprint 5-6)
- [ ] Sequential quiz generation ("what comes next")
- [ ] Fill-in-the-blank quiz generation
- [ ] Dropdown-based answer selection (standardized notation)
- [ ] Quiz attempt tracking
- [ ] Results display with explanations

### Phase 4: Progress & Polish (Sprint 7-8)
- [ ] User progress dashboard
- [ ] Accuracy tracking per song/section
- [ ] Spaced repetition suggestions
- [ ] Mobile-optimized UI
- [ ] Offline quiz mode (IndexedDB)
- [ ] Section looping for practice

---

## GCP Setup

**Project Name**: `harmony-lab`
**Region**: Same as Super-Flashcards for consistency

### Services Required
- Cloud Run (backend)
- Cloud SQL (MS SQL)
- Cloud Storage (sheet music PDFs, audio samples)
- Secret Manager (API keys if needed)

### Estimated Costs
Similar to Super-Flashcards: $15-40/month with scale-to-zero

---

## Key Learnings to Apply (from Super-Flashcards)

1. **Sprint documentation**: Maintain comprehensive handoff docs for AI collaboration
2. **Change tracking**: CHANGES.md for every sprint
3. **Testing protocols**: Playwright for automated testing
4. **Environment separation**: QA vs Production isolation
5. **User auth patterns**: Reuse authentication approach
6. **IndexedDB patterns**: Offline-first where appropriate

---

## Open Questions - ANSWERED

| Question | Answer |
|----------|--------|
| **Chord rendering** - Simple text grid vs. musical notation? | Start with **simple text grid**. Iterate based on user testing feedback. |
| **Audio playback** - Priority or later phase? | **Priority feature** - Sprint 2. Essential for learning. |
| **Multiple keys** - Support transposition? | **Yes**. Simple modal math (shift by semitones). |
| **Real Book integration** - Reference measure numbers? | No direct Real Book integration. **Support MIDI, MXL, MuseScore imports** instead. iReal Pro exports to MIDI, so that's covered. No text or image import—AI not reliable for lead sheet reading. |

---

## Success Metrics

- User can **import** a song from MIDI/MXL in <5 minutes
- Quiz mode feels natural, not tedious
- Dropdown notation prevents all spelling variations
- Playback helps user hear and internalize progressions
- User can practice offline
- Progress tracking motivates continued practice
- After 2 weeks of practice, user can play 3+ songs from memory

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-21 | Claude + Corey | Initial kickoff document |

---

*This document seeds the Harmony Lab project in Claude. Copy this entire document into the new project's knowledge base.*
