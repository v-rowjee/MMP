"""Upload API endpoints."""

from fastapi import APIRouter, File, Request, UploadFile

from server.app.services.ingestion.pipeline import upload_dataset
from app.schemas.upload import UploadResponse


router = APIRouter(
    prefix="/upload",
    tags=["upload"],
)


@router.post("")
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
) -> list[UploadResponse]:
    """
    Upload one or more CSV files.
    """

    db = request.app.state.db

    workspace_id = "ws_test1234"  # temporary until auth/workspace handling

    responses = []

    for file in files:
        response = upload_dataset(
            db=db,
            workspace_id=workspace_id,
            file=file,
        )

        responses.append(response)

    return responses