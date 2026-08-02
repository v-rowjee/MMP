"""Forecast generation agent."""

from typing import Any

from app.schemas.dashboard import ForecastAnalysis


def generate_forecasts(
    llm: Any,
    schema: dict[str, Any],
    analysis_plan: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    results = llm.generate(
        "dashboard",
        "forecasts",
        {"schema": schema, "analysis_plan": analysis_plan},
        ForecastAnalysis,
    ).model_dump()
    fields = {field["name"] for field in schema.get("fields", [])}
    forecast_fields = set(analysis_plan.get("forecast_fields", []))
    if any(
        forecast["available"]
        and (
            forecast["target"] not in fields
            or forecast["target"] not in forecast_fields
        )
        for forecast in results["forecasts"]
    ):
        raise ValueError("Forecast analysis contains unplanned or unknown fields")
    return results
