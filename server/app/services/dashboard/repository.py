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
