from sqlalchemy.orm import Session
from src.db.models import Dashboard, Message, Rubric, GradingRecord
import uuid

# Rubric CRUD

def create_rubric(
    db: Session, filename: str, file_path: str
) -> Rubric:
    # Delete old rubric if exists
    old_rubric = db.query(Rubric).first()
    if old_rubric:
        db.delete(old_rubric)

    rubric = Rubric(
        id=str(uuid.uuid4()),
        filename=filename,
        file_path=file_path,
    )
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return rubric

def get_active_rubric(db: Session) -> Rubric | None:
    return db.query(Rubric).order_by(Rubric.uploaded_at.desc()).first()

def delete_rubric(db: Session) -> bool:
    rubric = get_active_rubric(db)
    if rubric:
        db.delete(rubric)
        db.commit()
        return True
    return False

# Dashboard CRUD

def create_dashboard(
    db: Session, filename: str, file_path: str
) -> Dashboard:
    dashboard = Dashboard(
        id=str(uuid.uuid4()),
        filename=filename,
        file_path=file_path,
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return dashboard

def get_dashboard(db: Session, dashboard_id: str) -> Dashboard | None:
    return db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()

def get_all_dashboards(db: Session) -> list[Dashboard]:
    return db.query(Dashboard).order_by(Dashboard.uploaded_at.desc()).all()

def delete_dashboard(db: Session, dashboard_id: str) -> bool:
    dashboard = get_dashboard(db, dashboard_id)
    if dashboard:
        db.delete(dashboard)
        db.commit()
        return True
    return False

# Message CRUD

def create_message(
    db: Session,
    user_message: str,
    ai_response: dict,
    dashboard_id: str | None = None,
    pbix_dashboard_id: str | None = None,
    student_name: str | None = None,
) -> Message:
    message = Message(
        id=str(uuid.uuid4()),
        dashboard_id=dashboard_id,
        pbix_dashboard_id=pbix_dashboard_id,
        student_name=student_name,
        user_message=user_message,
        ai_response=ai_response,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_all_messages(db: Session) -> list[Message]:
    return db.query(Message).order_by(Message.created_at.asc()).all()

def get_dashboard_messages(db: Session, dashboard_id: str) -> list[Message]:
    return db.query(Message).filter(Message.dashboard_id == dashboard_id).order_by(Message.created_at.asc()).all()

def get_message(db: Session, message_id: str) -> Message | None:
    return db.query(Message).filter(Message.id == message_id).first()

# Grading Record CRUD

def create_or_update_grading_record(
    db: Session,
    student_name: str,
    pbix_dashboard_id: str | None = None,
    individual_visuals_create: int | None = None,
    individual_visuals_customize: int | None = None,
    individual_insights_interpret: int | None = None,
    individual_insights_provide: int | None = None,
    team_dashboard_design: int | None = None,
    team_dashboard_slicers: int | None = None,
    team_insights_sdg: int | None = None,
    team_insights_generate: int | None = None,
    grading_comments: dict | None = None,
) -> GradingRecord:
    # Check if record already exists
    existing = db.query(GradingRecord).filter(
        GradingRecord.student_name == student_name,
        GradingRecord.pbix_dashboard_id == pbix_dashboard_id
    ).first()

    if existing:
        if individual_visuals_create is not None:
            existing.individual_visuals_create = individual_visuals_create
        if individual_visuals_customize is not None:
            existing.individual_visuals_customize = individual_visuals_customize
        if individual_insights_interpret is not None:
            existing.individual_insights_interpret = individual_insights_interpret
        if individual_insights_provide is not None:
            existing.individual_insights_provide = individual_insights_provide
        if team_dashboard_design is not None:
            existing.team_dashboard_design = team_dashboard_design
        if team_dashboard_slicers is not None:
            existing.team_dashboard_slicers = team_dashboard_slicers
        if team_insights_sdg is not None:
            existing.team_insights_sdg = team_insights_sdg
        if team_insights_generate is not None:
            existing.team_insights_generate = team_insights_generate
        if grading_comments is not None:
            existing.grading_comments = grading_comments
        db.commit()
        db.refresh(existing)
        return existing

    record = GradingRecord(
        id=str(uuid.uuid4()),
        pbix_dashboard_id=pbix_dashboard_id,
        student_name=student_name,
        individual_visuals_create=individual_visuals_create,
        individual_visuals_customize=individual_visuals_customize,
        individual_insights_interpret=individual_insights_interpret,
        individual_insights_provide=individual_insights_provide,
        team_dashboard_design=team_dashboard_design,
        team_dashboard_slicers=team_dashboard_slicers,
        team_insights_sdg=team_insights_sdg,
        team_insights_generate=team_insights_generate,
        grading_comments=grading_comments,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_grading_record(
    db: Session,
    student_name: str,
    pbix_dashboard_id: str | None = None
) -> GradingRecord | None:
    return db.query(GradingRecord).filter(
        GradingRecord.student_name == student_name,
        GradingRecord.pbix_dashboard_id == pbix_dashboard_id
    ).first()

def get_grading_records_by_pbix(db: Session, pbix_dashboard_id: str) -> list[GradingRecord]:
    return db.query(GradingRecord).filter(
        GradingRecord.pbix_dashboard_id == pbix_dashboard_id
    ).order_by(GradingRecord.student_name).all()
