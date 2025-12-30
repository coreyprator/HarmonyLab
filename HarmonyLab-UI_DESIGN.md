# HarmonyLab UI Design Specification

**Project**: HarmonyLab  
**Version**: 1.0  
**Created**: 2025-12-28  
**Author**: Claude (Architect)  
**Status**: Sprint 1 Deliverable - Ready for VS Code AI Implementation

---

## Design Philosophy

### Core Principles

1. **Function Over Flash** — This is a practice tool, not a showcase. Optimize for learning efficiency.
2. **Text-First Grid** — Use simple text grids for chord progressions, not musical notation (per kickoff doc).
3. **Keyboard-Friendly** — Jazz pianists have hands on keyboards. Support keyboard navigation in quizzes.
4. **Audio Integration** — Hearing progressions is essential for learning. Tone.js playback is a priority feature.
5. **Mobile-Responsive** — Practice happens at the piano, often on a tablet or phone.

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Framework | React 18 | Component reusability, ecosystem |
| Styling | Tailwind CSS | Rapid UI development, consistent design |
| Audio | Tone.js | Web audio synthesis, piano voices |
| State | React Context + useState | Simple state needs, no Redux overhead |
| Routing | React Router v6 | Standard SPA routing |
| Build | Vite | Fast dev server, optimized builds |

---

## Information Architecture

```
HarmonyLab
├── Home (Song Library)
│   ├── Song List
│   ├── Filter by Genre
│   ├── Search
│   └── Import Song Button
│
├── Song Detail
│   ├── Metadata Header
│   ├── Chord Progression Grid
│   ├── Playback Controls
│   └── Actions (Quiz, Edit, Delete)
│
├── Quiz Mode
│   ├── Quiz Setup (select song, mode, section)
│   ├── Quiz Interface
│   └── Results Summary
│
├── Progress Dashboard
│   ├── Overall Stats
│   ├── Per-Song Progress
│   └── Practice History
│
└── Import
    ├── File Upload
    ├── Preview/Edit
    └── Save Confirmation
```

---

## Page Designs

### 1. Home Page (Song Library)

**URL**: `/`

**Purpose**: Browse and select songs to practice.

```
┌─────────────────────────────────────────────────────────────────┐
│  🎹 HarmonyLab                          [Progress] [Import]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Search songs...]                    Filter: [All Genres ▼]    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Girl from Ipanema          Bossa Nova    ★★★☆☆   [→]    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Blue Bossa                 Bossa Nova    ★★★★☆   [→]    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Fly Me to the Moon         Standard      ★★☆☆☆   [→]    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Corcovado                  Standard      ★★★★★   [→]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Showing 37 songs                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components**:
- `<Header />` — Logo, navigation links
- `<SearchBar />` — Text search across song titles
- `<GenreFilter />` — Dropdown filter (All, Bossa Nova, Standard, Latin, Classical)
- `<SongList />` — Scrollable list of songs
- `<SongCard />` — Individual song row with title, genre, mastery stars, click to detail

**Interactions**:
- Click song → Navigate to Song Detail
- Click Import → Navigate to Import page
- Click Progress → Navigate to Progress Dashboard
- Type in search → Filter song list in real-time
- Select genre → Filter song list

**API Endpoints Used**:
- `GET /api/songs` — List all songs
- `GET /api/progress` — Get mastery levels for star display

---

### 2. Song Detail Page

**URL**: `/songs/:id`

**Purpose**: View chord progression, play audio, start quiz.

```
┌─────────────────────────────────────────────────────────────────┐
│  [← Back]  Girl from Ipanema                    [Edit] [Delete] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Composer: Antonio Carlos Jobim    Key: F Major    BPM: 140     │
│  Genre: Bossa Nova                 Time: 4/4                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Transpose: [−] F Major [+]                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Section: A                                                     │
│  ┌────────┬────────┬────────┬────────┐                         │
│  │ FMaj7  │ FMaj7  │ G7     │ G7     │  1-4                    │
│  ├────────┼────────┼────────┼────────┤                         │
│  │ Gm7    │ Gb7    │ FMaj7  │ Gb7    │  5-8                    │
│  └────────┴────────┴────────┴────────┘                         │
│                                                                 │
│  Section: B                                                     │
│  ┌────────┬────────┬────────┬────────┐                         │
│  │ GbMaj7 │ GbMaj7 │ B9     │ B9     │  9-12                   │
│  ├────────┼────────┼────────┼────────┤                         │
│  │ F#m9   │ D7     │ Gm9    │ Eb9    │  13-16                  │
│  └────────┴────────┴────────┴────────┘                         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  [◀◀] [▶ Play]  ████████░░░░░░░░░░  1:24 / 3:45  [🔊]    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [📝 Start Quiz]                [📊 View Progress]             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components**:
- `<SongHeader />` — Title, metadata (composer, key, tempo, genre)
- `<TransposeControl />` — Shift key up/down by semitones
- `<ChordGrid />` — 4-column grid showing measures and chords
- `<SectionLabel />` — Section name (A, B, Bridge, etc.)
- `<ChordCell />` — Individual chord display, highlights during playback
- `<PlaybackControls />` — Play/pause, seek bar, volume, tempo adjust
- `<ActionButtons />` — Start Quiz, View Progress

**Chord Grid Specifications**:
- 4 measures per row (standard jazz lead sheet format)
- Each cell shows chord symbol
- Multiple chords per measure shown with beat position
- Current chord highlights during playback (yellow background)
- Roman numerals shown on hover/toggle

**Playback Features** (Tone.js):
- Piano voice for chord voicings
- Adjustable tempo (50%-150% of original)
- Visual sync: highlight current chord
- Loop section option

**API Endpoints Used**:
- `GET /api/songs/:id` — Song metadata
- `GET /api/songs/:id/progression` — Full chord progression
- `GET /api/songs/:id/sections` — Section list
- `GET /api/progress/song/:id` — Practice stats for this song

---

### 3. Quiz Page

**URL**: `/quiz/:songId`

**Purpose**: Practice chord recall through fill-in-the-blank quizzes.

#### 3a. Quiz Setup

```
┌─────────────────────────────────────────────────────────────────┐
│  [← Back]  Quiz: Girl from Ipanema                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Quiz Mode                                                      │
│  ○ Sequential - "What comes next?"                              │
│  ● Fill-in-Blank - Random chords hidden                         │
│                                                                 │
│  Section                                                        │
│  ○ Whole Song                                                   │
│  ● Section A only                                               │
│  ○ Section B only                                               │
│                                                                 │
│  Difficulty                                                     │
│  [████████░░] 40% blanks                                        │
│                                                                 │
│  [▶ Start Quiz]                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3b. Quiz Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  Quiz: Girl from Ipanema    Section A    Progress: 5/12         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────┬────────┬────────┬────────┐                         │
│  │ FMaj7  │  [?]   │ G7     │  [?]   │                         │
│  ├────────┼────────┼────────┼────────┤                         │
│  │  [?]   │ Gb7    │ FMaj7  │ Gb7    │                         │
│  └────────┴────────┴────────┴────────┘                         │
│                                                                 │
│  Fill in the blank:                                             │
│                                                                 │
│  Measure 2, Beat 1:                                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Root: [F ▼]   Quality: [Maj7 ▼]      →  FMaj7            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [Submit Answer]              [Skip] [Hear Chord]              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components**:
- `<QuizSetup />` — Mode selection, section, difficulty
- `<QuizGrid />` — Chord grid with blanks
- `<BlankCell />` — Highlighted cell indicating what to answer
- `<ChordPicker />` — Two dropdowns: Root note + Chord quality
- `<QuizControls />` — Submit, Skip, Hear Chord
- `<ProgressIndicator />` — X of Y questions answered

**Chord Picker Design** (Standardized Notation):
```
Root: [C][C#/Db][D][D#/Eb][E][F][F#/Gb][G][G#/Ab][A][A#/Bb][B]
Quality: [Maj7][m7][7][ø7][dim7][m9][Maj9][9][6][m6][sus4][aug]...
```
- Dropdowns populated from `ChordVocabulary` table
- Prevents typos/spelling variations
- Shows combined chord symbol preview

**Interactions**:
- Select root + quality → Preview shows "FMaj7"
- Submit → Check against correct answer, show feedback
- Skip → Move to next blank (counts as incorrect)
- Hear Chord → Play the correct chord audio (Tone.js)

**API Endpoints Used**:
- `POST /api/quiz/generate/:songId` — Generate quiz with blanks
- `POST /api/quiz/submit` — Submit answers, get results
- `GET /api/vocabulary/chords` — Chord dropdown options

---

#### 3c. Quiz Results

```
┌─────────────────────────────────────────────────────────────────┐
│  Quiz Complete!                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Girl from Ipanema - Section A                                  │
│                                                                 │
│  Score: 9/12 (75%)                                              │
│                                                                 │
│  ████████████████████░░░░░░                                     │
│                                                                 │
│  Mistakes:                                                      │
│  • Measure 5: You said Gm9, correct was Gm7                     │
│  • Measure 8: You said F7, correct was Gb7                      │
│  • Measure 11: Skipped (correct was FMaj7)                      │
│                                                                 │
│  [🔄 Try Again]    [📖 Review Song]    [🏠 Home]                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components**:
- `<ScoreSummary />` — Percentage, visual bar
- `<MistakesList />` — What was wrong and why
- `<ResultActions />` — Retry, review, or go home

---

### 4. Progress Dashboard

**URL**: `/progress`

**Purpose**: Track learning progress across all songs.

```
┌─────────────────────────────────────────────────────────────────┐
│  [← Back]  Your Progress                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Overall Stats                                                  │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐     │
│  │ Songs       │ Practiced   │ Mastered    │ Avg Score   │     │
│  │    37       │    12       │     3       │    68%      │     │
│  └─────────────┴─────────────┴─────────────┴─────────────┘     │
│                                                                 │
│  Recent Activity                                                │
│  • Girl from Ipanema - 85% (today)                              │
│  • Blue Bossa - 72% (yesterday)                                 │
│  • Fly Me to the Moon - 60% (2 days ago)                        │
│                                                                 │
│  Songs by Mastery                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ★★★★★ Mastered (3)                                      │   │
│  │   Corcovado, Blue Bossa, Wave                            │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ★★★☆☆ Learning (5)                                      │   │
│  │   Girl from Ipanema, One Note Samba, ...                 │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ ★☆☆☆☆ New (29)                                          │   │
│  │   [See all...]                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components**:
- `<StatsCards />` — Summary metrics
- `<RecentActivity />` — Last 5 quiz attempts
- `<MasteryTiers />` — Songs grouped by mastery level

**API Endpoints Used**:
- `GET /api/progress` — All user progress
- `GET /api/progress/stats` — Aggregate statistics
- `GET /api/quiz/attempts` — Recent quiz history

---

### 5. Import Page

**URL**: `/import`

**Purpose**: Upload MIDI files and import songs.

```
┌─────────────────────────────────────────────────────────────────┐
│  [← Back]  Import Song                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │     📁 Drop MIDI file here or click to browse           │   │
│  │                                                         │   │
│  │     Supported: .mid, .midi                              │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [After upload - Preview Mode]                                  │
│                                                                 │
│  Detected: 32 measures, 4/4 time, ~120 BPM                      │
│                                                                 │
│  Title: [Blue Bossa                    ]                        │
│  Composer: [Kenny Dorham                ]                       │
│  Genre: [Bossa Nova ▼]                                          │
│  Key: [C minor ▼]                                               │
│                                                                 │
│  Preview:                                                       │
│  ┌────────┬────────┬────────┬────────┐                         │
│  │ Cm7    │ Cm7    │ Fm7    │ Fm7    │                         │
│  ├────────┼────────┼────────┼────────┤                         │
│  │ Dm7b5  │ G7alt  │ Cm7    │ Cm7    │                         │
│  └────────┴────────┴────────┴────────┘                         │
│                                                                 │
│  ⚠️ 2 chords flagged for review (click to edit)                │
│                                                                 │
│  [Cancel]                              [Save Song]              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Components**:
- `<FileDropZone />` — Drag-and-drop file upload
- `<ImportPreview />` — Parsed chord data preview
- `<MetadataForm />` — Editable title, composer, genre, key
- `<ChordReview />` — Grid with flagged chords highlighted
- `<ImportActions />` — Cancel or Save

**Workflow**:
1. User drops MIDI file
2. API parses and returns detected chords
3. User reviews, edits metadata, fixes flagged chords
4. User clicks Save → Song created in database

**API Endpoints Used**:
- `POST /api/imports/midi` — Upload and parse MIDI
- `POST /api/imports/preview` — Get parsed preview
- `POST /api/imports/confirm` — Save to database

---

## Component Library

### Design Tokens

```css
/* Colors */
--color-primary: #2563eb;      /* Blue - actions, links */
--color-secondary: #64748b;    /* Slate - secondary text */
--color-success: #22c55e;      /* Green - correct answers */
--color-error: #ef4444;        /* Red - wrong answers */
--color-warning: #f59e0b;      /* Amber - flagged items */
--color-highlight: #fef08a;    /* Yellow - current chord */

/* Typography */
--font-sans: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', monospace;  /* Chord symbols */

/* Spacing */
--space-1: 0.25rem;
--space-2: 0.5rem;
--space-3: 0.75rem;
--space-4: 1rem;
--space-6: 1.5rem;
--space-8: 2rem;
```

### Chord Cell Component

```jsx
// ChordCell - displays a single chord in the grid
<ChordCell
  chord="FMaj7"
  romanNumeral="IVMaj7"
  isHighlighted={false}    // Yellow during playback
  isBlank={false}          // Shows [?] in quiz mode
  onClick={() => {}}       // For quiz selection
/>
```

**States**:
- Default: White background, black text
- Highlighted (playing): Yellow background
- Blank (quiz): Gray background with "?" 
- Correct (quiz result): Green border
- Incorrect (quiz result): Red border

### Responsive Breakpoints

| Breakpoint | Width | Columns in Grid |
|------------|-------|-----------------|
| Mobile | < 640px | 2 measures per row |
| Tablet | 640-1024px | 4 measures per row |
| Desktop | > 1024px | 4 measures per row, sidebar |

---

## Audio Implementation (Tone.js)

### Chord Playback

```javascript
// Initialize piano sampler
const piano = new Tone.Sampler({
  urls: {
    C4: "C4.mp3",
    // ... other samples
  },
  baseUrl: "https://tonejs.github.io/audio/salamander/",
}).toDestination();

// Play chord voicing
function playChord(chordSymbol, duration = "2n") {
  const notes = getVoicing(chordSymbol); // Returns ["C4", "E4", "G4", "B4"]
  piano.triggerAttackRelease(notes, duration);
}
```

### Playback Features

1. **Play/Pause** — Toggle chord sequence playback
2. **Tempo Control** — Slider 50%-150% of detected BPM
3. **Visual Sync** — Highlight current chord cell
4. **Section Loop** — Repeat selected section
5. **Single Chord** — Click any chord to hear it

---

## Accessibility

### Keyboard Navigation

| Key | Action |
|-----|--------|
| Tab | Move between interactive elements |
| Enter | Select/Submit |
| Space | Play/Pause audio |
| ← → | Navigate chords in grid |
| 1-9 | Quick-select root note (quiz) |

### ARIA Labels

```jsx
<button aria-label="Play chord progression">▶ Play</button>
<div role="grid" aria-label="Chord progression for Girl from Ipanema">
  <div role="row">
    <div role="gridcell" aria-label="Measure 1: F Major 7">FMaj7</div>
  </div>
</div>
```

### Color Contrast

All text meets WCAG AA contrast requirements (4.5:1 minimum).

---

## File Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── main.jsx                 # Entry point
│   ├── App.jsx                  # Router setup
│   ├── api/
│   │   └── client.js            # API client (fetch wrapper)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.jsx
│   │   │   └── Layout.jsx
│   │   ├── songs/
│   │   │   ├── SongList.jsx
│   │   │   ├── SongCard.jsx
│   │   │   └── SongDetail.jsx
│   │   ├── chords/
│   │   │   ├── ChordGrid.jsx
│   │   │   ├── ChordCell.jsx
│   │   │   └── ChordPicker.jsx
│   │   ├── quiz/
│   │   │   ├── QuizSetup.jsx
│   │   │   ├── QuizInterface.jsx
│   │   │   └── QuizResults.jsx
│   │   ├── playback/
│   │   │   ├── PlaybackControls.jsx
│   │   │   └── TonePlayer.js
│   │   ├── import/
│   │   │   ├── FileDropZone.jsx
│   │   │   └── ImportPreview.jsx
│   │   └── progress/
│   │       ├── StatsCards.jsx
│   │       └── MasteryTiers.jsx
│   ├── pages/
│   │   ├── HomePage.jsx
│   │   ├── SongPage.jsx
│   │   ├── QuizPage.jsx
│   │   ├── ProgressPage.jsx
│   │   └── ImportPage.jsx
│   ├── hooks/
│   │   ├── useSongs.js
│   │   ├── useQuiz.js
│   │   └── usePlayback.js
│   ├── context/
│   │   └── AudioContext.jsx     # Tone.js context
│   └── styles/
│       └── index.css            # Tailwind imports
├── package.json
├── vite.config.js
├── tailwind.config.js
└── .env                         # API_URL
```

---

## API Integration

### Base Configuration

```javascript
// src/api/client.js
const API_URL = import.meta.env.VITE_API_URL || 'https://harmonylab-wmrla7fhwa-uc.a.run.app';

export async function apiClient(endpoint, options = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }
  
  return response.json();
}
```

### Environment Variables

```env
# .env
VITE_API_URL=https://harmonylab-wmrla7fhwa-uc.a.run.app
```

---

## Definition of Done (UI)

- [ ] All pages render without errors
- [ ] All API integrations working
- [ ] Chord grid displays correctly on mobile and desktop
- [ ] Playback controls functional with Tone.js
- [ ] Quiz flow complete (setup → questions → results)
- [ ] Import flow complete (upload → preview → save)
- [ ] Progress page shows accurate data
- [ ] Keyboard navigation works for quiz
- [ ] No console errors in production build
- [ ] Help link points to USER_GUIDE.md on GitHub

---

**Document Version**: 1.0  
**Next**: VS Code AI implements per this specification  
**Testing**: See TEST_PLAN.md for UI test requirements
