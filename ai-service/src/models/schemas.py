from pydantic import BaseModel
from typing import Any

class GradeRequest(BaseModel):
    image_data: str  # base64 encoded image
    query: str
    context: str = ""

class GradeResponse(BaseModel):
    response: dict[str, Any]
