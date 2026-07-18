"""JWT session cookie helpers.

The session is a signed JWT stored in an HttpOnly cookie. It carries the
authenticated user's email and name; nothing sensitive lives client-side.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import jwt
from fastapi import Request, Response

from ..config import Settings, get_settings

ALGORITHM = "HS256"


@dataclass
class SessionUser:
    email: str
    name: str


def issue_session(response: Response, user: SessionUser, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    now = int(time.time())
    payload = {
        "sub": user.email,
        "name": user.name,
        "iat": now,
        "exp": now + settings.jwt_ttl_seconds,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    secure = settings.base_url.startswith("https://")
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.jwt_ttl_seconds,
        path="/",
    )


def clear_session(response: Response, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")


def read_session(request: Request, settings: Settings | None = None) -> SessionUser | None:
    settings = settings or get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    email = payload.get("sub")
    if not email:
        return None
    return SessionUser(email=email, name=payload.get("name", email))
