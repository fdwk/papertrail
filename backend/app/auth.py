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

from .mock_data import MOCK_USERS, get_user_by_email

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
) -> str | None:
    """Returns user id (email for mock) if valid JWT, else None. Does not raise."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("email")
    except jwt.PyJWTError:
        return None


def require_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> uuid.UUID:
    """Requires valid JWT; returns user id (UUID). Raises 401 if missing/invalid."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user["id"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


@router.post("/login", response_model=TokenResponse)
def login(body: LoginBody) -> TokenResponse:
    user = get_user_by_email(body.email)
    if not user or user.get("password_hash") != body.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = _create_token(user["email"])
    return TokenResponse(token=token)


@router.post("/signup", response_model=TokenResponse)
def signup(body: LoginBody) -> TokenResponse:
    if get_user_by_email(body.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    MOCK_USERS.append({
        "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"user-{body.email}"),
        "email": body.email,
        "password_hash": body.password,
    })
    token = _create_token(body.email)
    return TokenResponse(token=token)
