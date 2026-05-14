import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(), nullable=False, index=True)

class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(), nullable=False, index=True)

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dashboard_id = Column(String(36), ForeignKey("dashboards.id"), nullable=True, index=True)
    pbix_dashboard_id = Column(String(36), ForeignKey("dashboards.id"), nullable=True, index=True)
    student_name = Column(String(255), nullable=True)
    user_message = Column(Text, nullable=False)
    ai_response = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False, index=True)

class GradingRecord(Base):
    __tablename__ = "grading_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pbix_dashboard_id = Column(String(36), ForeignKey("dashboards.id"), nullable=True, index=True)
    student_name = Column(String(255), nullable=False, index=True)
    individual_visuals_create = Column(Integer, nullable=True)
    individual_visuals_customize = Column(Integer, nullable=True)
    individual_insights_interpret = Column(Integer, nullable=True)
    individual_insights_provide = Column(Integer, nullable=True)
    team_dashboard_design = Column(Integer, nullable=True)
    team_dashboard_slicers = Column(Integer, nullable=True)
    team_insights_sdg = Column(Integer, nullable=True)
    team_insights_generate = Column(Integer, nullable=True)
    grading_comments = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), nullable=False)
