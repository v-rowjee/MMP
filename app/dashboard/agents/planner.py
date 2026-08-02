"""Dashboard analysis planning agent."""

from pathlib import Path
from typing import Any

from app.schemas.dashboard import DashboardAnalysisPlan

PROMPT = Path(__file__).with_suffix(".toon").read_text(encoding="utf-8").strip()


def plan_dashboard_analysis(
    llm: Any,
    schema: dict[str, Any],
) -> dict[str, Any]:
    plan = llm.generate(
        "supervisor",
        PROMPT,
        schema,
        DashboardAnalysisPlan,
    ).model_dump()
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
