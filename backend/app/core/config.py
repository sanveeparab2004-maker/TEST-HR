import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "CS Creative Solutions Assessment Portal"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production_1234567890")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 180  # 3 hours, enough for 60-min exam + review

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./assess_local.db"
    )

    # Free tier DB Pool tuning
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_PRE_PING: bool = True

    # Assessment defaults
    EXAM_DURATION_MINUTES: int = int(os.getenv("TEST_DURATION_MINUTES", "60"))
    TOTAL_MARKS: int = int(os.getenv("TOTAL_MARKS", "100"))
    PASS_MARKS: int = int(os.getenv("PASS_MARKS", "35"))
    MARKS_PER_QUESTION: int = int(os.getenv("MARKS_PER_QUESTION", "1"))
    NEGATIVE_MARKING: float = float(os.getenv("NEGATIVE_MARKING", "0"))
    MAX_TAB_WARNINGS: int = int(os.getenv("MAX_TAB_WARNINGS", "5"))
    MAX_FACE_WARNINGS: int = int(os.getenv("MAX_FACE_WARNINGS", "5"))
    FACE_MISSING_SECONDS: int = int(os.getenv("FACE_MISSING_SECONDS", "3"))
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.5"))
    DEPARTMENTS: List[str] = ["HR", "CLAIM", "ASSESSMENT", "ASHTAPRADHAN", "TENDER", "ADMIN", "OPERATIONS", "ACCOUNTS"]

    # Google Sheets Integration
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "184qGjXRADe6RLzAlBy3LGk78xzkUa8GXeqkBOzWvkWI")
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", None)
    GOOGLE_SERVICE_ACCOUNT_FILE: Optional[str] = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", None)

    # Seed credentials
    DEFAULT_MONITOR_CODE: str = os.getenv("DEFAULT_MONITOR_CODE", "HR_MONITOR_01")
    DEFAULT_MONITOR_NAME: str = os.getenv("DEFAULT_MONITOR_NAME", "Chief Exam Proctor")
    DEFAULT_MONITOR_PIN: str = os.getenv("DEFAULT_MONITOR_PIN", "654321")

    DEFAULT_ADMIN_CODE: str = os.getenv("DEFAULT_ADMIN_CODE", "HR_ADMIN_01")
    DEFAULT_ADMIN_NAME: str = os.getenv("DEFAULT_ADMIN_NAME", "HR Operations Lead")
    DEFAULT_ADMIN_PIN: str = os.getenv("DEFAULT_ADMIN_PIN", "987123")

    # WebRTC STUN/TURN
    STUN_URLS: str = os.getenv("STUN_URLS", "stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302")
    TURN_URLS: Optional[str] = os.getenv("TURN_URLS", None)
    TURN_USERNAME: Optional[str] = os.getenv("TURN_USERNAME", None)
    TURN_CREDENTIAL: Optional[str] = os.getenv("TURN_CREDENTIAL", None)

    # Optional AI (Claude)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", None)
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    # Allowed Origins
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    @property
    def cors_origins(self) -> List[str]:
        if not self.ALLOWED_ORIGINS or self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
