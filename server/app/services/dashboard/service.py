"""Dashboard service façade."""

from typing import Any

from app.llm.client import OllamaClient
from app.services.dashboard import agents
from app.services.dashboard.repository import DashboardRepository
from app.services.dashboard.structured_output import DashboardStructuredOutputService
from app.services.dashboard.validation import DashboardValidationService


class DashboardService:
    def __init__(
        self,
        db: Any,
        llm: Any | None = None,
    ):
        self.db = db
        self.llm = llm or OllamaClient()
        self.repository = DashboardRepository(db)
        self.validation = DashboardValidationService()
        self.structured_output = DashboardStructuredOutputService(self.llm)

    def load_dataset_context(self, analysis_id: str, dataset_id: str) -> dict[str, Any]:
        return self.repository.load_dataset_context(analysis_id, dataset_id)

    def plan_dashboard_analysis(self, schema: dict[str, Any]) -> dict[str, Any]:
        return agents.plan_dashboard_analysis(self.structured_output, schema)

    def calculate_kpis_and_trends(
        self,
        schema: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        return agents.calculate_kpis_and_trends(
            self.structured_output, schema, analysis_plan
        )

    def detect_anomalies(
        self,
        schema: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        return agents.detect_anomalies(self.structured_output, schema, analysis_plan)

    def generate_forecasts(
        self,
        schema: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        return agents.generate_forecasts(self.structured_output, schema, analysis_plan)

    def synthesise_insights(
        self,
        kpis: list[dict[str, Any]],
        trends: list[dict[str, Any]],
        anomalies: list[dict[str, Any]],
        forecasts: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        return agents.synthesise_insights(
            self.structured_output, kpis, trends, anomalies, forecasts
        )

    def build_dashboard(
        self,
        schema: dict[str, Any],
        kpis: list[dict[str, Any]],
        trends: list[dict[str, Any]],
        anomalies: list[dict[str, Any]],
        forecasts: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return agents.build_dashboard(
            self.structured_output,
            schema,
            kpis,
            trends,
            anomalies,
            forecasts,
            insights,
            recommendations,
        )

    def validate_dashboard(self, dashboard: dict[str, Any]) -> list[str]:
        return self.validation.validate(dashboard)

    def persist_dashboard(
        self,
        analysis_id: str,
        dataset_id: str,
        dashboard: dict[str, Any],
    ) -> None:
        if self.validate_dashboard(dashboard):
            raise ValueError("Dashboard validation failed")
        self.repository.persist_dashboard(analysis_id, dataset_id, dashboard)
