from pydantic import BaseModel
from datetime import datetime

class DashboardUploadRequest(BaseModel):
    filename: str

class DashboardResponse(BaseModel):
    id: str
    filename: str
    file_path: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class DashboardListResponse(BaseModel):
    dashboards: list[DashboardResponse]
    total: int
