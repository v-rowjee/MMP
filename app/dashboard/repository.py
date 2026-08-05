"""Dashboard persistence and dataset context access."""

from io import BytesIO
from typing import Any

import polars as pl


class DashboardRepository:
    def __init__(self, db: Any, upload_bucket: str = "upload"):
        self.db = db
        self.upload_bucket = upload_bucket

    def load_dataset_context(
        self, analysis_id: str, dataset_ids: list[str] | None = None
    ) -> dict[str, Any]:
        linked_dataset_ids = self._load_analysis_dataset_ids(analysis_id)
        if dataset_ids is not None and set(dataset_ids) != set(linked_dataset_ids):
            raise ValueError("Analysis run does not match datasets")
        return {
            "datasets": [
                self._dataset_context(self._load_authorised_dataset(analysis_id, dataset_id))
                for dataset_id in linked_dataset_ids
            ]
        }

    def load_dataset_frame(self, analysis_id: str, dataset_id: str) -> pl.DataFrame:
        dataset = self._load_authorised_dataset(analysis_id, dataset_id)
        parquet_path = dataset.get("meta", {}).get("parquet_path")
        if not isinstance(parquet_path, str):
            raise ValueError("Dataset data is unavailable")
        try:
            parquet = self.db.storage.from_(self.upload_bucket).download(parquet_path)
            return pl.read_parquet(BytesIO(parquet))
        except Exception as error:
            raise ValueError("Dataset data is unavailable") from error

    def _load_authorised_dataset(self, analysis_id: str, dataset_id: str) -> dict[str, Any]:
        analysis = (
            self.db.table("analysis_runs")
            .select("workspace_id")
            .eq("id", analysis_id)
            .maybe_single()
            .execute()
            .data
        )
        if not analysis or dataset_id not in self._load_analysis_dataset_ids(analysis_id):
            raise ValueError("Analysis run does not match datasets")

        dataset = (
            self.db.table("datasets")
            .select(
                "id, workspace_id, name, source_filename, row_count, meta, uploaded_at"
            )
            .eq("id", dataset_id)
            .maybe_single()
            .execute()
            .data
        )
        if not dataset:
            raise ValueError("Dataset not found")
        if dataset["workspace_id"] != analysis["workspace_id"]:
            raise ValueError("Analysis run and dataset belong to different workspaces")
        return dataset

    def _load_analysis_dataset_ids(self, analysis_id: str) -> list[str]:
        links = (
            self.db.table("analysis_run_datasets")
            .select("dataset_id")
            .eq("analysis_id", analysis_id)
            .execute()
            .data
            or []
        )
        dataset_ids = [link["dataset_id"] for link in links]
        if not dataset_ids:
            raise ValueError("Analysis run has no datasets")
        return dataset_ids

    def _dataset_context(self, dataset: dict[str, Any]) -> dict[str, Any]:
        fields = (
            self.db.table("dataset_fields")
            .select("name, original_name, position, dtype, role, profile")
            .eq("dataset_id", dataset["id"])
            .execute()
            .data
            or []
        )
        return {
            "id": dataset["id"],
            "name": dataset["name"],
            "source_filename": dataset["source_filename"],
            "row_count": dataset["row_count"],
            "profile": dataset.get("meta", {}).get("profile", {}),
            "uploaded_at": dataset.get("uploaded_at"),
            "fields": sorted(fields, key=lambda field: field["position"]),
        }

    def create_analysis_for_workspace(self, workspace_id: str) -> dict[str, Any]:
        datasets = (
            self.db.table("datasets")
            .select("id")
            .eq("workspace_id", workspace_id)
            .eq("status", "ready")
            .order("uploaded_at")
            .execute()
            .data
            or []
        )
        if not datasets:
            raise ValueError("No ready dataset found for workspace")

        analysis = (
            self.db.table("analysis_runs")
            .insert(
                {"workspace_id": workspace_id, "status": "dashboard_generating"}
            )
            .execute()
            .data
        )
        if not analysis:
            raise RuntimeError("Dashboard analysis creation failed")
        created_analysis = analysis[0] if isinstance(analysis, list) else analysis
        (
            self.db.table("analysis_run_datasets")
            .insert(
                [
                    {"analysis_id": created_analysis["id"], "dataset_id": dataset["id"]}
                    for dataset in datasets
                ]
            )
            .execute()
        )
        return {**created_analysis, "dataset_ids": [dataset["id"] for dataset in datasets]}

    def load_latest_dashboard(self, workspace_id: str) -> dict[str, Any]:
        analyses = (
            self.db.table("analysis_runs")
            .select("id, dashboard")
            .eq("workspace_id", workspace_id)
            .eq("status", "dashboard_ready")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not analyses:
            raise ValueError("No ready dashboard found for workspace")

        analysis = analyses[0]
        dashboard = analysis["dashboard"]
        required_fields = {
            "generated_at",
            "kpis",
            "charts",
            "anomalies",
            "forecasts",
            "insights",
            "recommendations",
            "warnings",
        }
        if not isinstance(dashboard, dict) or required_fields - dashboard.keys():
            raise ValueError("Dashboard results are unavailable; regenerate dashboard")
        return analysis

    def persist_dashboard(
        self,
        analysis_id: str,
        dashboard: dict[str, Any],
    ) -> None:
        analysis = (
            self.db.table("analysis_runs")
            .select("id")
            .eq("id", analysis_id)
            .maybe_single()
            .execute()
            .data
        )
        if not analysis:
            raise ValueError("Analysis run not found")

        try:
            (
                self.db.table("analysis_runs")
                .update({"dashboard": dashboard, "status": "dashboard_ready"})
                .eq("id", analysis_id)
                .execute()
            )
        except Exception as error:
            raise RuntimeError("Dashboard persistence failed") from error

    def mark_analysis_failed(
        self,
        analysis_id: str,
        failure_stage: str,
        failure_diagnostic: str,
    ) -> None:
        try:
            (
                self.db.table("analysis_runs")
                .update(
                    {
                        "status": "failed",
                        "failure_stage": failure_stage,
                        "failure_diagnostic": failure_diagnostic,
                    }
                )
                .eq("id", analysis_id)
                .execute()
            )
        except Exception as error:
            raise RuntimeError("Dashboard failure persistence failed") from error
