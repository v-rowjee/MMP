"""Dashboard service façade."""

from datetime import datetime, timezone
from typing import Any

from app.llm.client import OllamaClient
from app.schemas.dashboard import (
    AnomalySection,
    Dashboard,
    DataSummary,
    DatasetMetadata,
    ForecastSection,
)
from app.dashboard.repository import DashboardRepository


class DashboardService:
    def __init__(
        self,
        db: Any,
        llm: Any | None = None,
    ):
        self.db = db
        self.llm = llm or OllamaClient()
        self.repository = DashboardRepository(db)

    def generate_dashboard(self, workspace_id: str) -> Dashboard:
        from app.dashboard.graph import build_dashboard_graph

        analysis = self.repository.create_analysis_for_workspace(workspace_id)
        try:
            state = build_dashboard_graph(self.db, self.llm).invoke(
                {
                    "analysis_id": analysis["id"],
                    "dataset_id": analysis["dataset_id"],
                }
            )
        except Exception as error:
            self.repository.mark_analysis_failed(
                analysis["id"], "dashboard_generation", str(error)
            )
            raise
        return self._build_response(workspace_id, state)

    def get_dashboard(self, workspace_id: str) -> Dashboard:
        analysis = self.repository.load_latest_dashboard(workspace_id)
        stored_dashboard = analysis["dashboard"]
        state = {
            "schema": self.repository.load_dataset_context(
                analysis["id"], analysis["dataset_id"]
            ),
            "generated_at": stored_dashboard["generated_at"],
            "kpis": stored_dashboard["kpis"],
            "anomalies": stored_dashboard["anomalies"],
            "forecasts": stored_dashboard["forecasts"],
            "insights": stored_dashboard["insights"],
            "recommendations": stored_dashboard["recommendations"],
            "dashboard": stored_dashboard,
            "errors": stored_dashboard["warnings"],
        }
        return self._build_response(workspace_id, state)

    def _build_response(self, workspace_id: str, state: dict[str, Any]) -> Dashboard:
        schema = state["schema"]
        dataset = schema["dataset"]
        fields = schema["fields"]
        profile = dataset["profile"]
        date_columns = sum("date" in field["dtype"].lower() for field in fields)
        numeric_columns = sum(field["role"] == "measure" for field in fields)
        text_columns = sum(
            field["role"] == "dimension" and "date" not in field["dtype"].lower()
            for field in fields
        )
        forecasts = state.get("forecasts", [])
        anomalies = state.get("anomalies", [])

        return Dashboard(
            workspace_id=workspace_id,
            generated_at=state.get("generated_at", datetime.now(timezone.utc)),
            metadata=[
                DatasetMetadata(
                    name=dataset["name"],
                    source_filename=dataset["source_filename"],
                    row_count=dataset["row_count"],
                    column_count=profile["column_count"],
                    uploaded_at=dataset["uploaded_at"],
                )
            ],
            summary=DataSummary(
                numeric_columns=numeric_columns,
                categorical_columns=0,
                text_columns=text_columns,
                date_columns=date_columns,
                missing_values=profile.get("missing_values", 0),
            ),
            kpis=state.get("kpis", []),
            charts=state["dashboard"].get("charts", []),
            anomalies=AnomalySection(
                available=bool(anomalies),
                items=anomalies,
                reason=None if anomalies else "No anomalies were detected.",
            ),
            forecast=(
                ForecastSection.model_validate(forecasts[0])
                if forecasts
                else ForecastSection(
                    available=False,
                    reason="No forecast was generated.",
                )
            ),
            insights=state.get("insights", []),
            recommendations=state.get("recommendations", []),
            warnings=state.get("errors", []),
        )
