"""Dashboard assembly, validation, and persistence nodes."""

from datetime import datetime, timezone
from typing import Any

from app.dashboard import agents
from app.dashboard.repository import DashboardRepository
from app.dashboard.state import DashboardState
from app.dashboard.validation import DashboardValidationService


def build_dashboard(llm: Any, state: DashboardState) -> dict[str, Any]:
    return {
        "dashboard": agents.build_dashboard(
            llm,
            state.get("schema", {}),
            state.get("kpis", []),
            state.get("trends", []),
            state.get("anomalies", []),
            state.get("forecasts", []),
            state.get("insights", []),
            state.get("recommendations", []),
        )
    }


def validate_dashboard(
    validation: DashboardValidationService, state: DashboardState
) -> dict[str, Any]:
    return {"errors": validation.validate(state.get("dashboard", {}))}


def persist_dashboard(
    repository: DashboardRepository,
    validation: DashboardValidationService,
    state: DashboardState,
) -> dict[str, Any]:
    if validation.validate(state.get("dashboard", {})):
        raise ValueError("Dashboard validation failed")
    generated_at = datetime.now(timezone.utc).isoformat()
    dashboard = {
        **state.get("dashboard", {}),
        "generated_at": generated_at,
        "kpis": state.get("kpis", []),
        "trends": state.get("trends", []),
        "anomalies": state.get("anomalies", []),
        "forecasts": state.get("forecasts", []),
        "insights": state.get("insights", []),
        "recommendations": state.get("recommendations", []),
        "warnings": state.get("errors", []),
    }
    repository.persist_dashboard(state["analysis_id"], dashboard)
    return {"dashboard": dashboard, "generated_at": generated_at}
