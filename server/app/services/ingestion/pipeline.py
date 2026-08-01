from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.schemas.upload import UploadResponse
from app.services.ingestion.processing import process_file


def upload_files(
    db: Any,
    workspace_id: str,
    files: list[UploadFile],
    *,
    bucket: str,
    max_file_bytes: int,
) -> UploadResponse:
    if len(files) != 1:
        raise ValueError("Upload one CSV file at a time")
    file = process_file(files[0], max_file_bytes)
    dataset_id, analysis_id = str(uuid4()), str(uuid4())
    original_path = f"{workspace_id}/{dataset_id}/{file.filename}"
    parquet_path = f"{workspace_id}/{dataset_id}/{file.name}.parquet"
    storage = db.storage.from_(bucket)
    try:
        storage.upload(original_path, file.original, {"upsert": "false", "content-type": "text/csv"})
        storage.upload(parquet_path, file.parquet, {"upsert": "false", "content-type": "application/vnd.apache.parquet"})
        db.table("datasets").insert({
            "id": dataset_id,
            "workspace_id": workspace_id,
            "name": file.name,
            "source_filename": file.filename,
            "status": "ready",
            "row_count": file.profile["row_count"],
            "meta": {"profile": file.profile, "original_path": original_path, "parquet_path": parquet_path},
        }).execute()
        db.table("dataset_fields").insert([{**field, "dataset_id": dataset_id} for field in file.fields]).execute()
        db.table("analysis_runs").insert({
            "id": analysis_id,
            "dataset_id": dataset_id,
            "workspace_id": workspace_id,
            "status": "dashboard_generating",
        }).execute()
    except Exception:
        db.table("datasets").delete().eq("id", dataset_id).execute()
        storage.remove([original_path, parquet_path])
        raise
    return UploadResponse(
        dataset_id=dataset_id,
        analysis_id=analysis_id,
        processing_status="dashboard_generating",
        filename=file.filename,
        row_count=file.profile["row_count"],
        column_count=file.profile["column_count"],
    )
