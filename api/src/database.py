from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from src.config import settings

# Create SQLite engine (synchronous)
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for ORM models
Base = declarative_base()

def get_db():
    """Dependency for getting database session in routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    from src.db.models import Base
    Base.metadata.create_all(bind=engine)
    if "sqlite" in settings.database_url:
        with engine.begin() as connection:
            columns = {
                row[1]
                for row in connection.exec_driver_sql("PRAGMA table_info(messages)").fetchall()
            }
            if "pbix_dashboard_id" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE messages ADD COLUMN pbix_dashboard_id VARCHAR(36)"
                )
            if "student_name" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE messages ADD COLUMN student_name VARCHAR(255)"
                )
