from typing import Literal

from pydantic import BaseModel


class UploadedFile(BaseModel):
    filename: str
    row_count: int
    column_count: int


class UploadResponse(BaseModel):
    processing_status: Literal["uploaded"]
    files: list[UploadedFile]
