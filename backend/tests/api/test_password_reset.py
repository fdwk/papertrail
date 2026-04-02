from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import FORGOT_PASSWORD_MESSAGE, RESET_PASSWORD_GENERIC_ERROR
from app.database import SessionLocal, get_db
from app.main import app
from app.models import PasswordResetToken, User
from app.passwords import hash_password, verify_password

# Setup/teardown session (main thread only). TestClient runs endpoints in worker threads — never share one Session with HTTP calls.
@pytest.fixture
def db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def _get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _unique_email() -> str:
    return f"pwreset_{uuid.uuid4().hex}@example.com"


def _token_from_reset_url(url: str) -> str:
    q = parse_qs(urlparse(url).query)
    return q["token"][0]


def _delete_user_cascade(session, user_id: uuid.UUID) -> None:
    session.rollback()
    session.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id
    ).delete(synchronize_session=False)
    session.query(User).filter(User.id == user_id).delete(
        synchronize_session=False
    )
    session.commit()


def test_forgot_password_unknown_email_returns_generic(client, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_send(to: str, url: str) -> None:
        calls.append((to, url))

    monkeypatch.setattr("app.auth.send_password_reset_email", fake_send)
    r = client.post(
        "/auth/forgot-password", json={"email": "nonexistent_xyz@example.com"}
    )
    assert r.status_code == 200
    assert r.json()["message"] == FORGOT_PASSWORD_MESSAGE
    assert calls == []


def test_forgot_password_existing_user_sends_email_once(
    client, db_session, monkeypatch
) -> None:
    email = _unique_email()
    user = User(email=email, password_hash=hash_password("OldPass123"))
    db_session.add(user)
    db_session.commit()
    uid = user.id

    calls: list[tuple[str, str]] = []

    def fake_send(to: str, url: str) -> None:
        calls.append((to, url))

    monkeypatch.setattr("app.auth.send_password_reset_email", fake_send)
    try:
        r = client.post("/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        assert r.json()["message"] == FORGOT_PASSWORD_MESSAGE
        assert len(calls) == 1
        assert calls[0][0] == email
        assert "token=" in calls[0][1]
    finally:
        _delete_user_cascade(db_session, uid)


def test_reset_password_happy_path_reuse_and_login(
    client, db_session, monkeypatch
) -> None:
    email = _unique_email()
    old_pw = "OldPass123"
    user = User(email=email, password_hash=hash_password(old_pw))
    db_session.add(user)
    db_session.commit()
    uid = user.id

    calls: list[tuple[str, str]] = []

    def fake_send(to: str, url: str) -> None:
        calls.append((to, url))

    monkeypatch.setattr("app.auth.send_password_reset_email", fake_send)
    try:
        r = client.post("/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        token = _token_from_reset_url(calls[0][1])

        new_pw = "NewPass456"
        r2 = client.post(
            "/auth/reset-password", json={"token": token, "password": new_pw}
        )
        assert r2.status_code == 200

        r_bad = client.post(
            "/auth/reset-password", json={"token": token, "password": new_pw}
        )
        assert r_bad.status_code == 400
        assert r_bad.json()["detail"] == RESET_PASSWORD_GENERIC_ERROR

        db_session.expire_all()
        row = db_session.query(User).filter(User.id == uid).first()
        assert row is not None
        ok_new, _ = verify_password(row.password_hash, new_pw)
        assert ok_new
        ok_old, _ = verify_password(row.password_hash, old_pw)
        assert not ok_old

        login_ok = client.post("/auth/login", json={"email": email, "password": new_pw})
        assert login_ok.status_code == 200
        login_bad = client.post(
            "/auth/login", json={"email": email, "password": old_pw}
        )
        assert login_bad.status_code == 401
    finally:
        _delete_user_cascade(db_session, uid)


def test_reset_password_invalid_token(client) -> None:
    r = client.post(
        "/auth/reset-password",
        json={"token": "not-a-real-token", "password": "ValidPass123"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == RESET_PASSWORD_GENERIC_ERROR


def test_reset_password_weak_password(client, db_session, monkeypatch) -> None:
    email = _unique_email()
    user = User(email=email, password_hash=hash_password("OldPass123"))
    db_session.add(user)
    db_session.commit()
    uid = user.id

    calls: list[str] = []

    def fake_send(_to: str, url: str) -> None:
        calls.append(url)

    monkeypatch.setattr("app.auth.send_password_reset_email", fake_send)
    try:
        client.post("/auth/forgot-password", json={"email": email})
        token = _token_from_reset_url(calls[0])
        r = client.post(
            "/auth/reset-password",
            json={"token": token, "password": "noupperordigit"},
        )
        assert r.status_code == 422
    finally:
        _delete_user_cascade(db_session, uid)
