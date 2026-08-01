from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.deps import workspace
from app.services.ingestion.pipeline import upload_files

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", status_code=201)
def upload(request: Request, files: list[UploadFile] = File(...), workspace_id: str = Depends(workspace)):
    return upload_files(request.app.state.db, workspace_id, files)
