"""Anomaly detection agent."""

from typing import Any

from app.schemas.dashboard import AnomalyAnalysis


def detect_anomalies(
    llm: Any,
    schema: dict[str, Any],
    analysis_plan: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    results = llm.generate(
        "dashboard",
        "anomalies",
        {"schema": schema, "analysis_plan": analysis_plan},
        AnomalyAnalysis,
    ).model_dump()
    fields = {field["name"] for field in schema.get("fields", [])}
    anomaly_fields = set(analysis_plan.get("anomaly_fields", []))
    dataset_name = schema.get("dataset", {}).get("name")
    if any(
        anomaly["column"] not in fields
        or anomaly["column"] not in anomaly_fields
        or dataset_name and anomaly["dataset"] != dataset_name
        for anomaly in results["anomalies"]
    ):
        raise ValueError("Anomaly analysis contains unplanned or unknown fields")
    return results
