"""Auth: mock users, JWT login/signup, get_current_user dependency."""
from __future__ import annotations

import contextlib
import hashlib
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated
from urllib.parse import quote, unquote, urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import get_db
from .email_resend import (
    build_reset_password_url,
    public_web_app_url,
    send_password_reset_email,
)
from .models import PasswordResetToken, User
from .passwords import hash_password, verify_password
from .repositories.trails import (
    count_trails_for_user as count_trails_for_user_db,
    delete_trail as delete_trail_db,
    list_oldest_trail_ids_for_user as list_oldest_trail_ids_for_user_db,
)
JWT_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_TTL_DAYS = 7
FREE_TRAIL_LIMIT = 3
PASSWORD_RESET_TTL = timedelta(hours=1)
FORGOT_PASSWORD_MESSAGE = (
    "If an account exists for this email, you will receive password reset instructions shortly."
)
RESET_PASSWORD_GENERIC_ERROR = "Invalid or expired reset link."
GOOGLE_ONLY_LOGIN_DETAIL = (
    "This account uses Google sign-in. Please sign in with Google."
)

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_OAUTH_STATE_COOKIE = "oauth_google_state"
GOOGLE_OAUTH_STATE_MAX_AGE = 600

logger = logging.getLogger("backend")

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class LoginBody(BaseModel):
    """Login accepts any non-empty password so legacy accounts are not locked out."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)


def validate_signup_password_strength(v: str) -> str:
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must include a lowercase letter")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must include an uppercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must include a number")
    return v


class SignupBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_signup_password_strength(v)


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordBody(BaseModel):
    token: str = Field(..., min_length=1, max_length=512)
    password: str = Field(..., min_length=8, max_length=256)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_signup_password_strength(v)


class ResetPasswordResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    token: str

class ChooseTierBody(BaseModel):
    tier: str
    confirmDowngrade: bool = False


def _create_token(email: str, tier: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=JWT_TTL_DAYS)
    payload = {"email": email, "tier": tier, "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _frontend_base_url() -> str:
    return public_web_app_url()


def _oauth_cookie_secure(redirect_uri: str) -> bool:
    u = redirect_uri.strip().lower()
    return u.startswith("https://")


@contextlib.contextmanager
def _google_oauth_https_env():
    """
    httpx and google-auth/requests read SSL_CERT_FILE / SSL_CERT_DIR from the environment.
    Conda/WSL setups often set these to paths that do not exist on Windows -> FileNotFoundError.
    Temporarily unset invalid entries for the Google token + JWKS calls only.
    """
    removed: dict[str, str] = {}
    for key, check_file in (("SSL_CERT_FILE", True), ("SSL_CERT_DIR", False)):
        val = os.environ.get(key)
        if not val:
            continue
        ok = os.path.isfile(val) if check_file else os.path.isdir(val)
        if not ok:
            removed[key] = val
            del os.environ[key]
    try:
        yield
    finally:
        for k, v in removed.items():
            os.environ[k] = v


def _redirect_oauth_error(message: str) -> RedirectResponse:
    base = _frontend_base_url()
    url = f"{base}/login?oauth_error={quote(message)}"
    resp = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE, path="/")
    return resp


def _redirect_oauth_success(jwt_token: str) -> RedirectResponse:
    base = _frontend_base_url()
    url = f"{base}/auth/callback?token={quote(jwt_token, safe='')}"
    resp = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(GOOGLE_OAUTH_STATE_COOKIE, path="/")
    return resp


@router.get("/google")
def google_oauth_start() -> RedirectResponse:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if not client_id or not redirect_uri:
        return _redirect_oauth_error("Google sign-in is not configured.")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"
    resp = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        key=GOOGLE_OAUTH_STATE_COOKIE,
        value=state,
        max_age=GOOGLE_OAUTH_STATE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_oauth_cookie_secure(redirect_uri),
        path="/",
    )
    return resp


@router.get("/google/callback")
def google_oauth_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Exchange Google auth code, verify ID token, issue same JWT as password login."""
    if error:
        if error == "access_denied":
            return _redirect_oauth_error("Google sign-in was cancelled.")
        return _redirect_oauth_error("Google sign-in failed. Please try again.")

    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if not client_id or not client_secret or not redirect_uri:
        return _redirect_oauth_error("Google sign-in is not configured.")

    cookie_state = request.cookies.get(GOOGLE_OAUTH_STATE_COOKIE)
    if (
        not code
        or not state
        or not cookie_state
        or not secrets.compare_digest(cookie_state, state)
    ):
        logger.warning(
            "Google OAuth callback: invalid or missing state "
            "(use the same host for API and GOOGLE_REDIRECT_URI, e.g. only localhost or only 127.0.0.1)"
        )
        return _redirect_oauth_error("Sign-in session expired. Please try again.")

    try:
        with _google_oauth_https_env():
            with httpx.Client(trust_env=False) as client:
                token_res = client.post(
                    GOOGLE_TOKEN_ENDPOINT,
                    data={
                        "code": code,
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri,
                        "grant_type": "authorization_code",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                token_res.raise_for_status()
                token_json = token_res.json()
    except (httpx.HTTPError, ValueError, OSError) as exc:
        logger.exception("Google token exchange failed: %s", exc)
        return _redirect_oauth_error(
            "Could not complete Google sign-in. Please try again."
        )

    id_token_str = token_json.get("id_token")
    if not id_token_str or not isinstance(id_token_str, str):
        logger.warning("Google token response missing id_token")
        return _redirect_oauth_error(
            "Could not complete Google sign-in. Please try again."
        )

    try:
        with _google_oauth_https_env():
            info = id_token.verify_oauth2_token(
                id_token_str,
                GoogleAuthRequest(),
                client_id,
            )
    except ValueError:
        logger.exception("Google ID token verification failed")
        return _redirect_oauth_error(
            "Google sign-in could not be verified. Please try again."
        )

    email = info.get("email")
    if not email or not isinstance(email, str):
        return _redirect_oauth_error(
            "Your Google account did not provide an email address."
        )
    if info.get("email_verified") is False:
        return _redirect_oauth_error(
            "Your Google email is not verified. Please verify it and try again."
        )

    email = email.strip()
    display_name = info.get("name")
    if display_name is not None and not isinstance(display_name, str):
        display_name = None

    user = (
        db.query(User)
        .filter(func.lower(User.email) == email.lower())
        .first()
    )
    if user is None:
        user = User(
            email=email,
            password_hash=None,
            name=display_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif display_name and not user.name:
        user.name = display_name
        db.commit()
        db.refresh(user)

    jwt_token = _create_token(user.email, user.tier)
    return _redirect_oauth_success(jwt_token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    body: ForgotPasswordBody, db: Session = Depends(get_db)
) -> ForgotPasswordResponse:
    """Same response whether or not the email exists (avoid account enumeration)."""
    user = (
        db.query(User)
        .filter(func.lower(User.email) == body.email.lower())
        .first()
    )
    if user:
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        ).delete(synchronize_session=False)
        raw = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        token_row = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_reset_token(raw),
            expires_at=now + PASSWORD_RESET_TTL,
            created_at=now,
        )
        db.add(token_row)
        db.commit()
        reset_url = build_reset_password_url(raw)
        try:
            send_password_reset_email(user.email, reset_url)
        except Exception:
            logger.exception("Failed to send password reset email")
    return ForgotPasswordResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    body: ResetPasswordBody, db: Session = Depends(get_db)
) -> ResetPasswordResponse:
    raw = unquote(body.token.strip())
    token_hash = _hash_reset_token(raw)
    now = datetime.now(timezone.utc)
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if (
        row is None
        or row.used_at is not None
        or row.expires_at < now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=RESET_PASSWORD_GENERIC_ERROR,
        )
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=RESET_PASSWORD_GENERIC_ERROR,
        )
    user.password_hash = hash_password(body.password)
    row.used_at = now
    db.commit()
    return ResetPasswordResponse(message="Your password has been reset. You can sign in now.")


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Session = Depends(get_db),
) -> uuid.UUID | None:
    """
    Returns the current user's DB id (UUID) if the JWT is valid, else None.
    Does not raise so it can be used in optional contexts.
    """
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        email = payload.get("email")
        if not email:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user.id if user else None
    except jwt.PyJWTError:
        return None


def require_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID:
    """Requires valid JWT; returns user id (UUID). Raises 401 if missing/invalid."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required"
        )
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        # Look up user in the real database
        with next(get_db()) as db:
            db_user = db.query(User).filter(User.email == email).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )
        return db_user.id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

@router.post("/login", response_model=TokenResponse)
def login(body: LoginBody, db: Session = Depends(get_db)) -> TokenResponse:
    """Verify password (Argon2id or legacy plaintext during migration); re-hash when needed."""
    db_user = db.query(User).filter(User.email == body.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not db_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=GOOGLE_ONLY_LOGIN_DETAIL,
        )
    ok, new_hash = verify_password(db_user.password_hash, body.password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if new_hash is not None:
        db_user.password_hash = new_hash
        db.commit()

    token = _create_token(db_user.email, db_user.tier)
    return TokenResponse(token=token)


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignupBody, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Signup persists the new user in the database
    """
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    new_user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = _create_token(new_user.email, new_user.tier)
    return TokenResponse(token=token)


@router.post("/choose-tier", response_model=TokenResponse)
def choose_tier(body: ChooseTierBody, user_id: uuid.UUID = Depends(require_user), db: Session = Depends(get_db)) -> TokenResponse:
    """Set the current user's plan tier and return a refreshed JWT with the new tier."""
    allowed = {"Reader", "Scholar", "Lab"}
    tier = (body.tier or "").strip()
    if tier not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tier")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_tier = user.tier or "Reader"

    # Downgrade flow: Reader supports up to FREE_TRAIL_LIMIT trails.
    if current_tier != "Reader" and tier == "Reader":
        trail_count = count_trails_for_user_db(db, user_id)
        if trail_count > FREE_TRAIL_LIMIT and not body.confirmDowngrade:
            to_delete = trail_count - FREE_TRAIL_LIMIT
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Downgrading to Reader will delete your {to_delete} oldest trail(s) and keep "
                    f"the {FREE_TRAIL_LIMIT} most recent. Continue?"
                ),
            )
        if trail_count > FREE_TRAIL_LIMIT and body.confirmDowngrade:
            to_delete = trail_count - FREE_TRAIL_LIMIT
            oldest_ids = list_oldest_trail_ids_for_user_db(db, user_id, to_delete)
            for tid in oldest_ids:
                delete_trail_db(db, tid, user_id)

    user.tier = tier
    db.commit()
    db.refresh(user)

    token = _create_token(user.email, user.tier)
    return TokenResponse(token=token)
