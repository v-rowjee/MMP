import json

import pytest

from app.llm.client import OllamaClient, OllamaError
from app.schemas.dashboard import DashboardAnalysisPlan


class Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.body


def test_generate_uses_the_configured_agent_model_prompt_and_options(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data)
        return Response(
            b'{"model":"nemotron-3-super:cloud","message":{"content":"{\\"focus_areas\\":[\\"Sales\\"],\\"kpi_fields\\":[],\\"trend_fields\\":[],\\"anomaly_fields\\":[],\\"forecast_fields\\":[]}"}}'
        )

    monkeypatch.setattr("app.llm.client.urlopen", fake_urlopen)
    client = OllamaClient()

    response = client.generate(
        "dashboard",
        "dashboard_planner",
        {"fields": [{"name": "amount"}]},
        DashboardAnalysisPlan,
    )

    assert response.focus_areas == ["Sales"]
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["timeout"] == 120
    assert captured["payload"] == {
        "model": "nemotron-3-super:cloud",
        "messages": [
            {"role": "system", "content": client._prompt("dashboard_planner")},
            {"role": "user", "content": '{"fields": [{"name": "amount"}]}'},
        ],
        "stream": False,
        "format": DashboardAnalysisPlan.model_json_schema(),
        "options": {"temperature": 0.1, "num_ctx": 32768},
    }


def test_loads_all_agent_configurations_from_one_file():
    client = OllamaClient()

    assert set(client.agents) == {"chat", "dashboard", "insights", "supervisor"}
    assert {config["model"] for config in client.agents.values()} == {
        "nemotron-3-super:cloud"
    }


def test_rejects_unknown_agent():
    client = OllamaClient()

    with pytest.raises(KeyError, match="unknown agent"):
        client.generate("unknown", "dashboard_planner", {}, DashboardAnalysisPlan)


def test_returns_one_error_for_ollama_failures(monkeypatch):
    def fake_urlopen(*_, **__):
        raise OSError

    monkeypatch.setattr("app.llm.client.urlopen", fake_urlopen)
    client = OllamaClient()

    with pytest.raises(OllamaError, match="agent='dashboard'"):
        client.generate("dashboard", "dashboard_planner", {}, DashboardAnalysisPlan)


def test_loads_dashboard_prompts():
    names = [
        "dashboard_planner",
        "kpis_and_trends",
        "anomalies",
        "forecasts",
        "insights",
        "dashboard_layout",
    ]

    client = OllamaClient()
    prompts = [client._prompt(name) for name in names]

    assert all(prompt.startswith("role: ") for prompt in prompts)
    assert all("task: " in prompt and "output: " in prompt for prompt in prompts)
