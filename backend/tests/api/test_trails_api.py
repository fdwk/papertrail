from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.auth import require_user
from app.database import get_db
from app.main import app
from app.schemas import TrailSummaryOut
from app.services.trail_generator import TrailGenerationError
import app.trails as trails_module


def _dummy_db():
    yield object()


def test_create_trail_uses_generator(monkeypatch) -> None:  # noqa: ANN001
    app.dependency_overrides[require_user] = lambda: uuid.uuid4()
    app.dependency_overrides[get_db] = _dummy_db

    def fake_generate_trail(db, user_id, topic, size="medium"):  # noqa: ANN001, ANN202
        return TrailSummaryOut(
            id="trail-1",
            topic=topic,
            createdAt="2026-03-12",
            readCount=0,
            totalCount=5,
        )

    monkeypatch.setattr(trails_module, "generate_trail", fake_generate_trail)

    with TestClient(app) as client:
        response = client.post("/trails/", json={"topic": "Transformer Architecture", "size": "small"})
        assert response.status_code == 201
        data = response.json()
        assert data["topic"] == "Transformer Architecture"
        assert data["totalCount"] == 5

    app.dependency_overrides.clear()


def test_create_trail_falls_back_to_random_when_generation_fails(monkeypatch) -> None:  # noqa: ANN001
    app.dependency_overrides[require_user] = lambda: uuid.uuid4()
    app.dependency_overrides[get_db] = _dummy_db

    def fake_generate_trail(db, user_id, topic, size="medium"):  # noqa: ANN001, ANN202
        raise TrailGenerationError("boom")

    def fake_random(db, user_id, topic):  # noqa: ANN001, ANN202
        return TrailSummaryOut(
            id="trail-fallback",
            topic=topic,
            createdAt="2026-03-12",
            readCount=0,
            totalCount=3,
        )

    monkeypatch.setattr(trails_module, "generate_trail", fake_generate_trail)
    monkeypatch.setattr(trails_module, "create_trail_with_random_graph_db", fake_random)

    with TestClient(app) as client:
        response = client.post("/trails/", json={"topic": "Fallback Topic"})
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "trail-fallback"
        assert data["totalCount"] == 3

    app.dependency_overrides.clear()
