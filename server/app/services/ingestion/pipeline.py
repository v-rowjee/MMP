"""Dataset ingestion pipeline."""

from app.schemas.upload import UploadResponse
from fastapi import UploadFile
from supabase import Client


def upload_dataset(
    db: Client,
    workspace_id: str,
    file: UploadFile,
) -> UploadResponse:
    """
    Upload CSV to Supabase Storage and create dataset metadata.
    """

    if not file.filename:
        raise ValueError("Filename is required")

    filename = file.filename

    storage_path = f"{workspace_id}/{filename}"

    file_content = file.file.read()

    db.storage.from_("datasets").upload(
        path=storage_path,
        file=file_content,
        file_options={
            "upsert": "true",
            "content-type": "text/csv",
        },
    )

    dataset_name = (
        filename
        .removesuffix(".csv")
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


    db.table("datasets").insert(
        {
            "workspace_id": workspace_id,
            "name": dataset_name,
            "source_filename": filename,
            "status": "ingesting",
            "meta": {
                "storage_path": storage_path,
            },
        }
    ).execute()
    

    return UploadResponse(
        workspace_id=workspace_id,
        dataset_name=dataset_name,
        rows=0,
        columns=0,
        warnings=[],
    )