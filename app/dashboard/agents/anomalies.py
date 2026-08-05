"""Anomaly detection agent."""

from math import isfinite
from pathlib import Path
from typing import Any, Iterable, Literal, TypedDict

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

PROMPT = (Path(__file__).parent / "prompts" / "anomalies.toon").read_text(
    encoding="utf-8"
).strip()


class AnomalyDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    reason: str = Field(min_length=1)


class AnomalyDescriptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descriptions: list[AnomalyDescription] = Field(default_factory=list)


class AnomalyEvidence(TypedDict):
    dataset: str
    column: str
    timestamp: str | None
    value: float
    expected: float
    score: float
    direction: Literal["high", "low"]


class IQRAnomaly(TypedDict):
    index: int
    value: float
    expected: float
    score: float
    direction: Literal["high", "low"]


def detect_anomalies(
    llm: Any,
    schema: dict[str, Any],
    frame: pl.DataFrame,
) -> dict[str, Any]:
    anomalies = _find_iqr_anomalies(frame, schema)
    if not anomalies:
        return {"anomalies": [], "errors": []}
    evidence = [
        {"id": f"anomalies[{index}]", **anomaly}
        for index, anomaly in enumerate(anomalies)
    ]
    reasons: dict[str, str] = {}
    errors: list[str] = []
    try:
        descriptions = llm.generate(
            "anomaly",
            PROMPT,
            {"anomalies": evidence},
            AnomalyDescriptions,
        ).model_dump()
    except RuntimeError:
        errors.append("Anomaly explanation worker output was unavailable.")
    else:
        reasons = {
            description["id"]: description["reason"]
            for description in descriptions["descriptions"]
        }
        expected_ids = {item["id"] for item in evidence}
        if len(reasons) != len(descriptions["descriptions"]) or set(reasons) != expected_ids:
            reasons = {}
            errors.append("Anomaly explanation worker output contained invalid evidence.")
    return {
        "anomalies": [
            _format_anomaly(anomaly, reasons.get(f"anomalies[{index}]"))
            for index, anomaly in enumerate(anomalies)
        ],
        "errors": errors,
    }


def _find_iqr_anomalies(
    frame: pl.DataFrame,
    schema: dict[str, Any],
) -> list[AnomalyEvidence]:
    dataset_name = schema.get("dataset", {}).get("name", "")
    timestamp_column = _timestamp_column(frame, schema)
    anomalies: list[AnomalyEvidence] = []
    for column, dtype in frame.schema.items():
        if not dtype.is_numeric():
            continue
        for anomaly in calculate_iqr_anomalies(frame.get_column(column).to_list()):
            row_index = int(anomaly["index"])
            anomalies.append(
                {
                    "dataset": dataset_name,
                    "column": column,
                    "timestamp": (
                        str(frame[timestamp_column][row_index])
                        if timestamp_column is not None
                        else None
                    ),
                    "value": anomaly["value"],
                    "expected": anomaly["expected"],
                    "score": anomaly["score"],
                    "direction": anomaly["direction"],
                }
            )
    return anomalies


def _format_anomaly(anomaly: AnomalyEvidence, reason: str | None) -> dict[str, Any]:
    if reason is None:
        reason = (
            "Above the upper IQR fence"
            if anomaly["direction"] == "high"
            else "Below the lower IQR fence"
        )
    return {
        key: value
        for key, value in anomaly.items()
        if key != "direction"
    } | {"reason": reason}


def calculate_iqr_anomalies(
    values: Iterable[float | int | None],
) -> list[IQRAnomaly]:
    """Return outliers using Tukey's 1.5 IQR fences for one numeric column."""

    numeric_values: list[tuple[int, float]] = []
    for index, value in enumerate(values):
        if value is None:
            continue
        numeric_value = float(value)
        if isfinite(numeric_value):
            numeric_values.append((index, numeric_value))
    if len(numeric_values) < 4:
        return []

    observed_values = [value for _, value in numeric_values]
    lower_quartile = _percentile(observed_values, 0.25)
    upper_quartile = _percentile(observed_values, 0.75)
    interquartile_range = upper_quartile - lower_quartile
    if interquartile_range == 0:
        return []
    lower_fence = lower_quartile - 1.5 * interquartile_range
    upper_fence = upper_quartile + 1.5 * interquartile_range
    expected = _percentile(observed_values, 0.5)

    anomalies: list[IQRAnomaly] = []
    for index, value in numeric_values:
        if lower_fence <= value <= upper_fence:
            continue
        is_high = value > upper_fence
        fence = upper_fence if is_high else lower_fence
        direction: Literal["high", "low"] = "high" if is_high else "low"
        anomalies.append(
            {
                "index": index,
                "value": value,
                "expected": expected,
                "score": abs(value - fence) / interquartile_range,
                "direction": direction,
            }
        )
    return anomalies


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index
    return ordered[lower_index] + fraction * (
        ordered[upper_index] - ordered[lower_index]
    )


def _timestamp_column(frame: pl.DataFrame, schema: dict[str, Any]) -> str | None:
    for field in schema.get("fields", []):
        column = field.get("name")
        dtype = str(field.get("dtype", "")).lower()
        if column in frame.columns and ("date" in dtype or "time" in dtype):
            return column
    return None
