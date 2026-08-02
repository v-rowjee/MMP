"""Placeholder chat nodes kept separate from graph wiring."""

from typing import Any

from app.chat.state import ChatState


def load_chat_context(state: ChatState) -> dict[str, Any]:
    return {"history": state.get("history", []), "schema": state.get("schema", {})}


def classify_question(state: ChatState) -> dict[str, Any]:
    return {"route": state.get("route", "dashboard")}


def retrieve_dashboard_context(state: ChatState) -> dict[str, Any]:
    return {"dashboard_context": state.get("dashboard_context", {})}


def plan_data_query(state: ChatState) -> dict[str, Any]:
    return {"query_plan": state.get("query_plan")}


def generate_sql(state: ChatState) -> dict[str, Any]:
    return {"sql": state.get("sql")}


def validate_sql(state: ChatState) -> dict[str, Any]:
    return {"errors": state.get("errors", [])}


def execute_query(state: ChatState) -> dict[str, Any]:
    return {"query_result": state.get("query_result", [])}


def compose_answer(state: ChatState) -> dict[str, Any]:
    return {"answer": state.get("answer", "")}


def validate_answer(state: ChatState) -> dict[str, Any]:
    return {"errors": state.get("errors", [])}


def persist_message(_: ChatState) -> dict[str, Any]:
    return {}
