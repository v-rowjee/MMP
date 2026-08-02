"""KPI and trend analysis agent."""

from typing import Any

from app.schemas.dashboard import KPIAndTrendAnalysis


def calculate_kpis_and_trends(
    llm: Any,
    schema: dict[str, Any],
    analysis_plan: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    results = llm.generate(
        "dashboard",
        "kpis_and_trends",
        {"schema": schema, "analysis_plan": analysis_plan},
        KPIAndTrendAnalysis,
    ).model_dump()
    fields = {field["name"] for field in schema.get("fields", [])}
    trend_fields = set(analysis_plan.get("trend_fields", []))
    if any(
        trend["field"] not in fields or trend["field"] not in trend_fields
        for trend in results["trends"]
    ):
        raise ValueError("Trend analysis contains unplanned or unknown fields")
    return results
