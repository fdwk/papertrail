"""Auth: mock users, JWT login/signup, get_current_user dependency."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
JWT_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_TTL_DAYS = 7

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    token: str


def _create_token(email: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=JWT_TTL_DAYS)
    payload = {"email": email, "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


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
    """
    Login now verifies the user against the real database.
    Passwords are stored in User.password_hash (currently as plain text).
    """
    db_user = db.query(User).filter(User.email == body.email).first()
    if not db_user or db_user.password_hash != body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = _create_token(db_user.email)
    return TokenResponse(token=token)


@router.post("/signup", response_model=TokenResponse)
def signup(body: LoginBody, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Signup persists the new user in the database
    """
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )

    new_user = User(email=body.email, password_hash=body.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = _create_token(new_user.email)
    return TokenResponse(token=token)
