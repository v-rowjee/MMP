"""Dashboard layout construction agent."""

from pathlib import Path
from typing import Any

from app.schemas.dashboard import DashboardLayout

PROMPT = (Path(__file__).parent / "prompts" / "layout.toon").read_text(
    encoding="utf-8"
).strip()


def build_dashboard(
    llm: Any,
    schema: dict[str, Any],
    kpis: list[dict[str, Any]],
    trends: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
    forecasts: list[dict[str, Any]],
    insights: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    dashboard = llm.generate(
        "layout",
        PROMPT,
        {
            "schema": schema,
            "kpis": kpis,
            "trends": trends,
            "anomalies": anomalies,
            "forecasts": forecasts,
            "insights": insights,
            "recommendations": recommendations,
        },
        DashboardLayout,
    ).model_dump()
    fields = {field["name"] for field in schema.get("fields", [])}
    dataset_name = schema.get("dataset", {}).get("name")
    if any(
        dataset_name and chart["dataset"] != dataset_name
        or chart["x_axis"] is not None and chart["x_axis"] not in fields
        or any(series["column"] not in fields for series in chart["series"])
        for chart in dashboard["charts"]
    ):
        raise ValueError("Dashboard layout contains unknown fields")
    return dashboard
