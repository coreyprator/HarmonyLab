# [HarmonyLab] 🔵 Sprint v1.4.0 — Quiz UI + Progress Dashboard

**Version**: 1.3.1 → 1.4.0  
**Date**: 2026-02-07  
**Status**: Ready for CC  
**Estimated Effort**: 12-16 hours  

---

## Overview

Build the frontend UI for Quiz and Progress features. The backend APIs already exist and are deployed (482+ lines of working code). This sprint focuses entirely on frontend development.

---

## Prerequisites

**Read First**:
- `CLAUDE.md`
- `HarmonyLab_LeadSheet_Analysis_Design.md`
- Existing API docs: https://harmonylab.rentyourcio.com/docs

**Backend Already Deployed**:
- Quiz endpoints: 282 lines in `app/routers/quiz.py`
- Progress endpoints: 242 lines in `app/routers/progress.py`

---

## Part A: Quiz UI

### A1. Quiz Page (`frontend/quiz.html`)

**New File** — Create quiz interface.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│ [Nav Bar]                              v1.4.0   │
├─────────────────────────────────────────────────┤
│                                                 │
│  Quiz Mode: [Sequential ▼]  Song: [Select ▼]   │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │                                         │   │
│  │     What chord comes next after:        │   │
│  │                                         │   │
│  │            Am7 → D7 → ?                 │   │
│  │                                         │   │
│  │   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │   │
│  │   │Gmaj7│ │ Em7 │ │Cmaj7│ │Bm7b5│      │   │
│  │   └─────┘ └─────┘ └─────┘ └─────┘      │   │
│  │                                         │   │
│  │     Question 3 of 10                    │   │
│  │     ████████░░░░░░░░░░░░  30%           │   │
│  │                                         │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  [End Quiz]                                     │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Features**:
1. **Quiz Mode Selector**:
   - Sequential (next chord in progression)
   - Fill-in-the-blank (random chord hidden)
   - Roman Numeral (identify function)

2. **Song Selector**:
   - Dropdown of all songs
   - Option: "Random from all songs"

3. **Question Display**:
   - Shows context (previous 2-3 chords)
   - Highlights the blank/question
   - 4 multiple choice options

4. **Progress Bar**:
   - Questions completed / total
   - Visual progress indicator

5. **Answer Feedback**:
   - Correct: Green highlight + brief celebration
   - Wrong: Red highlight + show correct answer
   - Auto-advance after 1.5 seconds

6. **End Quiz**:
   - Summary screen with score
   - Option to retry or return to songs

### A2. Quiz API Integration

**Existing Endpoints** (already deployed):

```
GET  /api/v1/quiz/songs/{song_id}/generate
     ?mode=sequential|fill_blank|roman_numeral
     &num_questions=10
     
POST /api/v1/quiz/submit
     {
       "song_id": 23,
       "question_index": 0,
       "user_answer": "Gmaj7",
       "correct_answer": "Gmaj7",
       "time_taken_ms": 2500
     }
     
GET  /api/v1/quiz/history
     ?song_id=23
     &limit=10
```

### A3. Quiz JavaScript (`frontend/js/quiz.js`)

**New File** — Quiz logic.

```javascript
// Key functions needed:
async function loadQuiz(songId, mode, numQuestions) { }
function displayQuestion(question, index, total) { }
function handleAnswer(selectedAnswer) { }
function showFeedback(isCorrect, correctAnswer) { }
async function submitAnswer(questionData) { }
function showResults(score, total, details) { }
```

### A4. Quiz Styles (`frontend/css/quiz.css`)

**New File** — Quiz-specific styles.

```css
/* Key classes needed */
.quiz-container { }
.quiz-question { }
.quiz-context { }
.quiz-options { }
.quiz-option { }
.quiz-option.selected { }
.quiz-option.correct { }
.quiz-option.wrong { }
.quiz-progress { }
.quiz-results { }
```

---

## Part B: Progress Dashboard

### B1. Progress Page (`frontend/progress.html`)

**New File** — Progress tracking interface.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│ [Nav Bar]                              v1.4.0   │
├─────────────────────────────────────────────────┤
│                                                 │
│  Your Progress                                  │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐    │
│  │  Songs Practiced │  │  Overall Accuracy │    │
│  │       12/37      │  │       78%         │    │
│  └──────────────────┘  └──────────────────┘    │
│                                                 │
│  ┌──────────────────┐  ┌──────────────────┐    │
│  │  Quiz Sessions   │  │  Current Streak   │    │
│  │       24         │  │     5 days        │    │
│  └──────────────────┘  └──────────────────┘    │
│                                                 │
│  Recent Activity                                │
│  ┌─────────────────────────────────────────┐   │
│  │ Today     Corcovado    Quiz    85%      │   │
│  │ Today     Blue Bossa   Quiz    90%      │   │
│  │ Yesterday Autumn Leaves Quiz   72%      │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Song Mastery                                   │
│  ┌─────────────────────────────────────────┐   │
│  │ Corcovado         ████████░░  80%  ⭐⭐⭐ │   │
│  │ Blue Bossa        ██████████  95%  ⭐⭐⭐⭐│   │
│  │ Girl from Ipanema ██████░░░░  60%  ⭐⭐   │   │
│  │ Autumn Leaves     ████░░░░░░  40%  ⭐    │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Features**:

1. **Summary Cards**:
   - Songs practiced (count / total)
   - Overall accuracy percentage
   - Total quiz sessions
   - Current streak (days in a row)

2. **Recent Activity**:
   - Last 10 quiz sessions
   - Date, song, type, score
   - Click to see detailed results

3. **Song Mastery**:
   - All songs with progress bars
   - Mastery level (1-5 stars)
   - Accuracy percentage
   - Sort by: mastery, accuracy, recent, alphabetical

4. **Mastery Levels**:
   - ⭐ Beginner (0-20%)
   - ⭐⭐ Learning (21-40%)
   - ⭐⭐⭐ Practicing (41-60%)
   - ⭐⭐⭐⭐ Proficient (61-80%)
   - ⭐⭐⭐⭐⭐ Mastered (81-100%)

### B2. Progress API Integration

**Existing Endpoints** (already deployed):

```
GET  /api/v1/progress/stats
     Returns: {
       "songs_practiced": 12,
       "total_songs": 37,
       "overall_accuracy": 78.5,
       "quiz_sessions": 24,
       "current_streak": 5
     }

GET  /api/v1/progress/songs
     Returns: [
       {
         "song_id": 23,
         "title": "Corcovado",
         "times_practiced": 8,
         "accuracy": 80.0,
         "mastery_level": 3,
         "last_practiced": "2026-02-07T..."
       },
       ...
     ]

GET  /api/v1/progress/history
     ?limit=10
     Returns: [
       {
         "date": "2026-02-07T...",
         "song_title": "Corcovado",
         "quiz_type": "sequential",
         "score": 85,
         "questions": 10
       },
       ...
     ]
```

### B3. Progress JavaScript (`frontend/js/progress.js`)

**New File** — Progress logic.

```javascript
// Key functions needed:
async function loadStats() { }
async function loadSongProgress() { }
async function loadRecentHistory() { }
function renderSummaryCards(stats) { }
function renderRecentActivity(history) { }
function renderSongMastery(songs) { }
function getMasteryStars(level) { }
function sortSongs(songs, sortBy) { }
```

### B4. Progress Styles (`frontend/css/progress.css`)

**New File** — Progress-specific styles.

```css
/* Key classes needed */
.progress-container { }
.summary-cards { }
.summary-card { }
.recent-activity { }
.activity-item { }
.song-mastery { }
.mastery-item { }
.mastery-bar { }
.mastery-stars { }
```

---

## Part C: Navigation Updates

### C1. Enable Nav Links

**Update**: `frontend/index.html` and `frontend/song.html`

Change disabled links to active:

```html
<!-- Before -->
<a href="#" class="nav-link disabled" title="Coming in v1.4.0">Quiz</a>
<a href="#" class="nav-link disabled" title="Coming in v1.4.0">Progress</a>

<!-- After -->
<a href="quiz.html" class="nav-link">Quiz</a>
<a href="progress.html" class="nav-link">Progress</a>
```

### C2. Add Nav to New Pages

Both `quiz.html` and `progress.html` need the same nav bar:

```html
<nav class="nav-bar">
    <a href="index.html" class="nav-link">Songs</a>
    <a href="quiz.html" class="nav-link">Quiz</a>
    <a href="progress.html" class="nav-link">Progress</a>
    <span class="version-badge">v1.4.0</span>
</nav>
```

---

## Part D: Version Bump

Update to **v1.4.0** in:
- `app/main.py` or `app/config.py`
- `frontend/index.html`
- `frontend/song.html`
- `frontend/quiz.html` (new)
- `frontend/progress.html` (new)

---

## Testing Requirements

### Quiz Tests

| Test | Expected |
|------|----------|
| Load quiz page | No errors |
| Select song + mode | Quiz generates |
| Answer question correctly | Green feedback, score +1 |
| Answer question wrong | Red feedback, shows correct |
| Complete quiz | Results screen with score |
| Retry quiz | New questions generated |

### Progress Tests

| Test | Expected |
|------|----------|
| Load progress page | Stats display |
| Summary cards | Show accurate counts |
| Recent activity | Shows last 10 sessions |
| Song mastery | Shows all songs with bars |
| Sort mastery | Sorts correctly |
| Click song | Links to song detail |

### Integration Tests

| Test | Expected |
|------|----------|
| Complete quiz → Progress updates | New session appears |
| Multiple quizzes → Accuracy changes | Stats recalculate |
| Nav links work | All pages accessible |

---

## Files to Create/Modify

### New Files (4)
- `frontend/quiz.html`
- `frontend/progress.html`
- `frontend/js/quiz.js`
- `frontend/js/progress.js`

### Modified Files (4)
- `frontend/index.html` — Enable nav links
- `frontend/song.html` — Enable nav links
- `frontend/styles.css` — Add quiz/progress styles (or separate CSS files)
- `app/main.py` or `app/config.py` — Version bump

---

## Do NOT Implement

- Audio playback (v1.5.0)
- Spaced repetition algorithm
- Social features / leaderboards
- Export quiz results
- Timed quiz mode

---

## Acceptance Criteria

### Quiz
- [ ] Quiz page loads without error
- [ ] Can select song and mode
- [ ] Questions display with 4 options
- [ ] Correct/wrong feedback works
- [ ] Progress bar updates
- [ ] Results screen shows score
- [ ] Quiz submits to API
- [ ] Can retry or return to songs

### Progress
- [ ] Progress page loads without error
- [ ] Summary cards show stats
- [ ] Recent activity shows history
- [ ] Song mastery shows all songs
- [ ] Mastery bars reflect accuracy
- [ ] Stars reflect mastery level
- [ ] Sorting works
- [ ] Links work

### Navigation
- [ ] Quiz link enabled in nav
- [ ] Progress link enabled in nav
- [ ] All pages have consistent nav
- [ ] Version shows v1.4.0

---

## Deployment

1. Create new frontend files
2. Update existing files
3. Bump version
4. Deploy frontend
5. Verify all pages load
6. Test quiz flow end-to-end
7. Test progress displays correctly
8. Create handoff with completion report

---

*Sprint spec created by Claude.ai (Architect)*
*Ready for CC implementation*
