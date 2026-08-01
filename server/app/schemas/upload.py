"""Upload API schemas."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    workspace_id: str
    dataset_name: str
    rows: int
    columns: int
    warnings: list[str] = []