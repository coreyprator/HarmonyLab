# Harmony Lab - Development Roadmap

Based on the project kickoff document and current setup status.

## ✅ Phase 0: Foundation (COMPLETE)

- [x] Virtual environment setup (C:\venvs\Harmony-Lab)
- [x] Project structure created
- [x] Core dependencies installed
- [x] Database connection layer
- [x] Pydantic models for all entities
- [x] Basic API routes (songs, sections, vocabulary)
- [x] FastAPI app with CORS
- [x] Configuration management

## 🔄 Phase 1: Core CRUD & Database (Sprint 1)

**Priority: High** | **Estimated Time: 1-2 weeks**

### Database Setup
- [ ] Create Cloud SQL instance or add HarmonyLab database to existing instance
- [ ] Execute schema (HarmonyLab-Schema-v1.0.sql)
- [ ] Verify seed data (ChordVocabulary, RomanNumeralVocabulary)
- [ ] Test connection from local machine

### Complete CRUD Routes
- [ ] `app/api/routes/measures.py` - Measure operations
- [ ] `app/api/routes/chords.py` - Chord operations
- [ ] Update health check endpoint to test DB connectivity
- [ ] Add error handling middleware

### Manual Data Entry Testing
- [ ] Create test song manually via API
- [ ] Add sections, measures, chords via API
- [ ] Test full progression retrieval
- [ ] Validate data integrity

**Deliverable**: Ability to manually enter a complete song progression

---

## 📥 Phase 2: File Import (Sprint 2-3)

**Priority: High** | **Estimated Time: 2-3 weeks**

### MIDI Parser
- [ ] `app/services/midi_parser.py`
  - [ ] Extract tempo, time signature, key
  - [ ] Separate melody track from harmony
  - [ ] Detect chord voicings
  - [ ] Map MIDI notes to chord symbols
  - [ ] Preserve timing (critical for syncopation)

### MusicXML Parser
- [ ] `app/services/musicxml_parser.py`
  - [ ] Parse .mxl and .xml files using music21
  - [ ] Extract chord symbols (if annotated)
  - [ ] Extract melody notes
  - [ ] Handle repeat signs and sections

### Chord Detection Service
- [ ] `app/services/chord_detection.py`
  - [ ] Map pitch sets to chord symbols
  - [ ] Handle inversions
  - [ ] Detect extensions (9ths, 11ths, 13ths)
  - [ ] Flag ambiguous chords for review

### Import Routes
- [ ] `app/api/routes/imports.py`
  - [ ] POST /import/midi - Upload and parse MIDI
  - [ ] POST /import/musicxml - Upload and parse MusicXML
  - [ ] GET /import/preview/{id} - Review parsed data
  - [ ] POST /import/save/{id} - Confirm and save to database

### File Storage
- [ ] Configure Cloud Storage bucket (or local temp storage)
- [ ] Upload handling with python-multipart
- [ ] File validation (size limits, formats)

**Deliverable**: Import 5 test songs from MIDI/MusicXML

---

## 🎵 Phase 3: Playback System (Sprint 4)

**Priority: High** | **Estimated Time: 1-2 weeks**

### Frontend Foundation
- [ ] Create `frontend/` directory
- [ ] Basic HTML/CSS structure
- [ ] Vanilla JavaScript setup (no frameworks)

### Tone.js Integration
- [ ] Install Tone.js via CDN or npm
- [ ] Create `frontend/js/playback.js`
- [ ] Piano synth for chords
- [ ] Lead synth for melody
- [ ] Transport controls (play, pause, stop)

### Playback API
- [ ] `app/api/routes/playback.py`
  - [ ] GET /playback/{song_id}/data - Full song data for Tone.js
  - [ ] POST /playback/{song_id}/transpose - Transpose by N semitones

### UI Components
- [ ] Song selection dropdown
- [ ] Play/pause/stop buttons
- [ ] Tempo slider
- [ ] Section selector
- [ ] Current position indicator
- [ ] Chord chart display with highlighting

**Deliverable**: Play back any imported song with melody and harmony

---

## 🎯 Phase 4: Quiz System (Sprint 5-6)

**Priority: Medium** | **Estimated Time: 2-3 weeks**

### Quiz Generation
- [ ] `app/services/quiz_generator.py`
  - [ ] Sequential quiz ("what comes next")
  - [ ] Fill-in-the-blank quiz
  - [ ] Distractor generation (plausible wrong answers)
  - [ ] Difficulty levels

### Quiz Routes
- [ ] `app/api/routes/quiz.py`
  - [ ] POST /quiz/start - Initialize quiz session
  - [ ] POST /quiz/answer - Submit answer
  - [ ] GET /quiz/results/{attempt_id} - View results
  - [ ] GET /quiz/history - User's quiz history

### Quiz UI
- [ ] Quiz mode selector (sequential, fill-blank)
- [ ] Question display
- [ ] Answer input (dropdowns from vocabulary)
- [ ] Immediate feedback
- [ ] Progress tracking
- [ ] Results summary

**Deliverable**: Interactive quiz system for any song

---

## 📊 Phase 5: Progress Tracking (Sprint 7)

**Priority: Medium** | **Estimated Time: 1 week**

### Progress Routes
- [ ] `app/api/routes/progress.py`
  - [ ] GET /progress/songs - All songs with progress
  - [ ] GET /progress/songs/{song_id} - Detailed progress
  - [ ] POST /progress/practice/{song_id} - Log practice session
  - [ ] GET /progress/stats - Overall statistics

### Progress UI
- [ ] Dashboard showing all songs
- [ ] Mastery level indicators (0-5 scale)
- [ ] Last practiced dates
- [ ] Accuracy rates
- [ ] Suggested practice list (spaced repetition)

**Deliverable**: User can track learning progress

---

## 🎨 Phase 6: UI Polish & Mobile (Sprint 8)

**Priority: Low** | **Estimated Time: 1-2 weeks**

### UI Improvements
- [ ] Mobile-responsive design
- [ ] Touch-friendly controls
- [ ] Swipe navigation
- [ ] Improved chord chart visualization
- [ ] Section looping for practice
- [ ] Comments/annotations per chord

### Offline Support
- [ ] IndexedDB for offline quiz mode
- [ ] Service worker for PWA
- [ ] Sync when back online

**Deliverable**: Polished, mobile-friendly interface

---

## 🚀 Phase 7: Deployment (Sprint 9)

**Priority: Medium** | **Estimated Time: 1 week**

### GCP Deployment
- [ ] Follow `harmony-lab-infra-setup.md`
- [ ] Create Cloud Run service
- [ ] Configure Cloud SQL connection
- [ ] Set up Cloud Storage
- [ ] Secret Manager for credentials
- [ ] CI/CD with Cloud Build

### Testing
- [ ] Integration tests
- [ ] End-to-end tests
- [ ] Performance testing
- [ ] Security review

**Deliverable**: Live production deployment

---

## 📚 Phase 8: Data Population (Sprint 10)

**Priority: Medium** | **Estimated Time: 2-3 weeks**

### Import Song Repertoire
Import all 37 songs from your repertoire:
- [ ] Find/acquire MIDI or MusicXML files
- [ ] Import via API
- [ ] Review and enrich data:
  - [ ] Add roman numerals
  - [ ] Add key centers
  - [ ] Add function labels
  - [ ] Add comments/explanations
- [ ] Verify playback quality
- [ ] Test quiz generation

**Deliverable**: Complete database of 37 songs ready for practice

---

## 🔮 Future Enhancements (Backlog)

### Advanced Features
- [ ] Real Book measure number references
- [ ] Collaborative features (share songs)
- [ ] Audio recording/playback of user performance
- [ ] Machine learning for personalized recommendations
- [ ] Social features (leaderboards, challenges)
- [ ] Integration with external services (Spotify, YouTube)

### Alternative Input Methods
- [ ] Sheet music OCR (if AI improves)
- [ ] Manual entry wizard UI
- [ ] Batch import tools

### Advanced Playback
- [ ] Multiple instrument sounds
- [ ] Backing track generation
- [ ] Click track/metronome
- [ ] Loop sections with count-in

---

## Current Status

**Phase**: 0 Complete, Phase 1 In Progress
**Next Immediate Steps**:
1. Configure database connection (.env file)
2. Run schema on Cloud SQL
3. Test API locally
4. Complete measures and chords routes

---

## Time Estimates

| Phase | Estimated Time | Priority |
|-------|---------------|----------|
| Phase 0: Foundation | ✅ Complete | - |
| Phase 1: Core CRUD | 1-2 weeks | High |
| Phase 2: File Import | 2-3 weeks | High |
| Phase 3: Playback | 1-2 weeks | High |
| Phase 4: Quiz System | 2-3 weeks | Medium |
| Phase 5: Progress | 1 week | Medium |
| Phase 6: UI Polish | 1-2 weeks | Low |
| Phase 7: Deployment | 1 week | Medium |
| Phase 8: Data Population | 2-3 weeks | Medium |
| **Total Core Features** | **9-16 weeks** | - |

---

*This roadmap follows the sprint-based methodology from Super-Flashcards project.*
*Update this document as phases complete and priorities shift.*
