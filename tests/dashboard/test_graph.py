from types import SimpleNamespace

import pytest

from app.dashboard import agents as dashboard_agents
from app.dashboard.graph import build_dashboard_graph
from app.dashboard.nodes import analysis as analysis_nodes
from app.dashboard.nodes.context import load_dataset_context
from app.dashboard.repository import DashboardRepository
from app.dashboard.validation import DashboardValidationService


class Query:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.value = None
        self.update_data = None

    def select(self, *_):
        return self

    def eq(self, _, value):
        self.value = value
        return self

    def maybe_single(self):
        return self

    def update(self, data):
        self.update_data = data
        return self

    def execute(self):
        rows = self.db.rows[self.table]
        if self.update_data is not None:
            row = next((row for row in rows if row["id"] == self.value), None)
            if row:
                row.update(self.update_data)
            return SimpleNamespace(data=row)
        if self.table == "dataset_fields":
            return SimpleNamespace(data=[row for row in rows if row["dataset_id"] == self.value])
        return SimpleNamespace(data=next((row for row in rows if row["id"] == self.value), None))


class Database:
    def __init__(self):
        self.rows = {
            "analysis_runs": [
                {
                    "id": "analysis_123",
                    "dataset_id": "dataset_123",
                    "workspace_id": "workspace_123",
                }
            ],
            "datasets": [
                {
                    "id": "dataset_123",
                    "workspace_id": "workspace_123",
                    "name": "sales",
                    "source_filename": "sales.csv",
                    "row_count": 2,
                    "meta": {"profile": {"column_count": 2}},
                }
            ],
            "dataset_fields": [
                {"dataset_id": "dataset_123", "name": "amount", "position": 1},
                {"dataset_id": "dataset_123", "name": "order_id", "position": 0},
            ],
        }

    def table(self, table):
        return Query(self, table)


class TestLLM:
    def generate(self, agent, _system_prompt, _context, response_model):
        try:
            return response_model.model_validate_json(self.response(agent))
        except ValueError as error:
            raise RuntimeError(f"agent={agent!r}: {error}") from error


class Planner(TestLLM):
    def response(self, agent):
        if agent == "supervisor":
            return (
                '{"focus_areas":["Sales performance"],"kpi_fields":["amount"],'
                '"trend_fields":["amount"],"anomaly_fields":["amount"],"forecast_fields":["amount"]}'
            )
        if agent == "anomaly":
            return (
                '{"anomalies":[{"dataset":"sales","column":"amount","timestamp":null,'
                '"value":99.0,"expected":15.0,"score":2.5,"reason":"Outside expected range"}]}'
            )
        if agent == "forecast":
            return (
                '{"forecasts":[{"available":true,"model":"linear","target":"amount",'
                '"granularity":"monthly","horizon":2,"backtest_mape":12.5,'
                '"points":[{"timestamp":"2026-01-01","actual":null,"prediction":35.0,'
                '"lower_bound":30.0,"upper_bound":40.0}],"reason":null}]}'
            )
        if agent == "insights":
            return (
                '{"insights":[{"type":"summary","title":"Amount is rising",'
                '"text":"Amount increased.","evidence":["kpis[0]","trends[0]"]}],'
                '"recommendations":[{"title":"Monitor amount","action":"Review monthly changes",'
                '"priority":"medium","reason":"An unusual amount was detected.",'
                '"evidence":["anomalies[0]"]}]}'
            )
        if agent == "layout":
            return (
                '{"charts":[{"id":"amount_over_time","title":"Amount over time",'
                '"type":"line","dataset":"sales","x_axis":"order_id",'
                '"series":[{"name":"Amount","column":"amount"}],'
                '"description":"Amount by order.","sql":"SELECT order_id, amount FROM sales"}]}'
            )
        return (
            '{"kpis":[{"name":"Amount","value":30.0,"unit":null,"period":null,'
            '"delta_pct":null,"trend":"unknown","sql":"SELECT SUM(amount) FROM dataset"}],'
            '"trends":[{"field":"amount","direction":"up","summary":"Amount increased",'
            '"period":null,"change_pct":null,"sql":"SELECT amount FROM dataset"}]}'
        )


class RecordingPlanner(Planner):
    def __init__(self):
        self.agents = set()

    def generate(self, agent, system_prompt, context, response_model):
        self.agents.add(agent)
        return super().generate(agent, system_prompt, context, response_model)


class UnavailableWorkersPlanner(Planner):
    def generate(self, agent, system_prompt, context, response_model):
        if agent in {"kpi", "anomaly", "forecast"}:
            raise RuntimeError("worker unavailable")
        if agent == "insights":
            return response_model.model_validate(
                {"insights": [], "recommendations": []}
            )
        return super().generate(agent, system_prompt, context, response_model)


class UnknownFieldPlanner(TestLLM):
    def response(self, *_args):
        return (
            '{"focus_areas":["Sales performance"],"kpi_fields":["missing"],'
            '"trend_fields":[],"anomaly_fields":[],"forecast_fields":[]}'
        )


class InvalidPlanner(TestLLM):
    def response(self, *_args):
        return "not json"


def test_dashboard_graph_delegates_to_planner_agent(monkeypatch):
    expected = {"focus_areas": ["Sales performance"]}
    monkeypatch.setattr(
        "app.dashboard.nodes.analysis.agents.plan_dashboard_analysis", lambda *_: expected
    )

    assert analysis_nodes.plan_dashboard_analysis(Planner(), {}) == {
        "analysis_plan": expected
    }


def test_dashboard_graph_runs_full_skeleton_flow():
    db = Database()
    result = build_dashboard_graph(db, Planner()).invoke(
        {
            "analysis_id": "analysis_123",
            "dataset_id": "dataset_123",
        }
    )

    assert result["analysis_id"] == "analysis_123"
    assert result["dataset_id"] == "dataset_123"
    assert result["schema"]["dataset"]["name"] == "sales"
    assert [field["name"] for field in result["schema"]["fields"]] == ["order_id", "amount"]
    assert result["analysis_plan"]["kpi_fields"] == ["amount"]
    assert result["kpis"][0]["value"] == 30.0
    assert result["trends"][0]["field"] == "amount"
    assert result["anomalies"][0]["column"] == "amount"
    assert result["forecasts"][0]["target"] == "amount"
    assert result["insights"][0]["evidence"] == ["kpis[0]", "trends[0]"]
    assert result["recommendations"][0]["evidence"] == ["anomalies[0]"]
    assert result["dashboard"]["charts"][0]["id"] == "amount_over_time"
    assert result["errors"] == []
    assert result["dashboard"]["kpis"] == result["kpis"]
    assert result["dashboard"]["generated_at"] == result["generated_at"]
    assert db.rows["analysis_runs"][0]["dashboard"] == result["dashboard"]


def test_dashboard_graph_uses_dedicated_agent_configurations():
    llm = RecordingPlanner()

    build_dashboard_graph(Database(), llm).invoke(
        {"analysis_id": "analysis_123", "dataset_id": "dataset_123"}
    )

    assert llm.agents == {"supervisor", "kpi", "anomaly", "forecast", "insights", "layout"}


def test_dashboard_graph_persists_worker_unavailable_warnings():
    result = build_dashboard_graph(Database(), UnavailableWorkersPlanner()).invoke(
        {"analysis_id": "analysis_123", "dataset_id": "dataset_123"}
    )

    assert result["kpis"] == []
    assert result["anomalies"] == []
    assert result["forecasts"][0]["available"] is False
    assert set(result["errors"]) == {
        "KPI worker output was unavailable.",
        "Anomaly worker output was unavailable.",
        "Forecast worker output was unavailable.",
    }


def test_load_dataset_context_rejects_mismatched_analysis_run():
    with pytest.raises(ValueError, match="does not match"):
        load_dataset_context(
            DashboardRepository(Database()),
            {"analysis_id": "analysis_123", "dataset_id": "dataset_456"},
        )


def test_load_dataset_context_returns_the_linked_dataset_and_fields():
    context = DashboardRepository(Database()).load_dataset_context(
        "analysis_123", "dataset_123"
    )

    assert context["dataset"]["id"] == "dataset_123"
    assert context["dataset"]["name"] == "sales"
    assert [field["name"] for field in context["fields"]] == ["order_id", "amount"]


def test_load_dataset_context_rejects_cross_workspace_dataset():
    db = Database()
    db.rows["datasets"][0]["workspace_id"] = "workspace_456"

    with pytest.raises(ValueError, match="different workspaces"):
        DashboardRepository(db).load_dataset_context(
            "analysis_123", "dataset_123"
        )


def test_plan_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown fields"):
        dashboard_agents.plan_dashboard_analysis(
            UnknownFieldPlanner(),
            {"fields": [{"name": "amount"}]}
        )


def test_plan_rejects_invalid_model_response():
    with pytest.raises(RuntimeError, match="Invalid JSON"):
        dashboard_agents.plan_dashboard_analysis(
            InvalidPlanner(),
            {"fields": [{"name": "amount"}]}
        )


class InvalidTrendPlanner(TestLLM):
    def response(self, *_args):
        return "not json"


def test_kpi_and_trend_worker_omits_invalid_model_response():
    result = dashboard_agents.calculate_kpis_and_trends(
        InvalidTrendPlanner(),
        {"fields": [{"name": "amount"}]},
        {"kpi_fields": ["amount"], "trend_fields": ["amount"]},
    )

    assert result == {
        "kpis": [],
        "trends": [],
        "errors": ["KPI worker output was unavailable."],
    }


class InvalidAnomalyPlanner(TestLLM):
    def response(self, *_args):
        return "not json"


def test_anomaly_worker_omits_invalid_model_response():
    result = dashboard_agents.detect_anomalies(
        InvalidAnomalyPlanner(),
        {"fields": [{"name": "amount"}]},
        {"anomaly_fields": ["amount"]},
    )

    assert result == {
        "anomalies": [],
        "errors": ["Anomaly worker output was unavailable."],
    }


class InvalidForecastPlanner(TestLLM):
    def response(self, *_args):
        return "not json"


def test_forecast_worker_returns_unavailable_for_invalid_model_response():
    result = dashboard_agents.generate_forecasts(
        InvalidForecastPlanner(),
        {"fields": [{"name": "amount"}]},
        {"forecast_fields": ["amount"]},
    )

    assert result["forecasts"][0]["available"] is False
    assert result["errors"] == ["Forecast worker output was unavailable."]


class InvalidInsightPlanner(TestLLM):
    def response(self, *_args):
        return "not json"


def test_insight_synthesis_rejects_invalid_model_response():
    with pytest.raises(RuntimeError, match="Invalid JSON"):
        dashboard_agents.synthesise_insights(
            InvalidInsightPlanner(),
            [], [], [], []
        )


class InvalidDashboardPlanner(TestLLM):
    def response(self, *_args):
        return "not json"


def test_dashboard_layout_rejects_invalid_model_response():
    with pytest.raises(RuntimeError, match="Invalid JSON"):
        dashboard_agents.build_dashboard(
            InvalidDashboardPlanner(),
            {"fields": [{"name": "amount"}]},
            [], [], [], [], [], [],
        )


def test_validate_dashboard_reports_invalid_chart_configuration():
    errors = DashboardValidationService().validate(
        {
            "charts": [
                {
                    "id": "amount",
                    "title": "Amount",
                    "type": "line",
                    "dataset": "sales",
                    "x_axis": None,
                    "series": [],
                    "sql": "",
                },
                {
                    "id": "amount",
                    "title": "Amount by order",
                    "type": "bar",
                    "dataset": "sales",
                    "series": [{"name": "", "column": "amount"}],
                    "sql": "SELECT amount FROM sales",
                },
            ]
        }
    )

    assert "Dashboard chart IDs must be unique" in errors
    assert "Dashboard chart 'amount' SQL cannot be blank" in errors
    assert "Dashboard chart 'amount' requires an x-axis" in errors
    assert "Dashboard chart 'amount' requires at least one series" in errors
    assert "Dashboard chart 'amount' has a blank series name or column" in errors


def test_validate_dashboard_reports_schema_errors():
    errors = DashboardValidationService().validate({"charts": [{"id": "amount"}]})

    assert any(error.startswith("charts.0.title:") for error in errors)


def test_persist_dashboard_saves_layout_and_marks_analysis_ready():
    db = Database()
    dashboard = {
        "charts": [
            {
                "id": "amount",
                "title": "Amount",
                "type": "bar",
                "dataset": "sales",
                "series": [{"name": "Amount", "column": "amount"}],
                "sql": "SELECT amount FROM sales",
            }
        ]
    }

    DashboardRepository(db).persist_dashboard("analysis_123", "dataset_123", dashboard)

    analysis = db.rows["analysis_runs"][0]
    assert analysis["dashboard"] == dashboard
    assert analysis["status"] == "dashboard_ready"


def test_persist_dashboard_rejects_mismatched_dataset():
    with pytest.raises(ValueError, match="does not match"):
        DashboardRepository(Database()).persist_dashboard(
            "analysis_123", "dataset_456", {"charts": []}
        )


def test_mark_analysis_failed_saves_stage_and_diagnostic():
    db = Database()

    DashboardRepository(db).mark_analysis_failed(
        "analysis_123", "dashboard_generation", "dashboard model is unavailable"
    )

    analysis = db.rows["analysis_runs"][0]
    assert analysis["status"] == "failed"
    assert analysis["failure_stage"] == "dashboard_generation"
    assert analysis["failure_diagnostic"] == "dashboard model is unavailable"
