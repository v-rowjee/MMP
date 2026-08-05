"""LLM-backed dashboard-analysis nodes."""

from typing import Any

from app.dashboard import agents
from app.dashboard.repository import DashboardRepository
from app.dashboard.state import DashboardState


def plan_dashboard_analysis(llm: Any, state: DashboardState) -> dict[str, Any]:
    return {"analysis_plan": agents.plan_dashboard_analysis(llm, state.get("schema", {}))}


def calculate_kpis_and_trends(llm: Any, state: DashboardState) -> dict[str, Any]:
    return agents.calculate_kpis_and_trends(
        llm, state.get("schema", {}), state.get("analysis_plan", {})
    )


def detect_anomalies(
    repository: DashboardRepository, llm: Any, state: DashboardState
) -> dict[str, Any]:
    anomalies: list[dict[str, Any]] = []
    errors: list[str] = []
    for dataset in state.get("schema", {}).get("datasets", []):
        try:
            frame = repository.load_dataset_frame(state["analysis_id"], dataset["id"])
        except ValueError:
            errors.append(f"Anomaly detection data was unavailable for {dataset['name']}.")
            continue
        result = agents.detect_anomalies(
            llm, {"dataset": dataset, "fields": dataset["fields"]}, frame
        )
        anomalies.extend(result["anomalies"])
        errors.extend(result["errors"])
    return {"anomalies": anomalies, "errors": errors}


def generate_forecasts(llm: Any, state: DashboardState) -> dict[str, Any]:
    return agents.generate_forecasts(
        llm, state.get("schema", {}), state.get("analysis_plan", {})
    )


def synthesise_insights(llm: Any, state: DashboardState) -> dict[str, Any]:
    return agents.synthesise_insights(
        llm,
        state.get("kpis", []),
        state.get("trends", []),
        state.get("anomalies", []),
        state.get("forecasts", []),
    )
