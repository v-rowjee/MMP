"""Dashboard analysis planning agent."""

from typing import Any

from app.schemas.dashboard import DashboardAnalysisPlan
from app.services.dashboard.structured_output import DashboardStructuredOutputService


def plan_dashboard_analysis(
    structured_output: DashboardStructuredOutputService,
    schema: dict[str, Any],
) -> dict[str, Any]:
    plan = structured_output.request(
        "dashboard",
        "dashboard_planner",
        schema,
        DashboardAnalysisPlan,
        "Invalid dashboard analysis plan",
    )
    fields = {field["name"] for field in schema.get("fields", [])}
    selected_fields = (
        plan["kpi_fields"]
        + plan["trend_fields"]
        + plan["anomaly_fields"]
        + plan["forecast_fields"]
    )
    if any(field not in fields for field in selected_fields):
        raise ValueError("Analysis plan contains unknown fields")
    return plan
