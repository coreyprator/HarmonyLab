# app/api/routes/auth.py
"""
HM44.1: Passphrase authentication for HarmonyLab.
Single-user app: correct passphrase sets a signed hl_session cookie.
"""
import hmac
import os
import time
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from itsdangerous import URLSafeSerializer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/passphrase")
async def passphrase_login(payload: dict, response: Response):
    """HM44.1: Passphrase login. Sets hl_session cookie on success."""
    submitted = payload.get("passphrase", "")
    expected = os.environ.get("APP_PASSPHRASE", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Auth not configured")
    if not hmac.compare_digest(submitted, expected):
        raise HTTPException(status_code=401, detail="Invalid passphrase")
    secret = os.environ.get("APP_SECRET_KEY", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Auth not configured")
    serializer = URLSafeSerializer(secret, salt="hl-session")
    token = serializer.dumps({"authed_at": int(time.time())})
    response.set_cookie(
        "hl_session",
        token,
        max_age=86400 * 30,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"ok": True}
