"""Dataset upload persistence."""

from typing import Any

from app.services.ingestion.processing import ProcessedFile


class IngestionRepository:
    def __init__(self, db: Any, bucket: str):
        self.db = db
        self.storage = db.storage.from_(bucket)

    def store_files(
        self,
        original_path: str,
        parquet_path: str,
        file: ProcessedFile,
    ) -> None:
        self.storage.upload(
            original_path,
            file.original,
            {"upsert": "false", "content-type": "text/csv"},
        )
        self.storage.upload(
            parquet_path,
            file.parquet,
            {"upsert": "false", "content-type": "application/vnd.apache.parquet"},
        )

    def create_dataset(
        self,
        dataset_id: str,
        workspace_id: str,
        file: ProcessedFile,
        original_path: str,
        parquet_path: str,
    ) -> None:
        self.db.table("datasets").insert(
            {
                "id": dataset_id,
                "workspace_id": workspace_id,
                "name": file.name,
                "source_filename": file.filename,
                "status": "ready",
                "row_count": file.profile["row_count"],
                "meta": {
                    "profile": file.profile,
                    "original_path": original_path,
                    "parquet_path": parquet_path,
                },
            }
        ).execute()
        self.db.table("dataset_fields").insert(
            [{**field, "dataset_id": dataset_id} for field in file.fields]
        ).execute()

    def create_analysis(self, analysis_id: str, dataset_id: str, workspace_id: str) -> None:
        self.db.table("analysis_runs").insert(
            {
                "id": analysis_id,
                "dataset_id": dataset_id,
                "workspace_id": workspace_id,
                "status": "dashboard_generating",
            }
        ).execute()

    def cleanup(self, dataset_id: str, paths: list[str]) -> None:
        self.db.table("datasets").delete().eq("id", dataset_id).execute()
        self.storage.remove(paths)
