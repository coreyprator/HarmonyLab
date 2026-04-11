"""
API routes for user preferences (HM34 REQ-011, HM36 REQ-010).
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.db.connection import DatabaseConnection, get_db
from app.api.routes.auth import get_current_user

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


class PreferenceUpdate(BaseModel):
    chord_symbol_mode: Optional[str] = None
    key_center_colors: Optional[dict] = None


@router.get("")
async def get_preferences(
    request: Request,
    db: DatabaseConnection = Depends(get_db)
):
    """Get current user's preferences."""
    user = get_current_user(request)
    row = db.execute_query(
        "SELECT chord_symbol_mode, key_center_colors FROM UserPreferences WHERE user_id = ?",
        (user['id'],)
    )
    if row:
        colors_raw = row[0].get('key_center_colors')
        colors = json.loads(colors_raw) if colors_raw else None
        return {
            "chord_symbol_mode": row[0]['chord_symbol_mode'],
            "key_center_colors": colors,
        }
    return {"chord_symbol_mode": "jazz", "key_center_colors": None}


@router.put("")
async def update_preferences(
    body: PreferenceUpdate,
    request: Request,
    db: DatabaseConnection = Depends(get_db)
):
    """Update current user's preferences."""
    user = get_current_user(request)

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

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(updates) + ", updated_at = GETUTCDATE()"

    # Build INSERT values
    mode = body.chord_symbol_mode or 'jazz'
    colors_json = json.dumps(body.key_center_colors) if body.key_center_colors else None

    db.execute_non_query(f"""
        MERGE UserPreferences AS target
        USING (SELECT ? AS user_id) AS source
        ON target.user_id = source.user_id
        WHEN MATCHED THEN
            UPDATE SET {set_clause}
        WHEN NOT MATCHED THEN
            INSERT (user_id, chord_symbol_mode, key_center_colors) VALUES (?, ?, ?);
    """, (user['id'], *params, user['id'], mode, colors_json))

    return {"chord_symbol_mode": mode, "key_center_colors": body.key_center_colors}
