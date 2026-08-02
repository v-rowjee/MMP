"""Dashboard workflow agents."""

from app.services.dashboard.agents.anomalies import detect_anomalies
from app.services.dashboard.agents.builder import build_dashboard
from app.services.dashboard.agents.forecasts import generate_forecasts
from app.services.dashboard.agents.insights import synthesise_insights
from app.services.dashboard.agents.kpis_and_trends import calculate_kpis_and_trends
from app.services.dashboard.agents.planner import plan_dashboard_analysis
