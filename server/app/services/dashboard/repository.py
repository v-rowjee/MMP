"""Dashboard persistence and dataset context access."""

from typing import Any


class DashboardRepository:
    def __init__(self, db: Any):
        self.db = db

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
            .select("id, name, source_filename, row_count, meta, uploaded_at")
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
                "uploaded_at": dataset.get("uploaded_at"),
            },
            "fields": sorted(fields, key=lambda field: field["position"]),
        }

    def create_analysis_for_workspace(self, workspace_id: str) -> dict[str, Any]:
        datasets = (
            self.db.table("datasets")
            .select("id")
            .eq("workspace_id", workspace_id)
            .eq("status", "ready")
            .order("uploaded_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not datasets:
            raise ValueError("No ready dataset found for workspace")

        analysis = (
            self.db.table("analysis_runs")
            .insert(
                {
                    "dataset_id": datasets[0]["id"],
                    "workspace_id": workspace_id,
                    "status": "dashboard_generating",
                }
            )
            .execute()
            .data
        )
        if not analysis:
            raise RuntimeError("Dashboard analysis creation failed")
        return analysis[0] if isinstance(analysis, list) else analysis

    def persist_dashboard(
        self,
        analysis_id: str,
        dataset_id: str,
        dashboard: dict[str, Any],
    ) -> None:
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
