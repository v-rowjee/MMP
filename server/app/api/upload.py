from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.deps import workspace
from app.schemas.upload import UploadResponse
from app.services.ingestion.pipeline import upload_files

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResponse, status_code=201)
def upload(
    request: Request,
    files: list[UploadFile] = File(...),
    workspace_id: str = Depends(workspace),
) -> UploadResponse:
    try:
        return upload_files(
            request.app.state.db,
            workspace_id,
            files,
            bucket=request.app.state.settings.upload_bucket,
            max_file_bytes=request.app.state.settings.upload_max_file_bytes,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
