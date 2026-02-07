"""
API routes for user progress tracking.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
from app.models import UserSongProgress, UserSongProgressCreate, ProgressResponse
from app.db.connection import DatabaseConnection
from config.settings import Settings

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])
settings = Settings()


@router.get("/", response_model=List[ProgressResponse])
async def list_all_progress(user_id: int):
    """List all progress for a user across all songs."""

    db = DatabaseConnection(settings)

    query = """
        SELECT p.song_id, s.title, p.last_practiced, p.times_practiced,
               p.accuracy_rate, p.mastery_level
        FROM UserSongProgress p
        INNER JOIN Songs s ON p.song_id = s.id
        WHERE p.user_id = ?
        ORDER BY p.last_practiced DESC
    """

    result = db.execute_query(query, (user_id,))

    if not result:
        return []

    progress_list = []
    for row in result:
        progress_list.append(ProgressResponse(
            song_id=row['song_id'],
            song_title=row['title'],
            last_practiced=row['last_practiced'],
            times_practiced=row['times_practiced'],
            accuracy_rate=float(row['accuracy_rate']) if row['accuracy_rate'] else None,
            mastery_level=row['mastery_level']
        ))

    return progress_list


@router.get("/song/{song_id}", response_model=UserSongProgress)
async def get_song_progress(song_id: int, user_id: int):
    """Get progress for a specific song."""

    db = DatabaseConnection(settings)

    # Check if song exists
    check_query = "SELECT COUNT(*) FROM Songs WHERE id = ?"
    count = db.execute_scalar(check_query, (song_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song with id {song_id} not found"
        )

    query = """
        SELECT id, user_id, song_id, last_practiced, times_practiced,
               accuracy_rate, mastery_level, notes
        FROM UserSongProgress
        WHERE song_id = ? AND user_id = ?
    """

    result = db.execute_query(query, (song_id, user_id))

    if not result:
        # Create default progress record
        create_query = """
            INSERT INTO UserSongProgress (user_id, song_id, times_practiced, mastery_level)
            OUTPUT INSERTED.id, INSERTED.user_id, INSERTED.song_id, INSERTED.last_practiced,
                   INSERTED.times_practiced, INSERTED.accuracy_rate, INSERTED.mastery_level,
                   INSERTED.notes
            VALUES (?, ?, 0, 0)
        """
        result = db.execute_query(create_query, (user_id, song_id))

    row = result[0]
    return UserSongProgress(
        id=row['id'],
        user_id=row['user_id'],
        song_id=row['song_id'],
        last_practiced=row['last_practiced'],
        times_practiced=row['times_practiced'],
        accuracy_rate=row['accuracy_rate'],
        mastery_level=row['mastery_level'],
        notes=row['notes']
    )


@router.post("/song/{song_id}", response_model=UserSongProgress)
async def update_song_progress(
    song_id: int,
    user_id: int,
    accuracy: float = None,
    increment_practice: bool = True
):
    """Create or update progress after a practice session."""

    db = DatabaseConnection(settings)

    # Check if song exists
    check_query = "SELECT COUNT(*) FROM Songs WHERE id = ?"
    count = db.execute_scalar(check_query, (song_id,))
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song with id {song_id} not found"
        )

    # Check if progress record exists
    existing_query = """
        SELECT id, times_practiced, accuracy_rate, mastery_level
        FROM UserSongProgress
        WHERE song_id = ? AND user_id = ?
    """
    existing = db.execute_query(existing_query, (song_id, user_id))

    if existing:
        # Update existing record
        progress_id = existing[0]['id']
        times_practiced = existing[0]['times_practiced'] + (1 if increment_practice else 0)
        current_accuracy = existing[0]['accuracy_rate']
        mastery_level = existing[0]['mastery_level']

        # Update accuracy with weighted average if new accuracy provided
        if accuracy is not None:
            if current_accuracy:
                new_accuracy = (float(current_accuracy) * 0.7) + (accuracy * 0.3)
            else:
                new_accuracy = accuracy
        else:
            new_accuracy = current_accuracy

        # Update mastery level based on accuracy
        if new_accuracy:
            if new_accuracy >= 95:
                mastery_level = min(5, mastery_level + 1)
            elif new_accuracy >= 80:
                mastery_level = max(0, min(4, mastery_level))
            elif new_accuracy < 60:
                mastery_level = max(0, mastery_level - 1)

        update_query = """
            UPDATE UserSongProgress
            SET last_practiced = GETDATE(),
                times_practiced = ?,
                accuracy_rate = ?,
                mastery_level = ?
            WHERE id = ?
        """
        db.execute_non_query(update_query, (times_practiced, new_accuracy, mastery_level, progress_id))
    else:
        # Create new record
        mastery_level = 1 if accuracy and accuracy >= 80 else 0

        insert_query = """
            INSERT INTO UserSongProgress (user_id, song_id, last_practiced, times_practiced,
                                          accuracy_rate, mastery_level)
            OUTPUT INSERTED.id
            VALUES (?, ?, GETDATE(), ?, ?, ?)
        """
        result = db.execute_query(insert_query, (user_id, song_id, 1 if increment_practice else 0, accuracy, mastery_level))
        progress_id = result[0]['id']

    # Retrieve and return updated progress
    select_query = """
        SELECT id, user_id, song_id, last_practiced, times_practiced,
               accuracy_rate, mastery_level, notes
        FROM UserSongProgress
        WHERE id = ?
    """
    result = db.execute_query(select_query, (progress_id,))
    row = result[0]

    return UserSongProgress(
        id=row['id'],
        user_id=row['user_id'],
        song_id=row['song_id'],
        last_practiced=row['last_practiced'],
        times_practiced=row['times_practiced'],
        accuracy_rate=row['accuracy_rate'],
        mastery_level=row['mastery_level'],
        notes=row['notes']
    )


@router.get("/stats", response_model=dict)
async def get_stats(user_id: int):
    """Get aggregate statistics for a user."""

    db = DatabaseConnection(settings)

    # Total songs practiced
    songs_query = """
        SELECT COUNT(DISTINCT song_id)
        FROM UserSongProgress
        WHERE user_id = ? AND times_practiced > 0
    """
    songs_count = db.execute_scalar(songs_query, (user_id,))

    # Average accuracy
    accuracy_query = """
        SELECT AVG(CAST(accuracy_rate AS FLOAT))
        FROM UserSongProgress
        WHERE user_id = ? AND accuracy_rate IS NOT NULL
    """
    avg_accuracy = db.execute_scalar(accuracy_query, (user_id,))

    # Total practice sessions
    sessions_query = """
        SELECT SUM(times_practiced)
        FROM UserSongProgress
        WHERE user_id = ?
    """
    total_sessions = db.execute_scalar(sessions_query, (user_id,))

    # Mastery distribution
    mastery_query = """
        SELECT mastery_level, COUNT(*) AS cnt
        FROM UserSongProgress
        WHERE user_id = ?
        GROUP BY mastery_level
        ORDER BY mastery_level
    """
    mastery_result = db.execute_query(mastery_query, (user_id,))
    mastery_dist = {row['mastery_level']: row['cnt'] for row in mastery_result} if mastery_result else {}

    return {
        "user_id": user_id,
        "total_songs_practiced": songs_count or 0,
        "average_accuracy": round(float(avg_accuracy), 2) if avg_accuracy else 0.0,
        "total_practice_sessions": total_sessions or 0,
        "mastery_distribution": mastery_dist
    }
