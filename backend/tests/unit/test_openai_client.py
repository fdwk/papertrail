from __future__ import annotations

import json

import pytest

from app.services import openai_client


class _FakeCompletion:
    def __init__(self, payload: str) -> None:
        self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": payload})()})()]


class _FakeChatCompletions:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def create(self, **kwargs):  # noqa: ANN003
        assert "model" in kwargs
        assert "messages" in kwargs
        return _FakeCompletion(self._payload)


class _FakeClient:
    def __init__(self, payload: str) -> None:
        self.chat = type("Chat", (), {"completions": _FakeChatCompletions(payload)})()


def test_parse_json_response_raises_for_invalid_json() -> None:
    with pytest.raises(openai_client.OpenAIClientError, match="valid JSON"):
        openai_client._parse_json_response("not-json")


def test_suggest_papers_normalizes_and_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    papers = [{"title": f"Paper {i}", "authors": "X", "year": "2020"} for i in range(20)]
    papers.append({"title": "", "authors": "Y", "year": 2019})
    payload = json.dumps({"papers": papers})
    monkeypatch.setattr(openai_client, "_client", lambda: _FakeClient(payload))

    result = openai_client.suggest_papers("transformers")
    assert len(result) == 15
    assert result[0] == {"title": "Paper 0", "authors": "X", "year": 2020}


def test_suggest_papers_raises_when_missing_papers_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_client, "_client", lambda: _FakeClient(json.dumps({"foo": []})))
    with pytest.raises(openai_client.OpenAIClientError, match="missing 'papers' list"):
        openai_client.suggest_papers("topic")


def test_select_and_order_normalizes_output(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps(
        {
            "selected_papers": ["W1", "  ", "W2"],
            "edges": [
                {"from": "W1", "to": "W2"},
                {"from": "W2", "to": "W2"},
                {"from": "", "to": "W1"},
            ],
        }
    )
    monkeypatch.setattr(openai_client, "_client", lambda: _FakeClient(payload))

    out = openai_client.select_and_order_papers("topic", [], [])
    assert out["selected_papers"] == ["W1", "W2"]
    assert out["edges"] == [{"from": "W1", "to": "W2"}]
