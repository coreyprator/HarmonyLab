"""
Analysis Rules API Routes (REQ-009 / HM30B)
CRUD for editable harmonic analysis rules.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel
from app.db.connection import DatabaseConnection, get_db
import logging

router = APIRouter(prefix="/api/v1/analysis-rules", tags=["analysis-rules"])
logger = logging.getLogger(__name__)


class RuleCreate(BaseModel):
    category: str
    title: str
    rule_text: str
    rule_order: int = 0


class RuleUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    rule_text: Optional[str] = None
    rule_order: Optional[int] = None
    active: Optional[bool] = None


@router.get("")
async def list_rules(db: DatabaseConnection = Depends(get_db)):
    """List all active analysis rules, ordered by rule_order."""
    rows = db.execute_query(
        "SELECT id, rule_order, category, title, rule_text, active, created_at, updated_at "
        "FROM analysis_rules WHERE active = 1 ORDER BY rule_order, id"
    )
    return [dict(r) for r in rows]


@router.post("")
async def create_rule(rule: RuleCreate, db: DatabaseConnection = Depends(get_db)):
    """Create a new analysis rule."""
    rows = db.execute_with_commit(
        "INSERT INTO analysis_rules (rule_order, category, title, rule_text) "
        "OUTPUT INSERTED.id "
        "VALUES (?, ?, ?, ?)",
        (rule.rule_order, rule.category, rule.title, rule.rule_text)
    )
    new_id = rows[0]['id'] if rows else None
    return {"id": new_id, "status": "created"}


@router.put("/{rule_id}")
async def update_rule(rule_id: int, rule: RuleUpdate, db: DatabaseConnection = Depends(get_db)):
    """Update an existing analysis rule."""
    existing = db.execute_query(
        "SELECT id FROM analysis_rules WHERE id = ?", (rule_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")

    updates = []
    params = []
    if rule.category is not None:
        updates.append("category = ?")
        params.append(rule.category)
    if rule.title is not None:
        updates.append("title = ?")
        params.append(rule.title)
    if rule.rule_text is not None:
        updates.append("rule_text = ?")
        params.append(rule.rule_text)
    if rule.rule_order is not None:
        updates.append("rule_order = ?")
        params.append(rule.rule_order)
    if rule.active is not None:
        updates.append("active = ?")
        params.append(1 if rule.active else 0)

    if not updates:
        return {"status": "no_changes"}

    updates.append("updated_at = GETDATE()")
    params.append(rule_id)

    db.execute_non_query(
        f"UPDATE analysis_rules SET {', '.join(updates)} WHERE id = ?",
        tuple(params)
    )
    return {"id": rule_id, "status": "updated"}


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: DatabaseConnection = Depends(get_db)):
    """Soft-delete an analysis rule (set active=0)."""
    existing = db.execute_query(
        "SELECT id FROM analysis_rules WHERE id = ?", (rule_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.execute_non_query(
        "UPDATE analysis_rules SET active = 0, updated_at = GETDATE() WHERE id = ?",
        (rule_id,)
    )
    return {"id": rule_id, "status": "deleted"}


@router.get("/all")
async def list_all_rules(db: DatabaseConnection = Depends(get_db)):
    """List all rules including inactive (for admin UI)."""
    rows = db.execute_query(
        "SELECT id, rule_order, category, title, rule_text, active, created_at, updated_at "
        "FROM analysis_rules ORDER BY rule_order, id"
    )
    return [dict(r) for r in rows]
