"""KPI and trend analysis agent."""

from pathlib import Path
from typing import Any

from app.schemas.dashboard import KPIAndTrendAnalysis

PROMPT = (Path(__file__).parent / "prompts" / "kpis_and_trends.toon").read_text(
    encoding="utf-8"
).strip()


def calculate_kpis_and_trends(
    llm: Any,
    schema: dict[str, Any],
    analysis_plan: dict[str, Any],
) -> dict[str, Any]:
    try:
        results = llm.generate(
            "kpi",
            PROMPT,
            {"schema": schema, "analysis_plan": analysis_plan},
            KPIAndTrendAnalysis,
        ).model_dump()
    except RuntimeError:
        return {
            "kpis": [],
            "trends": [],
            "errors": ["KPI worker output was unavailable."],
        }
    fields = {
        f"{dataset['name']}.{field['name']}"
        for dataset in schema.get("datasets", [])
        for field in dataset["fields"]
    }
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
