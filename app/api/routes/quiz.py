"""
API routes for quiz generation and submission.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
import random
import json
from app.models import QuizQuestion, QuizGenerate, QuizSubmission, QuizResult, QuizAttempt
from app.db.connection import DatabaseConnection
from config.settings import Settings

router = APIRouter(prefix="/api/v1/quiz", tags=["quiz"])
settings = Settings()


@router.post("/generate", response_model=dict)
async def generate_quiz(quiz_request: QuizGenerate, user_id: int):
    """Generate a quiz from a song with blanks to fill."""

    db = DatabaseConnection(settings)

    # Check if song exists
    check_query = "SELECT COUNT(*) FROM Songs WHERE id = ?"
    count = db.execute_scalar(check_query, (quiz_request.song_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song with id {quiz_request.song_id} not found"
        )

    # Build query to get all chords for the song (or specific section)
    if quiz_request.section_id:
        query = """
            SELECT c.id, m.measure_number, c.beat_position, c.chord_symbol,
                   c.roman_numeral, c.key_center, c.chord_order
            FROM Chords c
            INNER JOIN Measures m ON c.measure_id = m.id
            INNER JOIN Sections s ON m.section_id = s.id
            WHERE s.id = ?
            ORDER BY m.measure_number, c.chord_order
        """
        params = (quiz_request.section_id,)
    else:
        query = """
            SELECT c.id, m.measure_number, c.beat_position, c.chord_symbol,
                   c.roman_numeral, c.key_center, c.chord_order
            FROM Chords c
            INNER JOIN Measures m ON c.measure_id = m.id
            INNER JOIN Sections s ON m.section_id = s.id
            WHERE s.song_id = ?
            ORDER BY s.section_order, m.measure_number, c.chord_order
        """
        params = (quiz_request.song_id,)

    result = db.execute_query(query, params)

    if not result or len(result) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chords found for this song/section"
        )

    # Select random chords to blank out
    total_chords = len(result)
    num_blanks = max(1, int(total_chords * quiz_request.blank_percentage))
    blank_indices = random.sample(range(total_chords), num_blanks)

    # Build list of all chord symbols for generating wrong options
    all_chords = [row['chord_symbol'] for row in result]
    unique_chords = list(set(all_chords))

    questions = []
    answers = []

    for i, row in enumerate(result):
        is_blank = i in blank_indices

        if is_blank:
            # Build context: preceding chords (up to 3)
            context_start = max(0, i - 3)
            context = [result[j]['chord_symbol'] for j in range(context_start, i)]

            # Generate multiple choice options
            correct_answer = row['chord_symbol']

            # Get wrong options (other chords from the song, excluding correct)
            wrong_options = [c for c in unique_chords if c != correct_answer]
            random.shuffle(wrong_options)
            wrong_options = wrong_options[:3]  # Take up to 3 wrong options

            # If not enough wrong options, add some common jazz chords
            common_jazz_chords = ['Cmaj7', 'Dm7', 'Em7', 'Fmaj7', 'G7', 'Am7', 'Bm7b5',
                                  'Cm7', 'Fm7', 'Bb7', 'Ebmaj7', 'Abmaj7', 'Dbmaj7']
            while len(wrong_options) < 3:
                fallback = random.choice(common_jazz_chords)
                if fallback != correct_answer and fallback not in wrong_options:
                    wrong_options.append(fallback)

            # Build options array and shuffle
            options = [correct_answer] + wrong_options[:3]
            random.shuffle(options)

            # Build question object in format frontend expects
            questions.append({
                "context": context,
                "options": options,
                "correct_answer": correct_answer,
                "chord_id": row['id'],
                "measure_number": row['measure_number'],
                "beat_position": float(row['beat_position']),
                "roman_numeral": row['roman_numeral'],
                "key_center": row['key_center']
            })

            answers.append({
                "chord_id": row['id'],
                "correct_answer": correct_answer
            })

    # Create quiz attempt record
    insert_query = """
        INSERT INTO QuizAttempts (user_id, song_id, quiz_type, section_id,
                                  started_at, total_questions, details)
        OUTPUT INSERTED.id
        VALUES (?, ?, 'fill_in_blanks', ?, GETDATE(), ?, ?)
    """

    details_json = json.dumps({"answers": answers})
    attempt_result = db.execute_query(
        insert_query,
        (user_id, quiz_request.song_id, quiz_request.section_id, num_blanks, details_json)
    )
    attempt_id = attempt_result[0]['id']

    return {
        "attempt_id": attempt_id,
        "total_questions": num_blanks,
        "questions": questions
    }


@router.post("/submit", response_model=QuizResult)
async def submit_quiz(submission: QuizSubmission):
    """Submit quiz answers and get results."""

    db = DatabaseConnection(settings)

    # Get quiz attempt
    query = """
        SELECT id, user_id, song_id, section_id, total_questions, details
        FROM QuizAttempts
        WHERE id = ?
    """
    result = db.execute_query(query, (submission.attempt_id,))

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz attempt {submission.attempt_id} not found"
        )

    row = result[0]
    attempt_id = row['id']
    user_id = row['user_id']
    song_id = row['song_id']
    section_id = row['section_id']
    total_questions = row['total_questions']
    details_json = row['details']

    # Parse the stored answers
    details = json.loads(details_json)
    correct_answers_data = details.get("answers", [])

    if len(submission.answers) != len(correct_answers_data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected {len(correct_answers_data)} answers, got {len(submission.answers)}"
        )

    # Score the answers
    correct_count = 0
    results_details = []

    for i, (user_answer, correct_data) in enumerate(zip(submission.answers, correct_answers_data)):
        correct_answer = correct_data["correct_answer"]
        is_correct = user_answer.strip().lower() == correct_answer.strip().lower()

        if is_correct:
            correct_count += 1

        results_details.append({
            "question_number": i + 1,
            "chord_id": correct_data["chord_id"],
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct
        })

    accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0

    # Update quiz attempt with results
    update_query = """
        UPDATE QuizAttempts
        SET completed_at = GETDATE(),
            correct_answers = ?,
            details = ?
        WHERE id = ?
    """

    results_json = json.dumps({"results": results_details})
    db.execute_non_query(update_query, (correct_count, results_json, attempt_id))

    # Update user progress
    from app.api.routes.progress import update_song_progress
    await update_song_progress(song_id, user_id, accuracy, increment_practice=True)

    return QuizResult(
        attempt_id=attempt_id,
        total_questions=total_questions,
        correct_answers=correct_count,
        accuracy=round(accuracy, 2),
        details=results_details
    )


@router.get("/attempts", response_model=List[QuizAttempt])
async def list_quiz_attempts(user_id: int, song_id: int = None):
    """List quiz attempts for a user, optionally filtered by song."""

    db = DatabaseConnection(settings)

    if song_id:
        query = """
            SELECT id, user_id, song_id, quiz_type, section_id, started_at,
                   completed_at, total_questions, correct_answers, details
            FROM QuizAttempts
            WHERE user_id = ? AND song_id = ?
            ORDER BY started_at DESC
        """
        params = (user_id, song_id)
    else:
        query = """
            SELECT id, user_id, song_id, quiz_type, section_id, started_at,
                   completed_at, total_questions, correct_answers, details
            FROM QuizAttempts
            WHERE user_id = ?
            ORDER BY started_at DESC
        """
        params = (user_id,)

    result = db.execute_query(query, params)

    if not result:
        return []

    attempts = []
    for row in result:
        attempts.append(QuizAttempt(
            id=row['id'],
            user_id=row['user_id'],
            song_id=row['song_id'],
            quiz_type=row['quiz_type'],
            section_id=row['section_id'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            total_questions=row['total_questions'],
            correct_answers=row['correct_answers'],
            details=row['details']
        ))

    return attempts


@router.get("/attempts/{attempt_id}", response_model=dict)
async def get_quiz_attempt(attempt_id: int):
    """Get detailed results for a specific quiz attempt."""

    db = DatabaseConnection(settings)

    query = """
        SELECT qa.id, qa.user_id, qa.song_id, s.title, qa.quiz_type,
               qa.section_id, qa.started_at, qa.completed_at,
               qa.total_questions, qa.correct_answers, qa.details
        FROM QuizAttempts qa
        INNER JOIN Songs s ON qa.song_id = s.id
        WHERE qa.id = ?
    """
    result = db.execute_query(query, (attempt_id,))

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz attempt {attempt_id} not found"
        )

    row = result[0]
    details = json.loads(row['details']) if row['details'] else {}

    return {
        "id": row['id'],
        "user_id": row['user_id'],
        "song_id": row['song_id'],
        "song_title": row['title'],
        "quiz_type": row['quiz_type'],
        "section_id": row['section_id'],
        "started_at": row['started_at'].isoformat() if row['started_at'] else None,
        "completed_at": row['completed_at'].isoformat() if row['completed_at'] else None,
        "total_questions": row['total_questions'],
        "correct_answers": row['correct_answers'],
        "accuracy": round((row['correct_answers'] / row['total_questions'] * 100), 2) if row['total_questions'] and row['correct_answers'] else 0,
        "details": details
    }
