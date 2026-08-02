"""Dashboard LLM capabilities and their co-located prompts."""

from .anomalies import detect_anomalies
from .forecasts import generate_forecasts
from .insights import synthesise_insights
from .kpis_and_trends import calculate_kpis_and_trends
from .layout import build_dashboard
from .planner import plan_dashboard_analysis

__all__ = [
    "build_dashboard",
    "calculate_kpis_and_trends",
    "detect_anomalies",
    "generate_forecasts",
    "plan_dashboard_analysis",
    "synthesise_insights",
]
