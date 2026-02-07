"""
HarmonyLab Authentication Router
Google OAuth login/callback, token refresh, user info.
Based on Super-Flashcards pattern.
"""

from fastapi import APIRouter, HTTPException, status, Request, Response, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from datetime import datetime
from typing import Optional
import os
import logging

from app.db.connection import DatabaseConnection
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    sanitize_oauth_data,
    generate_username_from_email,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# Initialize OAuth client
oauth = OAuth()

if settings.google_client_id and settings.google_client_secret:
    logger.info(f"Registering Google OAuth client...")
    oauth.register(
        name='google',
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
        access_token_url='https://oauth2.googleapis.com/token',
        jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
        client_kwargs={
            'scope': 'openid email profile',
            'token_endpoint_auth_method': 'client_secret_post',
        },
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    )
    logger.info("Google OAuth client registered.")
else:
    logger.warning("Google OAuth NOT configured - Client ID or Secret missing!")


def get_current_user(request: Request) -> dict:
    """Dependency to get current authenticated user from JWT."""
    token = None

    # Try Authorization header first
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]

    # Fallback to cookie
    if not token:
        token = request.cookies.get('access_token')

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    user_id = payload.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Verify user exists in database
    db = DatabaseConnection(settings)
    result = db.execute_query(
        "SELECT id, email, display_name, avatar_url, is_active FROM Users WHERE id = ?",
        (user_id,)
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user = result[0]
    if not user.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_user_optional(request: Request) -> Optional[dict]:
    """Optional auth - returns None if not authenticated."""
    try:
        return get_current_user(request)
    except HTTPException:
        return None


def _set_refresh_cookie(response: Response, refresh_token: str):
    """Set refresh token as HTTP-only cookie."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login flow."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )

    redirect_uri = settings.google_redirect_uri
    logger.info(f"Starting Google OAuth with redirect: {redirect_uri}")

    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, response: Response):
    """Handle OAuth callback from Google."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )

    try:
        # Get OAuth token from Google
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )

        oauth_data = sanitize_oauth_data(user_info)
        db = DatabaseConnection(settings)

        # Check if user exists by Google ID
        result = db.execute_query(
            "SELECT id, email, display_name, avatar_url FROM Users WHERE google_id = ?",
            (oauth_data['google_id'],)
        )

        if result:
            user = result[0]
            # Update last login
            db.execute_non_query(
                "UPDATE Users SET last_login_at = GETDATE() WHERE id = ?",
                (user['id'],)
            )
        else:
            # Check if user exists by email
            result = db.execute_query(
                "SELECT id, email, display_name, avatar_url FROM Users WHERE email = ?",
                (oauth_data['email'],)
            )

            if result:
                user = result[0]
                # Link Google account to existing email user
                db.execute_non_query(
                    "UPDATE Users SET google_id = ?, avatar_url = ?, last_login_at = GETDATE() WHERE id = ?",
                    (oauth_data['google_id'], oauth_data['picture'], user['id'])
                )
            else:
                # Create new user
                display_name = oauth_data['name'] or generate_username_from_email(oauth_data['email'])
                db.execute_non_query(
                    """INSERT INTO Users (email, display_name, google_id, avatar_url, last_login_at)
                       VALUES (?, ?, ?, ?, GETDATE())""",
                    (oauth_data['email'], display_name, oauth_data['google_id'], oauth_data['picture'])
                )

                # Get the new user
                result = db.execute_query(
                    "SELECT id, email, display_name, avatar_url FROM Users WHERE google_id = ?",
                    (oauth_data['google_id'],)
                )
                user = result[0]

        # Create tokens
        token_data = {
            'user_id': str(user['id']),
            'email': user['email']
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Redirect to frontend with token
        # Use FRONTEND_URL env var if set, otherwise default to Cloud Run URL
        frontend_url = os.getenv("FRONTEND_URL")
        if not frontend_url:
            if os.getenv("K_SERVICE"):
                frontend_url = "https://harmonylab.rentyourcio.com"
            else:
                frontend_url = "http://localhost:8080"

        redirect_url = f"{frontend_url}/index.html?auth=success&token={access_token}"

        redirect_response = RedirectResponse(url=redirect_url)
        _set_refresh_cookie(redirect_response, refresh_token)
        return redirect_response

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_access_token(request: Request, response: Response):
    """Exchange refresh token for new access token."""
    refresh_tok = request.cookies.get("refresh_token")
    if not refresh_tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    payload = decode_refresh_token(refresh_tok)
    user_id = payload.get("user_id")

    # Verify user still exists
    db = DatabaseConnection(settings)
    result = db.execute_query(
        "SELECT id, email, is_active FROM Users WHERE id = ?",
        (user_id,)
    )

    if not result or not result[0].get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    user = result[0]

    # Issue new tokens
    token_data = {"user_id": str(user['id']), "email": user['email']}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)
    _set_refresh_cookie(response, new_refresh)

    return {
        "access_token": new_access,
        "token_type": "bearer",
        "expires_in": 900,
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user's profile."""
    return {
        "id": current_user['id'],
        "email": current_user['email'],
        "display_name": current_user.get('display_name'),
        "avatar_url": current_user.get('avatar_url'),
    }


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing auth cookies."""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return {"message": "Successfully logged out"}
