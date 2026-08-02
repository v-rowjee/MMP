"""Insight synthesis agent."""

from pathlib import Path
from typing import Any

from app.schemas.dashboard import InsightSynthesis

PROMPT = Path(__file__).with_suffix(".toon").read_text(encoding="utf-8").strip()


def synthesise_insights(
    llm: Any,
    kpis: list[dict[str, Any]],
    trends: list[dict[str, Any]],
    anomalies: list[dict[str, Any]],
    forecasts: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    context = {
        "kpis": _with_evidence_ids("kpis", kpis),
        "trends": _with_evidence_ids("trends", trends),
        "anomalies": _with_evidence_ids("anomalies", anomalies),
        "forecasts": _with_evidence_ids("forecasts", forecasts),
    }
    results = llm.generate(
        "insights",
        PROMPT,
        context,
        InsightSynthesis,
    ).model_dump()
    evidence_ids = {item["id"] for group in context.values() for item in group}
    outputs = results["insights"] + results["recommendations"]
    if any(
        not output["evidence"]
        or any(evidence not in evidence_ids for evidence in output["evidence"])
        for output in outputs
    ):
        raise ValueError("Insight synthesis contains unsupported evidence")
    return results


def _with_evidence_ids(
    name: str, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        {"id": f"{name}[{index}]", "data": item}
        for index, item in enumerate(items)
    ]
