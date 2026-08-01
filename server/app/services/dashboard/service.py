"""Dashboard business logic."""

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from app.llm.client import OllamaClient
from app.llm.prompt_loader import PromptLoader
from app.schemas.dashboard import (
    AnomalyAnalysis,
    DashboardAnalysisPlan,
    DashboardLayout,
    ForecastAnalysis,
    KPIAndTrendAnalysis,
    InsightSynthesis,
)


class DashboardService:
    def __init__(
        self,
        db: Any,
        llm: Any | None = None,
        prompts: PromptLoader | None = None,
    ):
        self.db = db
        self.llm = llm or OllamaClient()
        self.prompts = prompts or PromptLoader()

    def _request_structured_output(
        self,
        agent: str,
        prompt_name: str,
        context: dict[str, Any],
        response_model: type[BaseModel],
        error_message: str,
    ) -> dict[str, Any]:
        try:
            instruction = self.prompts.load(prompt_name)
            response = self.llm.chat(
                agent,
                [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": json.dumps(context)},
                ],
                response_format=response_model.model_json_schema(),
            )
            return response_model.model_validate_json(response).model_dump()
        except (RuntimeError, ValidationError, ValueError) as error:
            raise ValueError(error_message) from error

    def load_dataset_context(self, analysis_id: str, dataset_id: str) -> dict[str, Any]:
        analysis = (
            self.db.table("analysis_runs")
            .select("dataset_id")
            .eq("id", analysis_id)
            .maybe_single()
            .execute()
            .data
        )
        if not analysis or analysis["dataset_id"] != dataset_id:
            raise ValueError("Analysis run does not match dataset")

        dataset = (
            self.db.table("datasets")
            .select("id, name, source_filename, row_count, meta")
            .eq("id", dataset_id)
            .maybe_single()
            .execute()
            .data
        )
        if not dataset:
            raise ValueError("Dataset not found")

        fields = (
            self.db.table("dataset_fields")
            .select("name, original_name, position, dtype, role, profile")
            .eq("dataset_id", dataset_id)
            .execute()
            .data
            or []
        )
        return {
            "dataset": {
                "id": dataset["id"],
                "name": dataset["name"],
                "source_filename": dataset["source_filename"],
                "row_count": dataset["row_count"],
                "profile": dataset.get("meta", {}).get("profile", {}),
            },
            "fields": sorted(fields, key=lambda field: field["position"]),
        }

    def plan_dashboard_analysis(self, schema: dict[str, Any]) -> dict[str, Any]:
        plan = self._request_structured_output(
            "dashboard",
            "dashboard_planner",
            schema,
            DashboardAnalysisPlan,
            "Invalid dashboard analysis plan",
        )

        fields = {field["name"] for field in schema.get("fields", [])}
        selected_fields = (
            plan["kpi_fields"]
            + plan["trend_fields"]
            + plan["anomaly_fields"]
            + plan["forecast_fields"]
        )
        if any(field not in fields for field in selected_fields):
            raise ValueError("Analysis plan contains unknown fields")
        return plan

    def calculate_kpis_and_trends(
        self,
        schema: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        results = self._request_structured_output(
            "dashboard",
            "kpis_and_trends",
            {"schema": schema, "analysis_plan": analysis_plan},
            KPIAndTrendAnalysis,
            "Invalid KPI and trend analysis",
        )

        fields = {field["name"] for field in schema.get("fields", [])}
        trend_fields = set(analysis_plan.get("trend_fields", []))
        if any(trend["field"] not in fields or trend["field"] not in trend_fields for trend in results["trends"]):
            raise ValueError("Trend analysis contains unplanned or unknown fields")
        return results

    def detect_anomalies(
        self,
        schema: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        results = self._request_structured_output(
            "dashboard",
            "anomalies",
            {"schema": schema, "analysis_plan": analysis_plan},
            AnomalyAnalysis,
            "Invalid anomaly analysis",
        )

        fields = {field["name"] for field in schema.get("fields", [])}
        anomaly_fields = set(analysis_plan.get("anomaly_fields", []))
        dataset_name = schema.get("dataset", {}).get("name")
        if any(
            anomaly["column"] not in fields
            or anomaly["column"] not in anomaly_fields
            or dataset_name and anomaly["dataset"] != dataset_name
            for anomaly in results["anomalies"]
        ):
            raise ValueError("Anomaly analysis contains unplanned or unknown fields")
        return results

    def generate_forecasts(
        self,
        schema: dict[str, Any],
        analysis_plan: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        results = self._request_structured_output(
            "dashboard",
            "forecasts",
            {"schema": schema, "analysis_plan": analysis_plan},
            ForecastAnalysis,
            "Invalid forecast analysis",
        )

        fields = {field["name"] for field in schema.get("fields", [])}
        forecast_fields = set(analysis_plan.get("forecast_fields", []))
        if any(
            forecast["available"]
            and (
                forecast["target"] not in fields
                or forecast["target"] not in forecast_fields
            )
            for forecast in results["forecasts"]
        ):
            raise ValueError("Forecast analysis contains unplanned or unknown fields")
        return results

    def synthesise_insights(
        self,
        kpis: list[dict[str, Any]],
        trends: list[dict[str, Any]],
        anomalies: list[dict[str, Any]],
        forecasts: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        context = {
            "kpis": self._with_evidence_ids("kpis", kpis),
            "trends": self._with_evidence_ids("trends", trends),
            "anomalies": self._with_evidence_ids("anomalies", anomalies),
            "forecasts": self._with_evidence_ids("forecasts", forecasts),
        }
        results = self._request_structured_output(
            "insights",
            "insights",
            context,
            InsightSynthesis,
            "Invalid insight synthesis",
        )

        evidence_ids = {
            item["id"]
            for group in context.values()
            for item in group
        }
        outputs = results["insights"] + results["recommendations"]
        if any(
            not output["evidence"]
            or any(evidence not in evidence_ids for evidence in output["evidence"])
            for output in outputs
        ):
            raise ValueError("Insight synthesis contains unsupported evidence")
        return results

    @staticmethod
    def _with_evidence_ids(
        name: str, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {"id": f"{name}[{index}]", "data": item}
            for index, item in enumerate(items)
        ]

    def build_dashboard(
        self,
        schema: dict[str, Any],
        kpis: list[dict[str, Any]],
        trends: list[dict[str, Any]],
        anomalies: list[dict[str, Any]],
        forecasts: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        context = {
            "schema": schema,
            "kpis": kpis,
            "trends": trends,
            "anomalies": anomalies,
            "forecasts": forecasts,
            "insights": insights,
            "recommendations": recommendations,
        }
        dashboard = self._request_structured_output(
            "dashboard",
            "dashboard_builder",
            context,
            DashboardLayout,
            "Invalid dashboard layout",
        )

        fields = {field["name"] for field in schema.get("fields", [])}
        dataset_name = schema.get("dataset", {}).get("name")
        if any(
            dataset_name and chart["dataset"] != dataset_name
            or chart["x_axis"] is not None and chart["x_axis"] not in fields
            or any(series["column"] not in fields for series in chart["series"])
            for chart in dashboard["charts"]
        ):
            raise ValueError("Dashboard layout contains unknown fields")
        return dashboard

    def validate_dashboard(self, dashboard: dict[str, Any]) -> list[str]:
        try:
            layout = DashboardLayout.model_validate(dashboard)
        except ValidationError as error:
            return [
                f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                for item in error.errors()
            ]

        errors: list[str] = []
        chart_ids = [chart.id for chart in layout.charts]
        if len(chart_ids) != len(set(chart_ids)):
            errors.append("Dashboard chart IDs must be unique")

        for chart in layout.charts:
            if not chart.id.strip():
                errors.append("Dashboard chart ID cannot be blank")
            if not chart.title.strip():
                errors.append(f"Dashboard chart {chart.id!r} title cannot be blank")
            if not chart.dataset.strip():
                errors.append(f"Dashboard chart {chart.id!r} dataset cannot be blank")
            if not chart.sql.strip():
                errors.append(f"Dashboard chart {chart.id!r} SQL cannot be blank")
            if chart.type in {"line", "area", "scatter"} and chart.x_axis is None:
                errors.append(f"Dashboard chart {chart.id!r} requires an x-axis")
            if chart.type != "table" and not chart.series:
                errors.append(f"Dashboard chart {chart.id!r} requires at least one series")
            if any(not series.name.strip() or not series.column.strip() for series in chart.series):
                errors.append(f"Dashboard chart {chart.id!r} has a blank series name or column")
        return errors

    def persist_dashboard(
        self,
        analysis_id: str,
        dataset_id: str,
        dashboard: dict[str, Any],
    ) -> None:
        if self.validate_dashboard(dashboard):
            raise ValueError("Dashboard validation failed")

        analysis = (
            self.db.table("analysis_runs")
            .select("dataset_id")
            .eq("id", analysis_id)
            .maybe_single()
            .execute()
            .data
        )
        if not analysis or analysis["dataset_id"] != dataset_id:
            raise ValueError("Analysis run does not match dataset")

        try:
            (
                self.db.table("analysis_runs")
                .update({"dashboard": dashboard, "status": "dashboard_ready"})
                .eq("id", analysis_id)
                .execute()
            )
        except Exception as error:
            raise RuntimeError("Dashboard persistence failed") from error
