import os
from pathlib import Path

class Settings:
    APP_NAME = "AI Project Builder"
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-development-secret")
    SESSION_HTTPS_ONLY = os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/projects.db")
    PROJECT_STORAGE = Path(os.getenv("PROJECT_STORAGE", "./data/generated"))
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
    AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_CALLBACK_URL = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:8000/api/github/callback")
    COOKIE_NAME = "apb_session"

settings = Settings()
settings.PROJECT_STORAGE.mkdir(parents=True, exist_ok=True)
Path(settings.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
