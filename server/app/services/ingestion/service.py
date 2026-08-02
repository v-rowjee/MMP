"""Dataset upload service."""

from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.schemas.upload import UploadResponse
from app.services.ingestion.processing import process_file
from app.services.ingestion.repository import IngestionRepository


class IngestionService:
    def __init__(self, db: Any, bucket: str, max_file_bytes: int):
        self.repository = IngestionRepository(db, bucket)
        self.max_file_bytes = max_file_bytes

    def upload_files(self, workspace_id: str, files: list[UploadFile]) -> UploadResponse:
        if len(files) != 1:
            raise ValueError("Upload one CSV file at a time")

        file = process_file(files[0], self.max_file_bytes)
        dataset_id, analysis_id = str(uuid4()), str(uuid4())
        original_path = f"{workspace_id}/{dataset_id}/{file.filename}"
        parquet_path = f"{workspace_id}/{dataset_id}/{file.name}.parquet"
        try:
            self.repository.store_files(original_path, parquet_path, file)
            self.repository.create_dataset(
                dataset_id,
                workspace_id,
                file,
                original_path,
                parquet_path,
            )
            self.repository.create_analysis(analysis_id, dataset_id, workspace_id)
        except Exception:
            self.repository.cleanup(dataset_id, [original_path, parquet_path])
            raise

        return UploadResponse(
            dataset_id=dataset_id,
            analysis_id=analysis_id,
            processing_status="dashboard_generating",
            filename=file.filename,
            row_count=file.profile["row_count"],
            column_count=file.profile["column_count"],
        )
