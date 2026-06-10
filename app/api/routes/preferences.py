"""
API routes for user preferences (HM34 REQ-011, HM36 REQ-010).
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db.connection import DatabaseConnection, get_db

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


class PreferenceUpdate(BaseModel):
    chord_symbol_mode: Optional[str] = None
    key_center_colors: Optional[dict] = None
    debug_mode: Optional[bool] = None
    # HM44 A3 (REQ-020): default voicing notation preference
    default_voicing_notation: Optional[str] = None


@router.get("")
async def get_preferences(
    db: DatabaseConnection = Depends(get_db)
):
    """Get current user's preferences."""
    user_id = 1
    row = db.execute_query(
        "SELECT chord_symbol_mode, key_center_colors, debug_mode, "
        "default_voicing_notation FROM UserPreferences WHERE user_id = ?",
        (user_id,)
    )
    if row:
        colors_raw = row[0].get('key_center_colors')
        colors = json.loads(colors_raw) if colors_raw else None
        return {
            "chord_symbol_mode": row[0]['chord_symbol_mode'],
            "key_center_colors": colors,
            "debug_mode": bool(row[0].get('debug_mode', 0)),
            "default_voicing_notation": row[0].get('default_voicing_notation'),
        }
    return {
        "chord_symbol_mode": "jazz",
        "key_center_colors": None,
        "debug_mode": False,
        "default_voicing_notation": None,
    }


@router.put("")
async def update_preferences(
    body: PreferenceUpdate,
    db: DatabaseConnection = Depends(get_db)
):
    """Update current user's preferences."""
    user_id = 1

    if body.chord_symbol_mode is not None and body.chord_symbol_mode not in ('jazz', 'plain'):
        raise HTTPException(status_code=400, detail="chord_symbol_mode must be 'jazz' or 'plain'")

    # Build SET clause dynamically
    updates = []
    params = []
    if body.chord_symbol_mode is not None:
        updates.append("chord_symbol_mode = ?")
        params.append(body.chord_symbol_mode)
    if body.key_center_colors is not None:
        updates.append("key_center_colors = ?")
        params.append(json.dumps(body.key_center_colors))
    if body.debug_mode is not None:
        updates.append("debug_mode = ?")
        params.append(1 if body.debug_mode else 0)
    if body.default_voicing_notation is not None:
        updates.append("default_voicing_notation = ?")
        params.append(body.default_voicing_notation)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(updates) + ", updated_at = GETUTCDATE()"

    # Build INSERT defaults
    mode = body.chord_symbol_mode or 'jazz'
    colors_json = json.dumps(body.key_center_colors) if body.key_center_colors else None
    debug_val = (1 if body.debug_mode else 0) if body.debug_mode is not None else 0
    voicing_val = body.default_voicing_notation

    db.execute_non_query(f"""
        MERGE UserPreferences AS target
        USING (SELECT ? AS user_id) AS source
        ON target.user_id = source.user_id
        WHEN MATCHED THEN
            UPDATE SET {set_clause}
        WHEN NOT MATCHED THEN
            INSERT (user_id, chord_symbol_mode, key_center_colors, debug_mode,
                    default_voicing_notation)
            VALUES (?, ?, ?, ?, ?);
    """, (user_id, *params, user_id, mode, colors_json, debug_val, voicing_val))

    return {
        "chord_symbol_mode": mode,
        "key_center_colors": body.key_center_colors,
        "debug_mode": bool(body.debug_mode) if body.debug_mode is not None else False,
        "default_voicing_notation": voicing_val,
    }
