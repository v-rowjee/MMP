"""Dashboard output contracts for analytics visualisation and insights."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# -------------------------
# Dataset metadata
# -------------------------


class DatasetMetadata(BaseModel):
    """High-level information about the analysed dataset."""

    name: str
    source_filename: str

    row_count: int
    column_count: int
    size_bytes: int

    uploaded_at: datetime

    time_column: str | None = None
    primary_key: str | None = None

    description: str | None = None


class DataSummary(BaseModel):
    """Statistical summary of the dataset."""

    numeric_columns: int
    categorical_columns: int
    text_columns: int
    date_columns: int

    missing_values: int
    duplicate_rows: int

    summary_text: str | None = None


class DashboardAnalysisPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus_areas: list[str] = Field(min_length=1, max_length=5)
    kpi_fields: list[str] = Field(default_factory=list)
    trend_fields: list[str] = Field(default_factory=list)
    anomaly_fields: list[str] = Field(default_factory=list)
    forecast_fields: list[str] = Field(default_factory=list)


# -------------------------
# KPI cards
# -------------------------


class KPI(BaseModel):
    """A computed business metric."""

    name: str
    value: float

    unit: str | None = None
    period: str | None = None

    delta_pct: float | None = None

    trend: Literal[
        "up",
        "down",
        "stable",
        "unknown",
    ] = "unknown"

    sql: str


class Trend(BaseModel):
    """A verified change in a planned dataset field."""

    model_config = ConfigDict(extra="forbid")

    field: str
    direction: Literal["up", "down", "stable", "unknown"]
    summary: str
    period: str | None = None
    change_pct: float | None = None
    sql: str


class KPIAndTrendAnalysis(BaseModel):
    """Structured LLM output for the KPI and trend workflow node."""

    model_config = ConfigDict(extra="forbid")

    kpis: list[KPI] = Field(default_factory=list)
    trends: list[Trend] = Field(default_factory=list)


# -------------------------
# Charts
# -------------------------

ChartType = Literal[
    "line",
    "bar",
    "area",
    "scatter",
    "pie",
    "histogram",
    "table",
]


class ChartSeries(BaseModel):
    """A series displayed on a chart."""

    name: str
    column: str


class ChartConfig(BaseModel):
    """
    Frontend-agnostic chart description.

    The frontend decides how to render it.
    """

    id: str

    title: str

    type: ChartType

    dataset: str

    x_axis: str | None = None

    series: list[ChartSeries] = Field(default_factory=list)

    description: str | None = None

    sql: str


class DashboardLayout(BaseModel):
    """Structured LLM output for the dashboard construction workflow node."""

    model_config = ConfigDict(extra="forbid")

    charts: list[ChartConfig] = Field(default_factory=list)


# -------------------------
# Anomalies
# -------------------------


class Anomaly(BaseModel):
    """A detected abnormal observation."""

    dataset: str

    column: str

    timestamp: str | None = None

    value: float

    expected: float | None = None

    score: float

    reason: str


class AnomalyAnalysis(BaseModel):
    """Structured LLM output for the anomaly detection workflow node."""

    model_config = ConfigDict(extra="forbid")

    anomalies: list[Anomaly] = Field(default_factory=list)


class AnomalySection(BaseModel):
    """Anomaly detection result."""

    available: bool

    method: str | None = None

    items: list[Anomaly] = Field(default_factory=list)

    reason: str | None = None


# -------------------------
# Forecasting
# -------------------------


class ForecastPoint(BaseModel):
    """Single forecast observation."""

    timestamp: str

    actual: float | None = None

    prediction: float

    lower_bound: float | None = None

    upper_bound: float | None = None


class ForecastSection(BaseModel):
    """Forecasting output."""

    available: bool

    model: str | None = None

    target: str | None = None

    granularity: str | None = None

    horizon: int | None = None

    backtest_mape: float | None = None

    points: list[ForecastPoint] = Field(default_factory=list)

    reason: str | None = None


class ForecastAnalysis(BaseModel):
    """Structured LLM output for the forecasting workflow node."""

    model_config = ConfigDict(extra="forbid")

    forecasts: list[ForecastSection] = Field(default_factory=list)


# -------------------------
# Insights
# -------------------------

InsightType = Literal[
    "summary",
    "trend",
    "warning",
    "recommendation",
]


class Insight(BaseModel):
    """LLM-generated interpretation backed by evidence."""

    type: InsightType

    title: str

    text: str

    evidence: list[str]


# -------------------------
# Recommendations
# -------------------------


class Recommendation(BaseModel):
    """Suggested action derived from analytics."""

    title: str

    action: str

    priority: Literal[
        "low",
        "medium",
        "high",
    ]

    reason: str

    evidence: list[str]


class InsightSynthesis(BaseModel):
    """Structured LLM output for the insight synthesis workflow node."""

    model_config = ConfigDict(extra="forbid")

    insights: list[Insight] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)


# -------------------------
# Dashboard
# -------------------------


class Dashboard(BaseModel):
    """
    Complete analytics dashboard response.

    This is the frozen contract consumed by the frontend.
    """

    model_config = ConfigDict(frozen=True)

    workspace_id: str

    generated_at: datetime

    # Dataset understanding

    metadata: list[DatasetMetadata]

    summary: DataSummary

    # Main analytics

    kpis: list[KPI]

    charts: list[ChartConfig]

    anomalies: AnomalySection

    forecast: ForecastSection

    # AI layer

    insights: list[Insight]

    recommendations: list[Recommendation]

    warnings: list[str] = Field(default_factory=list)
