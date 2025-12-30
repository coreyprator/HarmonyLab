# HarmonyLab User Guide

**Version**: 1.0  
**Last Updated**: 2025-12-28

---

## Welcome to HarmonyLab

HarmonyLab is a practice tool for jazz musicians who want to memorize chord progressions. Instead of staring at lead sheets, you'll learn through interactive quizzes that test your recall of harmonic progressions.

**Who is this for?**
- Jazz pianists learning standards
- Musicians preparing for jam sessions
- Anyone who wants to internalize chord changes

**What you'll learn:**
- Chord symbols (Cmaj7, Dm7, G7, etc.)
- Roman numeral analysis (IMaj7, ii7, V7, etc.)
- Song structures (A sections, B sections, bridges)

---

## Quick Start

### 1. Browse Your Song Library

When you open HarmonyLab, you'll see your song library. Each song shows:
- Title and composer
- Genre (Bossa Nova, Standard, Latin, etc.)
- Your mastery level (★ to ★★★★★)

**To find a song:**
- Type in the search box to filter by title
- Use the genre dropdown to show only certain styles

### 2. View a Chord Progression

Click any song to see its chord progression displayed as a grid:

```
┌────────┬────────┬────────┬────────┐
│ FMaj7  │ FMaj7  │ G7     │ G7     │
├────────┼────────┼────────┼────────┤
│ Gm7    │ Gb7    │ FMaj7  │ Gb7    │
└────────┴────────┴────────┴────────┘
```

- Each row shows 4 measures
- Sections (A, B, Bridge) are labeled
- Click any chord to hear how it sounds

### 3. Listen to the Progression

Press the **▶ Play** button to hear the chords played in sequence:
- The current chord highlights in yellow as it plays
- Adjust the tempo slider to speed up or slow down
- Click the loop button to repeat a section

### 4. Test Yourself with a Quiz

Click **Start Quiz** to practice:
1. Choose your quiz mode:
   - **Fill-in-Blank**: Random chords are hidden, fill them in
   - **Sequential**: "What chord comes next?"
2. Select which section to practice (or whole song)
3. Set difficulty (how many blanks)

During the quiz:
- Select the root note (C, D, E, etc.)
- Select the chord quality (Maj7, m7, 7, etc.)
- Click **Submit** or press Enter
- Click **Hear Chord** if you need a hint

### 5. Track Your Progress

Visit the **Progress** page to see:
- How many songs you've practiced
- Your average quiz scores
- Songs grouped by mastery level

---

## Features

### Chord Progression Display

The chord grid shows your song's harmony in a simple text format:

- **4 measures per row** — Standard lead sheet layout
- **Section labels** — A, B, Bridge, Coda, etc.
- **Beat position** — Multiple chords per measure shown with beat numbers
- **Roman numerals** — Hover over any chord to see its function (IMaj7, ii7, V7)

#### Transpose

Need to practice in a different key? Use the transpose controls:
- Click **+** to shift everything up a half step
- Click **−** to shift everything down
- The key signature updates automatically

### Audio Playback

HarmonyLab plays chord voicings using a piano sound:

| Control | Function |
|---------|----------|
| ▶ Play | Start/resume playback |
| ⏸ Pause | Stop playback |
| ◀◀ | Return to beginning |
| Tempo slider | 50% to 150% of original tempo |
| 🔊 Volume | Adjust playback volume |
| 🔁 Loop | Repeat current section |

**Tip**: Click any chord cell to hear just that chord.

### Quiz Modes

#### Fill-in-Blank Mode

Random chords are replaced with **[?]**. Your job is to fill them in.

- Easier: 20% blanks
- Medium: 40% blanks  
- Harder: 60% blanks

#### Sequential Mode

You see the progression up to a point, then answer: "What comes next?"

Good for learning the flow of a song.

### Chord Picker

When answering quiz questions, use the chord picker:

1. **Select root**: C, C#/Db, D, D#/Eb, E, F, F#/Gb, G, G#/Ab, A, A#/Bb, B
2. **Select quality**: Maj7, m7, 7, ø7, dim7, m9, Maj9, 9, 6, m6, sus4, aug...

The preview shows your combined answer (e.g., "FMaj7") before you submit.

**Keyboard shortcuts:**
- Numbers 1-9 for common roots
- Enter to submit
- Tab to move between root and quality

### Progress Tracking

HarmonyLab remembers your practice history:

- **Times practiced** — How often you've quizzed on each song
- **Accuracy rate** — Your average score
- **Mastery level** — Stars based on your consistency

| Stars | Meaning |
|-------|---------|
| ★☆☆☆☆ | New — Haven't practiced yet |
| ★★☆☆☆ | Beginner — Still learning |
| ★★★☆☆ | Intermediate — Getting it |
| ★★★★☆ | Advanced — Almost there |
| ★★★★★ | Mastered — You know this cold |

### Import Songs

Add your own songs by importing MIDI files:

1. Click **Import** in the header
2. Drag a MIDI file onto the upload area (or click to browse)
3. Review the detected chords
4. Edit metadata (title, composer, genre, key)
5. Fix any flagged chords (shown in yellow)
6. Click **Save Song**

**Supported formats:**
- .mid (Standard MIDI File)
- .midi

**Tips for good imports:**
- Export from notation software (MuseScore, Finale, Sibelius)
- Use a dedicated chord track
- Commit groove/swing before exporting

---

## Workflows

### Daily Practice Routine

1. Open HarmonyLab
2. Go to **Progress** → Find songs at ★★★☆☆ level
3. Practice those songs first (they need reinforcement)
4. Then try a new song or one you've mastered
5. End with something fun you know well

### Learning a New Song

1. **Import** the MIDI or find it in your library
2. **Listen** through the whole progression 2-3 times
3. **Study** the A section — note patterns, ii-V-I's
4. **Quiz** the A section at 20% difficulty
5. Increase difficulty as you improve
6. Move to B section, then full song

### Preparing for a Gig

1. Filter your library by songs on the setlist
2. Quiz each song at 60% difficulty
3. Any score below 80%? Practice that song more
4. Listen to full playback while visualizing the tune

---

## Troubleshooting

### Audio not playing

- **Check your browser**: Make sure audio is not muted
- **Click somewhere first**: Browsers require a user interaction before playing audio
- **Try refreshing**: The audio engine may need to reinitialize

### Quiz won't generate

- **Song needs chords**: Make sure the song has chord data
- **Check the section**: Does the selected section have measures?

### Import doesn't detect chords

- **Wrong track**: The MIDI might have melody, not chords
- **Monophonic**: Need at least 3 notes at once for chord detection
- **Try another file**: Some MIDI files don't have useful chord data

### Progress not saving

- **Check your connection**: Progress saves to the cloud
- **Refresh the page**: Should sync automatically

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play/Pause audio |
| Enter | Submit quiz answer |
| Tab | Move to next element |
| Escape | Close modal/dialog |
| ← → | Navigate chord grid |
| 1-9 | Quick-select root note (C, D, E...) |

---

## Glossary

| Term | Definition |
|------|------------|
| **Chord symbol** | Letter notation like Cmaj7, Dm7, G7 |
| **Roman numeral** | Function notation like IMaj7, ii7, V7 |
| **Section** | A part of a song (A, B, Bridge, Coda) |
| **Measure** | A bar of music (usually 4 beats) |
| **Beat position** | Where in the measure a chord occurs (1, 2, 3, 4) |
| **Mastery level** | Your proficiency rating (1-5 stars) |
| **Transpose** | Shift all chords up or down by semitones |
| **ii-V-I** | The most common jazz chord progression |

---

## Getting Help

- **In-app help**: Click the **?** icon in the header
- **Documentation**: You're reading it!
- **Report issues**: [GitHub Issues](https://github.com/coreyprator/HarmonyLab/issues)

---

## About

HarmonyLab was built for jazz musicians who learn best by doing. Instead of passively reading chord charts, you actively recall the harmonies — which is how memory actually works.

**Built with:**
- React + Tailwind CSS (frontend)
- FastAPI + Cloud SQL (backend)
- Tone.js (audio playback)
- Google Cloud Run (hosting)

---

**Happy practicing! 🎹**
