from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.rubric import RubricResponse, RubricUploadResponse, RubricDeleteResponse
from src.db import crud
from src.services.file_handler import file_handler
from src.utils.errors import FileUploadError
import os

router = APIRouter()

@router.post("/upload", response_model=RubricUploadResponse)
async def upload_rubric(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a rubric (grading criteria) image or PDF."""
    try:
        # Save file
        file_id, file_path = await file_handler.save_dashboard_image(file)

        # Save rubric record (deletes old one automatically)
        rubric = crud.create_rubric(
            db=db,
            filename=file.filename or f"rubric_{file_id}",
            file_path=file_path,
        )

        return RubricUploadResponse(
            rubric=RubricResponse.model_validate(rubric),
            message="Rubric uploaded successfully"
        )

    except FileUploadError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=dict)
def get_rubric(
    db: Session = Depends(get_db),
):
    """Get the active rubric."""
    rubric = crud.get_active_rubric(db)
    if rubric:
        return {"rubric": RubricResponse.model_validate(rubric)}
    return {"rubric": None}

@router.delete("", response_model=RubricDeleteResponse)
def delete_rubric(
    db: Session = Depends(get_db),
):
    """Delete the active rubric."""
    rubric = crud.get_active_rubric(db)
    if not rubric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No rubric found"
        )

    # Delete file
    file_handler.delete_file(rubric.file_path)

    # Delete database record
    crud.delete_rubric(db)

    return RubricDeleteResponse(
        status="deleted",
        message="Rubric deleted successfully"
    )
