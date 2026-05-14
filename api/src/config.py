import os
from pathlib import Path
import tempfile

from pydantic_settings import BaseSettings


IS_VERCEL = bool(os.getenv("VERCEL"))
TEMP_DIR = Path(tempfile.gettempdir())


class Settings(BaseSettings):
    # Database (SQLite)
    database_url: str = (
        f"sqlite:///{(TEMP_DIR / 'app.db').as_posix()}"
        if IS_VERCEL
        else "sqlite:///./app.db"
    )

    # API
    api_port: int = 8000
    api_secret_key: str = ""
    debug: bool = True

    # OpenAI API
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.2

    # File Upload
    max_upload_size_mb: int = 100
    upload_dir: str = str(TEMP_DIR / "powerbi-vision-uploads") if IS_VERCEL else "uploads"
    allowed_image_types: list = [
        "image/png",
        "image/jpeg",
        "image/jpg",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ]
    max_pdf_pages: int = 10

    class Config:
        # Look for .env in project root and current directory
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        case_sensitive = False
        extra = "ignore"

settings = Settings()

# Validate that required keys are set
if not settings.api_secret_key:
    raise ValueError("API_SECRET_KEY not set in .env file")
if not settings.openai_api_key:
    raise ValueError("OPENAI_API_KEY not set in .env file")
