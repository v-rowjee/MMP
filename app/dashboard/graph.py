"""Dashboard LangGraph wiring."""

from functools import partial
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.dashboard.nodes.analysis import (
    calculate_kpis_and_trends,
    detect_anomalies,
    generate_forecasts,
    plan_dashboard_analysis,
    synthesise_insights,
)
from app.dashboard.nodes.context import load_dataset_context
from app.dashboard.nodes.result import (
    build_dashboard,
    persist_dashboard,
    validate_dashboard,
)
from app.dashboard.repository import DashboardRepository
from app.dashboard.state import DashboardState
from app.dashboard.validation import DashboardValidationService


class DashboardWorkflow:
    def __init__(self, db: Any, llm: Any | None = None):
        self.repository = DashboardRepository(db)
        self.llm = llm
        self.validation = DashboardValidationService()

    def build(self):
        graph = StateGraph(DashboardState)
        graph.add_node("load_dataset_context", partial(load_dataset_context, self.repository))
        graph.add_node("plan_dashboard_analysis", partial(plan_dashboard_analysis, self.llm))
        graph.add_node(
            "calculate_kpis_and_trends", partial(calculate_kpis_and_trends, self.llm)
        )
        graph.add_node("detect_anomalies", partial(detect_anomalies, self.llm))
        graph.add_node("generate_forecasts", partial(generate_forecasts, self.llm))
        graph.add_node("synthesise_insights", partial(synthesise_insights, self.llm))
        graph.add_node("build_dashboard", partial(build_dashboard, self.llm))
        graph.add_node("validate_dashboard", partial(validate_dashboard, self.validation))
        graph.add_node(
            "persist_dashboard",
            partial(persist_dashboard, self.repository, self.validation),
        )

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


def build_dashboard_graph(db: Any, llm: Any | None = None):
    return DashboardWorkflow(db, llm).build()
