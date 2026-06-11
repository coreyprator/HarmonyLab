# app/middleware/session_auth.py
"""
HM44.1: Passphrase session authentication middleware.
Validates the hl_session cookie signed with APP_SECRET_KEY.
Copied from ArtForge session_auth.py and adapted for HarmonyLab (no ORM, single user).
"""

import os
import logging
from itsdangerous import URLSafeSerializer, BadSignature
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse, JSONResponse

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {
    "/",
    "/login",
    "/health",
    "/api/auth/passphrase",
    "/favicon.ico",
}

STATIC_PREFIXES = (
    "/frontend-redesign/",
    "/proto/",
    "/redesign.css",
    "/login.html",
    "/index.html",
)


class SessionAuthMiddleware(BaseHTTPMiddleware):
    """
    Validates hl_session cookie for all non-public paths.
    - API paths (starting /api/) return 401 JSON when unauthenticated.
    - Browser paths redirect to /login when unauthenticated.
    """

    def __init__(self, app):
        super().__init__(app)
        self._serializer = None

    def _get_serializer(self):
        if self._serializer is None:
            secret = os.environ.get("APP_SECRET_KEY", "").strip()
            if secret:
                self._serializer = URLSafeSerializer(secret, salt="hl-session")
        return self._serializer

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Pass through public paths and static prefixes
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in STATIC_PREFIXES):
            return await call_next(request)

        # Also pass through static file extensions (css, js, ico, png)
        if path.endswith((".css", ".js", ".jsx", ".ico", ".png", ".svg", ".woff2", ".woff", ".html")):
            return await call_next(request)

        cookie = request.cookies.get("hl_session")

        if not cookie:
            if path.startswith("/api/"):
                return JSONResponse(
                    {"detail": "Not authenticated"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Cookie"},
                )
            return RedirectResponse(url="/login", status_code=302)

        serializer = self._get_serializer()
        if serializer is None:
            # APP_SECRET_KEY not configured — bypass (should not happen in prod)
            logger.warning("[SessionAuth] APP_SECRET_KEY not set, bypassing session check")
            return await call_next(request)

        try:
            serializer.loads(cookie)
        except BadSignature:
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Invalid session"}, status_code=401)
            return RedirectResponse(url="/login", status_code=302)

        return await call_next(request)
