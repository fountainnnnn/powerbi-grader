from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    ai_service_port: int = 8001
    debug: bool = True

    # Gemini API settings
    gemini_model: str = "gemini-2.5-flash"
    max_tokens: int = 1024
    temperature: float = 0.7

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
