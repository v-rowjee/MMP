import json

import pytest

from app.llm.client import OllamaClient


class Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.body


def test_chat_uses_the_configured_agent_model_and_options(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data)
        return Response(b'{"model":"nemotron-3-super:cloud","message":{"content":"Hello"}}')

    monkeypatch.setattr("app.llm.client.urlopen", fake_urlopen)
    client = OllamaClient()

    response = client.chat("chat", [{"role": "user", "content": "Hi"}])

    assert response == "Hello"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["timeout"] == 120
    assert captured["payload"] == {
        "model": "nemotron-3-super:cloud",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 32768},
    }


def test_loads_all_agent_configurations_from_one_file():
    client = OllamaClient()

    assert set(client.agents) == {"chat", "dashboard", "insights", "supervisor"}
    assert {config["model"] for config in client.agents.values()} == {
        "nemotron-3-super:cloud"
    }


def test_rejects_unknown_agent():
    client = OllamaClient()

    with pytest.raises(RuntimeError, match="Ollama request failed"):
        client.chat("unknown", [{"role": "user", "content": "Hi"}])


def test_returns_one_error_for_ollama_failures(monkeypatch):
    def fake_urlopen(*_):
        raise OSError

    monkeypatch.setattr("app.llm.client.urlopen", fake_urlopen)
    client = OllamaClient()

    with pytest.raises(RuntimeError, match="Ollama request failed"):
        client.chat("chat", [{"role": "user", "content": "Hi"}])
