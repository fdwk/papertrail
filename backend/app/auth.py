"""Auth: mock users, JWT login/signup, get_current_user dependency."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated
from urllib.parse import unquote

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import get_db
from .email_resend import build_reset_password_url, send_password_reset_email
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
