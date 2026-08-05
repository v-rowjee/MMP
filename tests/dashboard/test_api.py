from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.dashboard import router
from app.core.deps import workspace
from app.dashboard import service as dashboard_service
from app.schemas.dashboard import (
    AnomalySection,
    Dashboard,
    DataSummary,
    DatasetMetadata,
    ForecastSection,
)


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
    app.state.settings = SimpleNamespace(upload_bucket="upload")
    app.include_router(router)
    app.dependency_overrides[workspace] = lambda: "ws_12345678"
    expected = dashboard()

    class DashboardService:
        def __init__(self, db, upload_bucket):
            assert db is app.state.db
            assert upload_bucket == "upload"

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


def test_get_dashboard_uses_the_workspace_resolved_from_the_jwt(monkeypatch):
    app = FastAPI()
    app.state.db = SimpleNamespace()
    app.state.settings = SimpleNamespace(upload_bucket="upload")
    app.include_router(router)
    app.dependency_overrides[workspace] = lambda: "ws_12345678"
    expected = dashboard()

    class DashboardService:
        def __init__(self, db, upload_bucket):
            assert db is app.state.db
            assert upload_bucket == "upload"

        def get_dashboard(self, workspace_id):
            assert workspace_id == "ws_12345678"
            return expected

    monkeypatch.setattr("app.api.dashboard.DashboardService", DashboardService)

    response = TestClient(app).get("/dashboard")

    assert response.status_code == 200
    assert response.json()["workspace_id"] == "ws_12345678"


def test_get_dashboard_rejects_a_missing_bearer_token():
    app = FastAPI()
    app.state.db = SimpleNamespace()
    app.include_router(router)

    response = TestClient(app).get("/dashboard")

    assert response.status_code == 401


def test_dashboard_routes_reject_an_invalid_bearer_token():
    app = FastAPI()
    app.state.db = SimpleNamespace(
        auth=SimpleNamespace(get_user=lambda _: (_ for _ in ()).throw(ValueError()))
    )
    app.include_router(router)

    response = TestClient(app).post(
        "/dashboard", headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401


def test_dashboard_routes_publish_the_supabase_bearer_scheme():
    app = FastAPI()
    app.include_router(router)

    schema = app.openapi()

    assert schema["components"]["securitySchemes"]["SupabaseBearer"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter a Supabase user access token.",
    }
    for operation in ("post", "get"):
        assert schema["paths"]["/dashboard"][operation]["security"] == [
            {"SupabaseBearer": []}
        ]


def test_dashboard_service_returns_dashboard_schema(monkeypatch):
    uploaded_at = datetime.now(timezone.utc)
    state = {
        "schema": {
            "datasets": [
                {
                    "name": "sales",
                    "source_filename": "sales.csv",
                    "row_count": 2,
                    "profile": {"column_count": 2, "missing_values": 0},
                    "uploaded_at": uploaded_at,
                    "fields": [
                        {"name": "amount", "dtype": "Int64", "role": "measure"},
                        {"name": "customer", "dtype": "String", "role": "dimension"},
                    ],
                },
                {
                    "name": "inventory",
                    "source_filename": "inventory.csv",
                    "row_count": 3,
                    "profile": {"column_count": 1, "missing_values": 1},
                    "uploaded_at": uploaded_at,
                    "fields": [
                        {"name": "stock", "dtype": "Int64", "role": "measure"},
                    ],
                },
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
        def __init__(self, _, _upload_bucket="upload"):
            pass

        def create_analysis_for_workspace(self, workspace_id):
            assert workspace_id == "ws_12345678"
            return {"id": "analysis_123", "dataset_ids": ["dataset_123", "dataset_456"]}

    class Graph:
        def invoke(self, input):
            assert input == {
                "analysis_id": "analysis_123",
                "dataset_ids": ["dataset_123", "dataset_456"],
            }
            return state

    monkeypatch.setattr(dashboard_service, "DashboardRepository", Repository)
    monkeypatch.setattr(
        "app.dashboard.graph.build_dashboard_graph", lambda *_: Graph()
    )

    response = dashboard_service.DashboardService(
        SimpleNamespace(), SimpleNamespace()
    ).generate_dashboard("ws_12345678")

    assert response.workspace_id == "ws_12345678"
    assert response.summary.numeric_columns == 2
    assert response.summary.text_columns == 1
    assert [metadata.name for metadata in response.metadata] == ["sales", "inventory"]
    assert response.summary.missing_values == 1
    assert response.forecast.available is False


def test_dashboard_service_marks_the_analysis_failed_when_the_graph_raises(monkeypatch):
    failure: dict[str, str] = {}

    class Repository:
        def __init__(self, _, _upload_bucket="upload"):
            pass

        def create_analysis_for_workspace(self, workspace_id):
            assert workspace_id == "ws_12345678"
            return {"id": "analysis_123", "dataset_ids": ["dataset_123", "dataset_456"]}

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
        "app.dashboard.graph.build_dashboard_graph", lambda *_: Graph()
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


def test_dashboard_service_returns_the_persisted_dashboard(monkeypatch):
    generated_at = datetime.now(timezone.utc)
    stored_dashboard = {
        "generated_at": generated_at.isoformat(),
        "kpis": [
            {
                "name": "Amount",
                "value": 30.0,
                "unit": None,
                "period": None,
                "delta_pct": None,
                "trend": "unknown",
                "sql": "SELECT SUM(amount) FROM sales",
            }
        ],
        "charts": [],
        "anomalies": [],
        "forecasts": [],
        "insights": [],
        "recommendations": [],
        "warnings": [],
    }
    schema = {
        "datasets": [
            {
                "name": "sales",
                "source_filename": "sales.csv",
                "row_count": 2,
                "profile": {"column_count": 2, "missing_values": 0},
                "uploaded_at": generated_at,
                "fields": [
                    {"name": "amount", "dtype": "Int64", "role": "measure"},
                    {"name": "customer", "dtype": "String", "role": "dimension"},
                ],
            }
        ]
    }

    class Repository:
        def __init__(self, _, _upload_bucket="upload"):
            pass

        def load_latest_dashboard(self, workspace_id):
            assert workspace_id == "ws_12345678"
            return {
                "id": "analysis_123",
                "dashboard": stored_dashboard,
            }

        def load_dataset_context(self, analysis_id):
            assert analysis_id == "analysis_123"
            return schema

    monkeypatch.setattr(dashboard_service, "DashboardRepository", Repository)

    response = dashboard_service.DashboardService(
        SimpleNamespace(), SimpleNamespace()
    ).get_dashboard("ws_12345678")

    assert response.generated_at == generated_at
    assert response.kpis[0].value == 30.0
