import json

import pytest

from app.dashboard.agents.anomalies import PROMPT as ANOMALIES_PROMPT
from app.dashboard.agents.forecasts import PROMPT as FORECASTS_PROMPT
from app.dashboard.agents.insights import PROMPT as INSIGHTS_PROMPT
from app.dashboard.agents.kpis_and_trends import PROMPT as KPIS_PROMPT
from app.dashboard.agents.layout import PROMPT as LAYOUT_PROMPT
from app.dashboard.agents.planner import PROMPT as PLANNER_PROMPT
from app.llm.client import OllamaClient
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


def test_generate_uses_the_configured_model_and_explicit_agent_prompt(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data)
        return Response(
            b'{"message":{"content":"{\\"focus_areas\\":[\\"Sales\\"],\\"kpi_fields\\":[],\\"trend_fields\\":[],\\"anomaly_fields\\":[],\\"forecast_fields\\":[]}"}}'
        )

    monkeypatch.setattr("app.llm.client.urlopen", fake_urlopen)
    response = OllamaClient().generate(
        "supervisor", PLANNER_PROMPT, {"fields": [{"name": "amount"}]}, DashboardAnalysisPlan
    )

    assert response.focus_areas == ["Sales"]
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["timeout"] == 120
    assert captured["payload"] == {
        "model": "nemotron-3-super:cloud",
        "messages": [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": '{"fields": [{"name": "amount"}]}'},
        ],
        "stream": False,
        "format": DashboardAnalysisPlan.model_json_schema(),
        "options": {"temperature": 0.1, "num_ctx": 32768},
    }


def test_loads_all_agent_configurations_from_one_file():
    client = OllamaClient()

    assert set(client.agents) == {
        "supervisor", "kpi", "anomaly", "forecast", "insights", "layout", "chat"
    }
    assert {config["model"] for config in client.agents.values()} == {
        "nemotron-3-super:cloud"
    }


def test_rejects_unknown_agent():
    with pytest.raises(KeyError, match="unknown agent"):
        OllamaClient().generate("unknown", PLANNER_PROMPT, {}, DashboardAnalysisPlan)


def test_returns_one_error_for_ollama_failures(monkeypatch):
    monkeypatch.setattr("app.llm.client.urlopen", lambda *_, **__: (_ for _ in ()).throw(OSError()))

    with pytest.raises(RuntimeError, match="agent='supervisor'"):
        OllamaClient().generate("supervisor", PLANNER_PROMPT, {}, DashboardAnalysisPlan)


@pytest.mark.parametrize(
    ("prompt", "response_keys"),
    [
        (PLANNER_PROMPT, ("focus_areas", "kpi_fields", "trend_fields", "anomaly_fields", "forecast_fields")),
        (KPIS_PROMPT, ("kpis", "trends")),
        (ANOMALIES_PROMPT, ("descriptions",)),
        (FORECASTS_PROMPT, ("forecasts",)),
        (INSIGHTS_PROMPT, ("insights", "recommendations")),
        (LAYOUT_PROMPT, ("charts",)),
    ],
)
def test_dashboard_prompts_are_owned_by_agents(prompt, response_keys):
    assert prompt.startswith("role: ")
    assert "task: " in prompt and "output: " in prompt
    for key in response_keys:
        assert f'"{key}"' in prompt
