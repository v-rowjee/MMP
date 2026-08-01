from pydantic import BaseModel


class UploadResponse(BaseModel):
    dataset_id: str
    analysis_id: str
    processing_status: str
    filename: str
    row_count: int
    column_count: int
