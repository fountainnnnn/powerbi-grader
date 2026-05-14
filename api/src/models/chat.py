from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any

class ChatMessageRequest(BaseModel):
    message: str | None = None
    dashboard_id: str | None = None
    pbix_id: str | None = None
    student_name: str | None = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.message and not self.dashboard_id and not self.pbix_id:
            raise ValueError("Either message, dashboard_id, or pbix_id is required")

class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    dashboard_id: str | None
    pbix_id: str | None = None
    student_name: str | None = None
    user_message: str
    ai_response: dict[str, Any]
    created_at: datetime
    dashboard_filename: str | None = None
    dashboard_file_path: str | None = None
    pbix_filename: str | None = None
    pbix_file_path: str | None = None

class GradingMarks(BaseModel):
    individual_visuals_create: int | None = None
    individual_visuals_customize: int | None = None
    individual_insights_interpret: int | None = None
    individual_insights_provide: int | None = None
    team_dashboard_design: int | None = None
    team_dashboard_slicers: int | None = None
    team_insights_sdg: int | None = None
    team_insights_generate: int | None = None

class GradingResponse(BaseModel):
    student_name: str
    marks: GradingMarks
    individual_total: int | None = None
    team_total: int | None = None
    overall_total: int | None = None
    explanation: dict[str, str]
    evidence_received: dict[str, str]

class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    total: int

class AIGradeRequest(BaseModel):
    image_data: str  # base64 encoded image
    query: str
    context: str = ""

class AIGradeResponse(BaseModel):
    response: dict[str, Any]
