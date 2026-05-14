from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.models.dashboard import DashboardResponse, DashboardListResponse
from src.db import crud
from src.services.file_handler import file_handler
from src.services.pbix_inspector import pbix_inspector
from src.utils.errors import FileUploadError, NotFoundError

router = APIRouter()

@router.post("/upload", response_model=DashboardResponse)
async def upload_dashboard(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a dashboard image."""
    try:
        # Save file
        file_id, file_path = await file_handler.save_dashboard_image(file)

        # Save dashboard record
        dashboard = crud.create_dashboard(
            db=db,
            filename=file.filename or f"dashboard_{file_id}",
            file_path=file_path,
        )

        return DashboardResponse.model_validate(dashboard)

    except FileUploadError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("", response_model=DashboardListResponse)
def list_dashboards(
    db: Session = Depends(get_db),
):
    """List all dashboards."""
    dashboards = crud.get_all_dashboards(db)
    return DashboardListResponse(
        dashboards=[DashboardResponse.model_validate(d) for d in dashboards],
        total=len(dashboards),
    )

@router.get("/{dashboard_id}", response_model=DashboardResponse)
def get_dashboard(
    dashboard_id: str,
    db: Session = Depends(get_db),
):
    """Get dashboard details."""
    dashboard = crud.get_dashboard(db, dashboard_id)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found"
        )

    return DashboardResponse.model_validate(dashboard)

@router.get("/{dashboard_id}/students")
def get_dashboard_students(
    dashboard_id: str,
    db: Session = Depends(get_db),
):
    """Return student names detected in a PBIX dashboard, plus raw chart titles for debugging."""
    dashboard = crud.get_dashboard(db, dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")

    if not dashboard.file_path.lower().endswith(".pbix"):
        return {"students": [], "debug_titles": []}

    inspection = pbix_inspector.inspect(dashboard.file_path)
    names = pbix_inspector.extract_student_names(inspection)

    # Collect all text entries from the Dashboard page for debugging
    debug_titles = []
    for page in inspection.get("pages", []):
        page_name = (page.get("display_name") or page.get("name") or "").lower()
        if "dashboard" in page_name:
            for visual in page.get("visuals", []):
                for entry in visual.get("text_content", []):
                    t = entry.get("text", "").strip()
                    if t:
                        debug_titles.append(t)

    return {"students": names, "debug_titles": debug_titles}


@router.delete("/{dashboard_id}")
def delete_dashboard(
    dashboard_id: str,
    db: Session = Depends(get_db),
):
    """Delete dashboard."""
    dashboard = crud.get_dashboard(db, dashboard_id)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard not found"
        )

    # Delete file
    file_handler.delete_file(dashboard.file_path)

    # Delete database record
    crud.delete_dashboard(db, dashboard_id)

    return {"status": "deleted"}
