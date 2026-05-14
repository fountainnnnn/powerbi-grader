from datetime import datetime
import os
import tempfile
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from src.models.chat import ChatMessageResponse
from src.services.chat_service import chat_service
from src.services.file_handler import file_handler
from src.services.pbix_inspector import pbix_inspector
from src.utils.errors import AIServiceError, ChatServiceError, FileUploadError

router = APIRouter()


def _temp_parent() -> str | None:
    return "/tmp" if os.path.isdir("/tmp") else None


async def _save_optional_file(
    file: UploadFile | None,
    upload_dir: str,
) -> tuple[str | None, str | None]:
    if not file or not file.filename:
        return None, None
    _, path = await file_handler.save_dashboard_image(file, upload_dir=upload_dir)
    return file.filename, path


@router.post("/students")
async def detect_students_stateless(file: UploadFile = File(...)) -> dict:
    """Detect student names from a PBIX file without persisting it."""
    try:
        with tempfile.TemporaryDirectory(dir=_temp_parent()) as temp_dir:
            _, pbix_path = await file_handler.save_dashboard_image(file, upload_dir=temp_dir)
            inspection = pbix_inspector.inspect(pbix_path)
            return {"students": pbix_inspector.extract_student_names(inspection)}
    except FileUploadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Student detection failed: {str(e)}",
        )


@router.post("/grade", response_model=ChatMessageResponse)
async def grade_stateless(
    message: str | None = Form(None),
    student_name: str | None = Form(None),
    rubric_file: UploadFile | None = File(None),
    visual_file: UploadFile | None = File(None),
    pbix_file: UploadFile | None = File(None),
):
    """One-shot stateless grading endpoint for Vercel/serverless deployments."""
    try:
        with tempfile.TemporaryDirectory(dir=_temp_parent()) as temp_dir:
            rubric_filename, rubric_path = await _save_optional_file(rubric_file, temp_dir)
            visual_filename, visual_path = await _save_optional_file(visual_file, temp_dir)
            pbix_filename, pbix_path = await _save_optional_file(pbix_file, temp_dir)

            response = chat_service.grade_stateless(
                message=message,
                image_path=visual_path,
                image_filename=visual_filename,
                pbix_path=pbix_path,
                pbix_filename=pbix_filename,
                rubric_path=rubric_path,
                rubric_filename=rubric_filename,
                student_name=student_name,
            )

            return ChatMessageResponse(
                id=str(uuid.uuid4()),
                dashboard_id=None,
                pbix_id=None,
                student_name=student_name,
                user_message=message or "",
                ai_response=response["ai_response"],
                created_at=datetime.now(),
                dashboard_filename=visual_filename,
                dashboard_file_path=None,
                pbix_filename=pbix_filename,
                pbix_file_path=None,
            )

    except FileUploadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AIServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is unavailable",
        )
    except ChatServiceError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
