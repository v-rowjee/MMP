"""Dashboard LangGraph workflow skeleton."""

from typing import Any, Required, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents import (
    build_dashboard,
    calculate_kpis_and_trends,
    detect_anomalies,
    generate_forecasts,
    plan_dashboard_analysis,
    synthesise_insights,
)
from app.services.dashboard.repository import DashboardRepository
from app.services.dashboard.validation import DashboardValidationService


class DashboardState(TypedDict, total=False):
    analysis_id: Required[str]
    dataset_id: Required[str]
    schema: dict[str, Any]
    analysis_plan: dict[str, Any]
    kpis: list[dict[str, Any]]
    trends: list[dict[str, Any]]
    anomalies: list[dict[str, Any]]
    forecasts: list[dict[str, Any]]
    insights: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    dashboard: dict[str, Any]
    errors: list[str]


class DashboardWorkflow:
    def __init__(self, db: Any, llm: Any | None = None):
        self.repository = DashboardRepository(db)
        self.llm = llm
        self.validation = DashboardValidationService()

    def build(self):
        graph = StateGraph(DashboardState)
        graph.add_node("load_dataset_context", self.load_dataset_context)
        graph.add_node("plan_dashboard_analysis", self.plan_dashboard_analysis)
        graph.add_node("calculate_kpis_and_trends", self.calculate_kpis_and_trends)
        graph.add_node("detect_anomalies", self.detect_anomalies)
        graph.add_node("generate_forecasts", self.generate_forecasts)
        graph.add_node("synthesise_insights", self.synthesise_insights)
        graph.add_node("build_dashboard", self.build_dashboard)
        graph.add_node("validate_dashboard", self.validate_dashboard)
        graph.add_node("persist_dashboard", self.persist_dashboard)

        graph.add_edge(START, "load_dataset_context")
        graph.add_edge("load_dataset_context", "plan_dashboard_analysis")
        graph.add_edge("plan_dashboard_analysis", "calculate_kpis_and_trends")
        graph.add_edge("plan_dashboard_analysis", "detect_anomalies")
        graph.add_edge("plan_dashboard_analysis", "generate_forecasts")
        graph.add_edge(
            ["calculate_kpis_and_trends", "detect_anomalies", "generate_forecasts"],
            "synthesise_insights",
        )
        graph.add_edge("synthesise_insights", "build_dashboard")
        graph.add_edge("build_dashboard", "validate_dashboard")
        graph.add_edge("validate_dashboard", "persist_dashboard")
        graph.add_edge("persist_dashboard", END)
        return graph.compile()

    def load_dataset_context(self, state: DashboardState) -> dict[str, Any]:
        return {
            "schema": self.repository.load_dataset_context(
                state["analysis_id"],
                state["dataset_id"],
            )
        }

    def plan_dashboard_analysis(self, state: DashboardState) -> dict[str, Any]:
        return {
            "analysis_plan": plan_dashboard_analysis(
                self.llm,
                state.get("schema", {}),
            )
        }

    def calculate_kpis_and_trends(self, state: DashboardState) -> dict[str, Any]:
        return calculate_kpis_and_trends(
            self.llm,
            state.get("schema", {}),
            state.get("analysis_plan", {}),
        )

    def detect_anomalies(self, state: DashboardState) -> dict[str, Any]:
        return detect_anomalies(
            self.llm,
            state.get("schema", {}),
            state.get("analysis_plan", {}),
        )

    def generate_forecasts(self, state: DashboardState) -> dict[str, Any]:
        return generate_forecasts(
            self.llm,
            state.get("schema", {}),
            state.get("analysis_plan", {}),
        )

    def synthesise_insights(self, state: DashboardState) -> dict[str, Any]:
        return synthesise_insights(
            self.llm,
            state.get("kpis", []),
            state.get("trends", []),
            state.get("anomalies", []),
            state.get("forecasts", []),
        )

    def build_dashboard(self, state: DashboardState) -> dict[str, Any]:
        return {
            "dashboard": build_dashboard(
                self.llm,
                state.get("schema", {}),
                state.get("kpis", []),
                state.get("trends", []),
                state.get("anomalies", []),
                state.get("forecasts", []),
                state.get("insights", []),
                state.get("recommendations", []),
            )
        }

    def validate_dashboard(self, state: DashboardState) -> dict[str, Any]:
        return {
            "errors": self.validation.validate(
                state.get("dashboard", {}),
            )
        }

    def persist_dashboard(self, state: DashboardState) -> dict[str, Any]:
        if self.validation.validate(state.get("dashboard", {})):
            raise ValueError("Dashboard validation failed")
        self.repository.persist_dashboard(
            state["analysis_id"],
            state["dataset_id"],
            state.get("dashboard", {}),
        )
        return {}


def build_dashboard_graph(db: Any, llm: Any | None = None):
    return DashboardWorkflow(db, llm).build()
