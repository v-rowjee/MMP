from types import SimpleNamespace

import pytest

from app.graph.dashboard import DashboardWorkflow, build_dashboard_graph
from app.services.dashboard.service import DashboardService


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
            "analysis_runs": [{"id": "analysis_123", "dataset_id": "dataset_123"}],
            "datasets": [
                {
                    "id": "dataset_123",
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


class Planner:
    def chat(self, _, messages, **_kwargs):
        prompt = messages[0]["content"]
        if "task: plan_analysis" in prompt:
            return (
                '{"focus_areas":["Sales performance"],"kpi_fields":["amount"],'
                '"trend_fields":["amount"],"anomaly_fields":["amount"],"forecast_fields":["amount"]}'
            )
        if "task: detect_anomalies" in prompt:
            return (
                '{"anomalies":[{"dataset":"sales","column":"amount","timestamp":null,'
                '"value":99.0,"expected":15.0,"score":2.5,"reason":"Outside expected range"}]}'
            )
        if "task: generate_forecasts" in prompt:
            return (
                '{"forecasts":[{"available":true,"model":"linear","target":"amount",'
                '"granularity":"monthly","horizon":2,"backtest_mape":12.5,'
                '"points":[{"timestamp":"2026-01-01","actual":null,"prediction":35.0,'
                '"lower_bound":30.0,"upper_bound":40.0}],"reason":null}]}'
            )
        if "task: synthesise_insights" in prompt:
            return (
                '{"insights":[{"type":"summary","title":"Amount is rising",'
                '"text":"Amount increased.","evidence":["kpis[0]","trends[0]"]}],'
                '"recommendations":[{"title":"Monitor amount","action":"Review monthly changes",'
                '"priority":"medium","reason":"An unusual amount was detected.",'
                '"evidence":["anomalies[0]"]}]}'
            )
        if "task: build_dashboard_layout" in prompt:
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


class UnknownFieldPlanner:
    def chat(self, *_args, **_kwargs):
        return (
            '{"focus_areas":["Sales performance"],"kpi_fields":["missing"],'
            '"trend_fields":[],"anomaly_fields":[],"forecast_fields":[]}'
        )


class InvalidPlanner:
    def chat(self, *_args, **_kwargs):
        return "not json"


def test_dashboard_graph_runs_full_skeleton_flow():
    result = build_dashboard_graph(Database(), Planner()).invoke(
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


def test_load_dataset_context_rejects_mismatched_analysis_run():
    with pytest.raises(ValueError, match="does not match"):
        DashboardWorkflow(Database()).load_dataset_context(
            {"analysis_id": "analysis_123", "dataset_id": "dataset_456"}
        )


def test_plan_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown fields"):
        DashboardService(Database(), UnknownFieldPlanner()).plan_dashboard_analysis(
            {"fields": [{"name": "amount"}]}
        )


def test_plan_rejects_invalid_model_response():
    with pytest.raises(ValueError, match="Invalid dashboard analysis plan"):
        DashboardService(Database(), InvalidPlanner()).plan_dashboard_analysis(
            {"fields": [{"name": "amount"}]}
        )


class InvalidTrendPlanner:
    def chat(self, *_args, **_kwargs):
        return "not json"


def test_kpi_and_trend_analysis_rejects_invalid_model_response():
    with pytest.raises(ValueError, match="Invalid KPI and trend analysis"):
        DashboardService(Database(), InvalidTrendPlanner()).calculate_kpis_and_trends(
            {"fields": [{"name": "amount"}]},
            {"kpi_fields": ["amount"], "trend_fields": ["amount"]},
        )


class InvalidAnomalyPlanner:
    def chat(self, *_args, **_kwargs):
        return "not json"


def test_anomaly_analysis_rejects_invalid_model_response():
    with pytest.raises(ValueError, match="Invalid anomaly analysis"):
        DashboardService(Database(), InvalidAnomalyPlanner()).detect_anomalies(
            {"fields": [{"name": "amount"}]},
            {"anomaly_fields": ["amount"]},
        )


class InvalidForecastPlanner:
    def chat(self, *_args, **_kwargs):
        return "not json"


def test_forecast_analysis_rejects_invalid_model_response():
    with pytest.raises(ValueError, match="Invalid forecast analysis"):
        DashboardService(Database(), InvalidForecastPlanner()).generate_forecasts(
            {"fields": [{"name": "amount"}]},
            {"forecast_fields": ["amount"]},
        )


class InvalidInsightPlanner:
    def chat(self, *_args, **_kwargs):
        return "not json"


def test_insight_synthesis_rejects_invalid_model_response():
    with pytest.raises(ValueError, match="Invalid insight synthesis"):
        DashboardService(Database(), InvalidInsightPlanner()).synthesise_insights(
            [], [], [], []
        )


class InvalidDashboardPlanner:
    def chat(self, *_args, **_kwargs):
        return "not json"


def test_dashboard_layout_rejects_invalid_model_response():
    with pytest.raises(ValueError, match="Invalid dashboard layout"):
        DashboardService(Database(), InvalidDashboardPlanner()).build_dashboard(
            {"fields": [{"name": "amount"}]},
            [], [], [], [], [], [],
        )


def test_validate_dashboard_reports_invalid_chart_configuration():
    errors = DashboardService(Database()).validate_dashboard(
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
    errors = DashboardService(Database()).validate_dashboard({"charts": [{"id": "amount"}]})

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

    DashboardService(db).persist_dashboard("analysis_123", "dataset_123", dashboard)

    analysis = db.rows["analysis_runs"][0]
    assert analysis["dashboard"] == dashboard
    assert analysis["status"] == "dashboard_ready"


def test_persist_dashboard_rejects_mismatched_dataset():
    with pytest.raises(ValueError, match="does not match"):
        DashboardService(Database()).persist_dashboard(
            "analysis_123", "dataset_456", {"charts": []}
        )
