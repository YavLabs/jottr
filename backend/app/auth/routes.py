"""Authentication routes: Google OAuth 2.0 with an email allowlist.

Flow:
    GET  /api/auth/login     -> redirect to Google consent (or dev bypass)
    GET  /api/auth/callback  -> exchange code, verify email, set session cookie
    POST /api/auth/logout    -> clear session cookie
    GET  /api/auth/me        -> current user or 401

A dev bypass (settings.dev_auth, on by default when Google isn't configured)
logs in a fixed local user so Phase 0 runs before real credentials exist.
"""

from __future__ import annotations

import json

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from ..config import Settings, get_settings
from .session import SessionUser, clear_session, issue_session, read_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Authlib OAuth registry. Google's OIDC discovery document wires up endpoints.
_oauth = OAuth()
_google_registered = False


def _ensure_google_registered(settings: Settings) -> None:
    global _google_registered
    if _google_registered or not settings.google_configured:
        return
    _oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    _google_registered = True


def _persist_refresh_token(settings: Settings, email: str, token: dict) -> None:
    """Store the Google refresh token in the volume for later calendar access."""
    refresh = token.get("refresh_token")
    if not refresh:
        return
    settings.auth_dir.mkdir(parents=True, exist_ok=True)
    path = settings.auth_dir / "token.json"
    path.write_text(json.dumps({"email": email, "refresh_token": refresh}, indent=2))


def current_user(
    request: Request, settings: Settings = Depends(get_settings)
) -> SessionUser:
    user = read_session(request, settings)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/login")
async def login(request: Request, settings: Settings = Depends(get_settings)):
    # Dev bypass: no Google configured -> log in the fixed dev user directly.
    if settings.dev_auth and not settings.google_configured:
        if not settings.is_email_allowed(settings.dev_auth_email):
            raise HTTPException(status_code=403, detail="Dev user not allowed")
        response = RedirectResponse(url="/")
        issue_session(response, SessionUser(email=settings.dev_auth_email, name="Dev User"), settings)
        return response

    if not settings.google_configured:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    _ensure_google_registered(settings)
    return await _oauth.google.authorize_redirect(request, settings.oauth_redirect_uri)


@router.get("/callback")
async def callback(request: Request, settings: Settings = Depends(get_settings)):
    if not settings.google_configured:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    _ensure_google_registered(settings)
    try:
        token = await _oauth.google.authorize_access_token(request)
    except Exception as exc:  # authlib raises varied error types
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {exc}")

    userinfo = token.get("userinfo") or {}
    email = (userinfo.get("email") or "").lower()
    name = userinfo.get("name") or email

    if not email or not userinfo.get("email_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")
    if not settings.is_email_allowed(email):
        raise HTTPException(status_code=403, detail="This email is not on the allowlist")

    _persist_refresh_token(settings, email, token)

    response = RedirectResponse(url="/")
    issue_session(response, SessionUser(email=email, name=name), settings)
    return response


@router.post("/logout")
async def logout(settings: Settings = Depends(get_settings)):
    response = JSONResponse({"ok": True})
    clear_session(response, settings)
    return response


@router.get("/me")
async def me(request: Request, settings: Settings = Depends(get_settings)):
    user = read_session(request, settings)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"email": user.email, "name": user.name}
