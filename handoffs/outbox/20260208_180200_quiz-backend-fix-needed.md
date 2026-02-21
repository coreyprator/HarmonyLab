# [HarmonyLab] 🔵 Quiz Regression - Backend Fix Required

> **From**: Claude Code (Command Center)
> **To**: Claude.ai (Architect)
> **Project**: HarmonyLab
> **Task**: Quiz regression investigation
> **Timestamp**: 2026-02-08T18:02:00Z
> **Status**: INVESTIGATION COMPLETE - BACKEND FIX NEEDED

---

## Summary

Investigated the quiz regression. The issue is NOT a frontend bug - it's a **backend API mismatch**.

---

## Error

```
Invalid question data at index 0
```

This error comes from the defensive coding I added - it catches the malformed question before crashing.

---

## Root Cause Analysis

### Frontend Expects (quiz.html lines 298-320)

```javascript
{
    "context": ["Dm7", "G7", "Cmaj7"],  // Preceding chords for display
    "options": ["Am7", "Dm7", "Fmaj7", "Bm7b5"],  // Multiple choice answers
    "correct_answer": "Am7"  // The right answer
}
```

### Backend Returns (quiz.py lines 74-82)

```python
{
    "chord_id": 123,
    "measure_number": 4,
    "beat_position": 1.0,
    "is_blank": True,
    "displayed_chord": None,
    "roman_numeral": "ii7",
    "key_center": "C"
}
```

### The Problem

The backend returns **raw chord data** but the frontend needs **fully-formed quiz questions** with:
- `context` - preceding chords for context
- `options` - multiple choice answer strings
- `correct_answer` - the correct chord symbol

---

## Fix Required (Backend)

The `/api/v1/quiz/generate` endpoint in `app/api/routes/quiz.py` needs to:

1. **Add context chords** - Get 2-3 preceding chords for each question
2. **Generate multiple choice options** - Create 4 plausible chord choices
3. **Package as proper questions** - Return structure frontend expects

### Example Fix Pattern

```python
def generate_quiz_question(chord, song_chords, song_key):
    # Get preceding chords for context
    context = get_preceding_chords(chord, song_chords, count=3)

    # Generate multiple choice options (including correct answer)
    correct = chord.chord_symbol
    distractors = generate_plausible_chords(chord, song_key, count=3)
    options = shuffle([correct] + distractors)

    return {
        "context": context,
        "options": options,
        "correct_answer": correct
    }
```

---

## Frontend Status

The frontend defensive coding is working correctly - it catches invalid questions instead of crashing with TypeError.

**Files already fixed:**
- `frontend/quiz.html` - Defensive checks (commit `9721cdc`)
- `frontend/song.html` - Fixed window.allChords (commit `90a7e9a`)
- `frontend/js/audio.js` - Fixed Salamander URL (commit `9721cdc`)

---

## Blocked By

Quiz testing is blocked until the backend `/api/v1/quiz/generate` endpoint returns proper question structure.

---

## Priority

HIGH - This blocks all quiz UAT testing.

---

## Next Steps

1. Update `app/api/routes/quiz.py` to transform raw chord data into quiz questions
2. Add `context`, `options`, `correct_answer` fields to question response
3. Deploy backend
4. Retest quiz

---

*Sent via Handoff Bridge per project-methodology policy*
*HarmonyLab/handoffs/outbox/20260208_180200_quiz-backend-fix-needed.md -> GCS backup*
