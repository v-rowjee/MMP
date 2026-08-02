"""Anomaly detection agent."""

from typing import Any

from app.schemas.dashboard import AnomalyAnalysis


def detect_anomalies(
    llm: Any,
    schema: dict[str, Any],
    analysis_plan: dict[str, Any],
) -> dict[str, Any]:
    try:
        results = llm.generate(
            "anomaly",
            "anomalies",
            {"schema": schema, "analysis_plan": analysis_plan},
            AnomalyAnalysis,
        ).model_dump()
    except RuntimeError:
        return {
            "anomalies": [],
            "errors": ["Anomaly worker output was unavailable."],
        }
    fields = {field["name"] for field in schema.get("fields", [])}
    anomaly_fields = set(analysis_plan.get("anomaly_fields", []))
    dataset_name = schema.get("dataset", {}).get("name")
    if any(
        anomaly["column"] not in fields
        or anomaly["column"] not in anomaly_fields
        or dataset_name and anomaly["dataset"] != dataset_name
        for anomaly in results["anomalies"]
    ):
        return {
            "anomalies": [],
            "errors": ["Anomaly worker output contained invalid fields."],
        }
    return results
