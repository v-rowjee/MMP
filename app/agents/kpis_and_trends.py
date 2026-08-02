"""KPI and trend analysis agent."""

from typing import Any

from app.schemas.dashboard import KPIAndTrendAnalysis


def calculate_kpis_and_trends(
    llm: Any,
    schema: dict[str, Any],
    analysis_plan: dict[str, Any],
) -> dict[str, Any]:
    try:
        results = llm.generate(
            "kpi",
            "kpis_and_trends",
            {"schema": schema, "analysis_plan": analysis_plan},
            KPIAndTrendAnalysis,
        ).model_dump()
    except RuntimeError:
        return {
            "kpis": [],
            "trends": [],
            "errors": ["KPI worker output was unavailable."],
        }
    fields = {field["name"] for field in schema.get("fields", [])}
    trend_fields = set(analysis_plan.get("trend_fields", []))
    if any(
        trend["field"] not in fields or trend["field"] not in trend_fields
        for trend in results["trends"]
    ):
        return {
            "kpis": [],
            "trends": [],
            "errors": ["KPI worker output contained invalid fields."],
        }
    return results
