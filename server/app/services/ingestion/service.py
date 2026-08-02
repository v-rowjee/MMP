"""Dataset upload service."""

from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.schemas.upload import UploadedFile, UploadResponse
from app.services.ingestion.processing import process_file
from app.services.ingestion.repository import IngestionRepository


class IngestionService:
    def __init__(self, db: Any, bucket: str, max_file_bytes: int):
        self.repository = IngestionRepository(db, bucket)
        self.max_file_bytes = max_file_bytes

    def upload_files(self, workspace_id: str, files: list[UploadFile]) -> UploadResponse:
        if not files:
            raise ValueError("Upload at least one CSV file")

        processed_files = [process_file(file, self.max_file_bytes) for file in files]
        if len({file.name for file in processed_files}) != len(processed_files):
            raise ValueError("Uploaded files must have unique names")

        stored_files: list[tuple[str, str, str]] = []
        try:
            for file in processed_files:
                dataset_id = str(uuid4())
                original_path = f"{workspace_id}/{dataset_id}/{file.filename}"
                parquet_path = f"{workspace_id}/{dataset_id}/{file.name}.parquet"
                stored_files.append((dataset_id, original_path, parquet_path))
                self.repository.store_files(original_path, parquet_path, file)
                self.repository.create_dataset(
                    dataset_id,
                    workspace_id,
                    file,
                    original_path,
                    parquet_path,
                )
        except Exception:
            for dataset_id, original_path, parquet_path in stored_files:
                self.repository.cleanup(dataset_id, [original_path, parquet_path])
            raise

        return UploadResponse(
            processing_status="uploaded",
            files=[
                UploadedFile(
                    filename=file.filename,
                    row_count=file.profile["row_count"],
                    column_count=file.profile["column_count"],
                )
                for file in processed_files
            ],
        )
