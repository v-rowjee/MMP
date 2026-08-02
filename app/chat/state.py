"""Run-scoped state for dataset chat."""

from typing import Any, TypedDict


class ChatState(TypedDict, total=False):
    analysis_id: str
    dataset_id: str
    session_id: str
    question: str
    history: list[dict[str, Any]]
    schema: dict[str, Any]
    dashboard_context: dict[str, Any]
    route: str
    query_plan: dict[str, Any] | None
    sql: str | None
    query_result: list[dict[str, Any]]
    answer: str
    errors: list[str]
