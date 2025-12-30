# HarmonyLab TEST_PLAN.md

**Project**: HarmonyLab  
**Version**: 1.0  
**Last Updated**: 2025-12-28  
**Author**: Claude (Architect)  
**Status**: Sprint 1 Deliverable - Ready for VS Code AI Implementation

---

## Testing Philosophy

> **If it's in the requirements or user documentation, it MUST be tested.**

| Category | What to Test |
|----------|--------------|
| Happy Path | Every documented feature works as described |
| Obvious Exceptions | User-friendly error messages for common mistakes |

**Key Principle**: VS Code AI implements ALL automated tests. Zero manual testing by Project Lead. Deliverables arrive fully tested.

---

## Test Environment

### Cloud-First Testing

**DO NOT test against localhost.** All tests run against the Cloud Run deployment.

```
API Base URL: https://harmonylab-wmrla7fhwa-uc.a.run.app
API Docs: https://harmonylab-wmrla7fhwa-uc.a.run.app/docs
```

### Local Test Execution

```powershell
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html --cov-fail-under=70

# Run specific test file
pytest tests/test_songs.py -v

# Run specific test
pytest tests/test_songs.py::test_get_all_songs -v
```

### CI Testing

Tests run automatically in GitHub Actions on every push to main.

**Coverage threshold**: 70% (enforced in CI - deployment fails if not met)

---

## Test Categories

### 1. API Endpoint Tests

#### 1.1 Health Check

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_health_check` | `/health` | GET | 200, `{"status": "healthy", "database": "connected"}` |

#### 1.2 Songs API

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_get_all_songs` | `/api/songs` | GET | 200, list of songs |
| `test_get_song_by_id` | `/api/songs/{id}` | GET | 200, single song with metadata |
| `test_get_song_not_found` | `/api/songs/99999` | GET | 404, "Song not found" |
| `test_create_song` | `/api/songs` | POST | 201, created song with id |
| `test_create_song_invalid` | `/api/songs` | POST | 422, validation error |
| `test_update_song` | `/api/songs/{id}` | PUT | 200, updated song |
| `test_delete_song` | `/api/songs/{id}` | DELETE | 204, no content |
| `test_get_song_progression` | `/api/songs/{id}/progression` | GET | 200, full chord progression |

#### 1.3 Sections API

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_get_song_sections` | `/api/songs/{id}/sections` | GET | 200, list of sections |
| `test_create_section` | `/api/sections` | POST | 201, created section |
| `test_update_section` | `/api/sections/{id}` | PUT | 200, updated section |
| `test_delete_section` | `/api/sections/{id}` | DELETE | 204, no content |

#### 1.4 Measures API

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_get_section_measures` | `/api/sections/{id}/measures` | GET | 200, list of measures |
| `test_create_measure` | `/api/measures` | POST | 201, created measure |
| `test_get_measure_with_chords` | `/api/measures/{id}` | GET | 200, measure with chords |

#### 1.5 Chords API

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_get_measure_chords` | `/api/measures/{id}/chords` | GET | 200, list of chords |
| `test_create_chord` | `/api/chords` | POST | 201, created chord |
| `test_create_chords_bulk` | `/api/measures/{id}/chords/bulk` | POST | 201, created chords |
| `test_update_chord` | `/api/chords/{id}` | PUT | 200, updated chord |
| `test_delete_chord` | `/api/chords/{id}` | DELETE | 204, no content |

#### 1.6 Vocabulary API

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_get_chord_vocabulary` | `/api/vocabulary/chords` | GET | 200, 30+ chord types |
| `test_get_roman_numeral_vocabulary` | `/api/vocabulary/roman-numerals` | GET | 200, 50+ roman numerals |
| `test_vocabulary_has_maj7` | `/api/vocabulary/chords` | GET | Contains "Maj7" |
| `test_vocabulary_has_aliases` | `/api/vocabulary/chords` | GET | Aliases populated |

#### 1.7 Quiz API

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_generate_quiz` | `/api/quiz/generate/{song_id}` | POST | 200, quiz with blanks |
| `test_generate_quiz_with_difficulty` | `/api/quiz/generate/{song_id}?blank_percent=40` | POST | 200, ~40% blanks |
| `test_submit_quiz` | `/api/quiz/submit` | POST | 200, score and results |
| `test_submit_quiz_all_correct` | `/api/quiz/submit` | POST | 200, 100% score |
| `test_submit_quiz_all_wrong` | `/api/quiz/submit` | POST | 200, 0% score |
| `test_get_quiz_attempts` | `/api/quiz/attempts` | GET | 200, list of attempts |
| `test_get_quiz_attempt_by_id` | `/api/quiz/attempts/{id}` | GET | 200, attempt details |

#### 1.8 Progress API

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_get_all_progress` | `/api/progress` | GET | 200, list of progress records |
| `test_get_song_progress` | `/api/progress/song/{song_id}` | GET | 200, progress for song |
| `test_update_progress` | `/api/progress/song/{song_id}` | POST | 200, updated progress |
| `test_get_progress_stats` | `/api/progress/stats` | GET | 200, aggregate stats |

#### 1.9 Import API

| Test | Endpoint | Method | Expected |
|------|----------|--------|----------|
| `test_upload_midi` | `/api/imports/midi` | POST | 200, parsed chord data |
| `test_upload_invalid_file` | `/api/imports/midi` | POST | 400, "Invalid MIDI file" |
| `test_preview_import` | `/api/imports/preview` | POST | 200, preview with flags |
| `test_confirm_import` | `/api/imports/confirm` | POST | 201, song created |

---

### 2. Error Handling Tests

#### Error Message Quality Standards

```python
# ❌ BAD - Technical error exposed
{"detail": "NoneType has no attribute 'id'"}

# ✅ GOOD - User-friendly message
{"detail": "Song not found. It may have been deleted."}
```

| Test | Scenario | Expected Status | Expected Message |
|------|----------|-----------------|------------------|
| `test_song_not_found` | GET `/api/songs/99999` | 404 | "Song not found" |
| `test_section_not_found` | GET `/api/sections/99999` | 404 | "Section not found" |
| `test_measure_not_found` | GET `/api/measures/99999` | 404 | "Measure not found" |
| `test_chord_not_found` | GET `/api/chords/99999` | 404 | "Chord not found" |
| `test_quiz_song_no_chords` | POST `/api/quiz/generate/{empty_song}` | 400 | "Song has no chords to quiz" |
| `test_invalid_chord_symbol` | POST `/api/chords` with "XYZ123" | 422 | "Invalid chord symbol" |
| `test_invalid_roman_numeral` | POST `/api/chords` with "XIV7" | 422 | "Invalid roman numeral" |
| `test_empty_song_title` | POST `/api/songs` with "" title | 422 | "Title is required" |
| `test_duplicate_measure_number` | POST duplicate measure | 409 | "Measure already exists" |

---

### 3. Integration Tests

| Test | Service | Scenario | Expected |
|------|---------|----------|----------|
| `test_database_connection` | Cloud SQL | Health check returns DB status | `"database": "connected"` |
| `test_full_song_workflow` | All | Create song → sections → measures → chords → quiz | Complete workflow succeeds |
| `test_import_to_quiz_workflow` | All | Import MIDI → Generate quiz → Submit answers | Complete workflow succeeds |

---

### 4. Frontend Component Tests

#### 4.1 Song Library (Home Page)

| Test | Component | Scenario | Expected |
|------|-----------|----------|----------|
| `test_song_list_renders` | `SongList` | Load page | Shows list of songs |
| `test_song_list_empty` | `SongList` | No songs in DB | Shows "No songs yet" message |
| `test_search_filters_songs` | `SearchBar` | Type "Ipanema" | Only matching songs shown |
| `test_genre_filter` | `GenreFilter` | Select "Bossa Nova" | Only bossa nova songs shown |
| `test_click_song_navigates` | `SongCard` | Click song | Navigate to `/songs/{id}` |

#### 4.2 Song Detail Page

| Test | Component | Scenario | Expected |
|------|-----------|----------|----------|
| `test_song_detail_renders` | `SongDetail` | Load page | Shows song metadata |
| `test_chord_grid_displays` | `ChordGrid` | Load page | Shows 4-column chord grid |
| `test_transpose_up` | `TransposeControl` | Click + | All chords shift up semitone |
| `test_transpose_down` | `TransposeControl` | Click - | All chords shift down semitone |
| `test_playback_starts` | `PlaybackControls` | Click Play | Audio starts, chord highlights |
| `test_playback_stops` | `PlaybackControls` | Click Pause | Audio stops |
| `test_tempo_adjust` | `PlaybackControls` | Drag tempo slider | Playback speed changes |

#### 4.3 Quiz Interface

| Test | Component | Scenario | Expected |
|------|-----------|----------|----------|
| `test_quiz_setup_renders` | `QuizSetup` | Load page | Shows mode/section options |
| `test_quiz_grid_shows_blanks` | `QuizGrid` | Start quiz | Some cells show "?" |
| `test_chord_picker_selects` | `ChordPicker` | Select root + quality | Preview shows combined symbol |
| `test_submit_correct_answer` | `QuizInterface` | Submit correct chord | Green feedback, next question |
| `test_submit_wrong_answer` | `QuizInterface` | Submit wrong chord | Red feedback, show correct |
| `test_skip_question` | `QuizInterface` | Click Skip | Move to next, count as wrong |
| `test_quiz_completion` | `QuizResults` | Answer all questions | Show score summary |
| `test_hear_chord_plays` | `QuizControls` | Click "Hear Chord" | Audio plays correct chord |

#### 4.4 Progress Dashboard

| Test | Component | Scenario | Expected |
|------|-----------|----------|----------|
| `test_stats_cards_render` | `StatsCards` | Load page | Shows 4 stat cards |
| `test_recent_activity_shows` | `RecentActivity` | Has quiz history | Shows recent attempts |
| `test_mastery_tiers_groups` | `MasteryTiers` | Has songs | Songs grouped by mastery |

#### 4.5 Import Page

| Test | Component | Scenario | Expected |
|------|-----------|----------|----------|
| `test_file_drop_zone` | `FileDropZone` | Drag MIDI file | File accepted, preview shown |
| `test_reject_non_midi` | `FileDropZone` | Drag .txt file | Error "Only MIDI files accepted" |
| `test_preview_shows_chords` | `ImportPreview` | Valid MIDI | Chord grid displayed |
| `test_flagged_chords_highlighted` | `ImportPreview` | Low confidence chords | Yellow highlight on flags |
| `test_save_creates_song` | `ImportActions` | Click Save | Song created, redirect to detail |

---

### 5. Playback Tests (Tone.js)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_piano_sampler_loads` | Initialize audio | No errors, sampler ready |
| `test_play_single_chord` | Click chord cell | Chord audio plays |
| `test_play_progression` | Click Play | Chords play in sequence |
| `test_tempo_affects_speed` | Set tempo 50% | Playback half speed |
| `test_visual_sync` | Play progression | Current chord highlights yellow |
| `test_loop_section` | Enable loop | Section repeats |

---

### 6. Keyboard Navigation Tests

| Test | Key | Context | Expected |
|------|-----|---------|----------|
| `test_tab_navigation` | Tab | Any page | Focus moves through interactive elements |
| `test_enter_submits` | Enter | Quiz answer | Submits current answer |
| `test_space_plays` | Space | Song detail | Toggle play/pause |
| `test_arrow_keys_grid` | ←→↑↓ | Chord grid | Navigate between cells |
| `test_escape_closes` | Escape | Modal open | Modal closes |

---

## Test Data

### Fixtures

```python
# tests/conftest.py

import pytest
from httpx import AsyncClient

API_URL = "https://harmonylab-wmrla7fhwa-uc.a.run.app"

@pytest.fixture
def api_client():
    return AsyncClient(base_url=API_URL)

@pytest.fixture
def sample_song():
    return {
        "title": "Test Song",
        "composer": "Test Composer",
        "key_signature": "C",
        "tempo": 120,
        "time_signature": "4/4",
        "genre": "Test"
    }

@pytest.fixture
def sample_section():
    return {
        "song_id": 1,
        "name": "A",
        "section_order": 1,
        "repeat_count": 1
    }

@pytest.fixture
def sample_chord():
    return {
        "measure_id": 1,
        "beat_position": 1.0,
        "chord_symbol": "Cmaj7",
        "roman_numeral": "IMaj7",
        "chord_order": 1
    }

@pytest.fixture
def sample_quiz_submission():
    return {
        "quiz_id": 1,
        "answers": ["Cmaj7", "Dm7", "G7", "Cmaj7"]
    }
```

### Test Database Strategy

- **DO NOT use a separate test database**
- Tests run against production Cloud SQL
- Tests create test data with identifiable names (prefix: "TEST_")
- Tests clean up after themselves (delete TEST_ records)
- Use transactions where possible for rollback

---

## Coverage Requirements

### Minimum Coverage: 70%

```yaml
# In GitHub Actions
pytest --cov=app --cov-report=xml --cov-fail-under=70
```

### Coverage by Module

| Module | Minimum |
|--------|---------|
| `app/api/routes/songs.py` | 80% |
| `app/api/routes/quiz.py` | 80% |
| `app/api/routes/progress.py` | 70% |
| `app/api/routes/imports.py` | 70% |
| `app/services/midi_parser.py` | 75% |
| `app/db/connection.py` | 60% |

### Coverage Exclusions

```python
# In pyproject.toml
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/__init__.py",
    "*/config/*",
]
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# Add to .github/workflows/deploy.yml BEFORE deploy step

- name: Install test dependencies
  run: pip install pytest pytest-cov pytest-asyncio httpx

- name: Run tests
  run: |
    pytest --cov=app --cov-report=xml --cov-fail-under=70
  env:
    API_URL: https://harmonylab-wmrla7fhwa-uc.a.run.app

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

### Test Gate

**Tests must pass before deployment proceeds.** If tests fail, deployment is blocked.

---

## Test File Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures, API client
├── test_health.py           # Health check tests
├── test_songs.py            # Songs API tests
├── test_sections.py         # Sections API tests
├── test_measures.py         # Measures API tests
├── test_chords.py           # Chords API tests
├── test_vocabulary.py       # Vocabulary API tests
├── test_quiz.py             # Quiz API tests
├── test_progress.py         # Progress API tests
├── test_imports.py          # Import API tests
├── test_error_handling.py   # Error message tests
├── test_integration.py      # End-to-end workflow tests
└── frontend/
    ├── __init__.py
    ├── test_song_list.py    # Song library component tests
    ├── test_song_detail.py  # Song detail component tests
    ├── test_quiz.py         # Quiz component tests
    ├── test_progress.py     # Progress component tests
    ├── test_import.py       # Import component tests
    └── test_playback.py     # Tone.js playback tests
```

---

## Traceability Matrix

Every feature in USER_GUIDE.md must have a corresponding test.

| USER_GUIDE Feature | Test(s) |
|--------------------|---------|
| Browse song library | `test_song_list_renders`, `test_search_filters_songs` |
| View chord progression | `test_chord_grid_displays`, `test_song_detail_renders` |
| Play progression audio | `test_playback_starts`, `test_play_progression` |
| Transpose chords | `test_transpose_up`, `test_transpose_down` |
| Take a quiz | `test_quiz_setup_renders`, `test_submit_correct_answer` |
| View quiz results | `test_quiz_completion` |
| Track progress | `test_stats_cards_render`, `test_mastery_tiers_groups` |
| Import MIDI file | `test_file_drop_zone`, `test_save_creates_song` |

---

## Definition of Done (Testing)

- [ ] All test files created per structure above
- [ ] All API endpoint tests passing
- [ ] All error handling tests passing
- [ ] All frontend component tests passing
- [ ] Integration tests passing
- [ ] Coverage ≥ 70% overall
- [ ] Coverage ≥ 80% for songs and quiz modules
- [ ] CI/CD pipeline runs tests before deploy
- [ ] No console errors in test output
- [ ] Test cleanup removes TEST_ data

---

**Document Version**: 1.0  
**Companion Documents**: UI_DESIGN.md, USER_GUIDE.md  
**Implementation**: VS Code AI creates all tests per this specification
