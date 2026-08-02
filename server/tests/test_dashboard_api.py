from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.dashboard import router
from app.deps import workspace
from app.schemas.dashboard import (
    AnomalySection,
    Dashboard,
    DataSummary,
    DatasetMetadata,
    ForecastSection,
)
from app.services.dashboard import service as dashboard_service


def dashboard() -> Dashboard:
    return Dashboard(
        workspace_id="ws_12345678",
        generated_at=datetime.now(timezone.utc),
        metadata=[
            DatasetMetadata(
                name="sales",
                source_filename="sales.csv",
                row_count=2,
                column_count=2,
                uploaded_at=datetime.now(timezone.utc),
            )
        ],
        summary=DataSummary(
            numeric_columns=1,
            categorical_columns=0,
            text_columns=1,
            date_columns=0,
            missing_values=0,
        ),
        kpis=[],
        charts=[],
        anomalies=AnomalySection(available=False, reason="No anomalies were detected."),
        forecast=ForecastSection(available=False, reason="No forecast was generated."),
        insights=[],
        recommendations=[],
    )


def test_generate_dashboard_uses_the_workspace_resolved_from_the_jwt(monkeypatch):
    app = FastAPI()
    app.state.db = SimpleNamespace()
    app.include_router(router)
    app.dependency_overrides[workspace] = lambda: "ws_12345678"
    expected = dashboard()

    class DashboardService:
        def __init__(self, db):
            assert db is app.state.db

        def generate_dashboard(self, workspace_id):
            assert workspace_id == "ws_12345678"
            return expected

    monkeypatch.setattr("app.api.dashboard.DashboardService", DashboardService)

    response = TestClient(app).post("/dashboard")

    assert response.status_code == 200
    assert response.json()["workspace_id"] == "ws_12345678"


def test_generate_dashboard_rejects_a_missing_bearer_token():
    app = FastAPI()
    app.state.db = SimpleNamespace()
    app.include_router(router)

    response = TestClient(app).post("/dashboard")

    assert response.status_code == 401


def test_dashboard_service_returns_dashboard_schema(monkeypatch):
    uploaded_at = datetime.now(timezone.utc)
    state = {
        "schema": {
            "dataset": {
                "name": "sales",
                "source_filename": "sales.csv",
                "row_count": 2,
                "profile": {"column_count": 2, "missing_values": 0},
                "uploaded_at": uploaded_at,
            },
            "fields": [
                {"name": "amount", "dtype": "Int64", "role": "measure"},
                {"name": "customer", "dtype": "String", "role": "dimension"},
            ],
        },
        "kpis": [],
        "dashboard": {"charts": []},
        "anomalies": [],
        "forecasts": [],
        "insights": [],
        "recommendations": [],
        "errors": [],
    }

    class Repository:
        def __init__(self, _):
            pass

        def create_analysis_for_workspace(self, workspace_id):
            assert workspace_id == "ws_12345678"
            return {"id": "analysis_123", "dataset_id": "dataset_123"}

    class Graph:
        def invoke(self, input):
            assert input == {"analysis_id": "analysis_123", "dataset_id": "dataset_123"}
            return state

    monkeypatch.setattr(dashboard_service, "DashboardRepository", Repository)
    monkeypatch.setattr(
        "app.graph.dashboard.build_dashboard_graph", lambda *_: Graph()
    )

    response = dashboard_service.DashboardService(
        SimpleNamespace(), SimpleNamespace()
    ).generate_dashboard("ws_12345678")

    assert response.workspace_id == "ws_12345678"
    assert response.summary.numeric_columns == 1
    assert response.summary.text_columns == 1
    assert response.forecast.available is False


def test_dashboard_service_marks_the_analysis_failed_when_the_graph_raises(monkeypatch):
    failure: dict[str, str] = {}

    class Repository:
        def __init__(self, _):
            pass

        def create_analysis_for_workspace(self, workspace_id):
            assert workspace_id == "ws_12345678"
            return {"id": "analysis_123", "dataset_id": "dataset_123"}

        def mark_analysis_failed(self, analysis_id, stage, diagnostic):
            failure.update(
                analysis_id=analysis_id,
                stage=stage,
                diagnostic=diagnostic,
            )

    class Graph:
        def invoke(self, _):
            raise RuntimeError("dashboard model is unavailable")

    monkeypatch.setattr(dashboard_service, "DashboardRepository", Repository)
    monkeypatch.setattr(
        "app.graph.dashboard.build_dashboard_graph", lambda *_: Graph()
    )

    with pytest.raises(RuntimeError, match="dashboard model is unavailable"):
        dashboard_service.DashboardService(
            SimpleNamespace(), SimpleNamespace()
        ).generate_dashboard("ws_12345678")

    assert failure == {
        "analysis_id": "analysis_123",
        "stage": "dashboard_generation",
        "diagnostic": "dashboard model is unavailable",
    }
