from pydantic import BaseModel
from datetime import datetime

class RubricResponse(BaseModel):
    id: str
    filename: str
    file_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class RubricUploadResponse(BaseModel):
    rubric: RubricResponse
    message: str

class RubricDeleteResponse(BaseModel):
    status: str
    message: str
