"""Run-scoped state for dashboard generation."""

from operator import add
from typing import Annotated, Any, Required, TypedDict


class DashboardState(TypedDict, total=False):
    analysis_id: Required[str]
    dataset_ids: Required[list[str]]
    schema: dict[str, Any]
    analysis_plan: dict[str, Any]
    kpis: list[dict[str, Any]]
    trends: list[dict[str, Any]]
    anomalies: list[dict[str, Any]]
    forecasts: list[dict[str, Any]]
    insights: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    dashboard: dict[str, Any]
    errors: Annotated[list[str], add]
    generated_at: str
