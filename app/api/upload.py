from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.core.deps import workspace
from app.schemas.upload import UploadResponse
from app.datasets.service import IngestionService

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResponse, status_code=201)
def upload(
    request: Request,
    files: list[UploadFile] = File(...),
    workspace_id: str = Depends(workspace),
) -> UploadResponse:
    try:
        return IngestionService(
            request.app.state.db,
            request.app.state.settings.upload_bucket,
            request.app.state.settings.upload_max_file_bytes,
        ).upload_files(workspace_id, files)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
