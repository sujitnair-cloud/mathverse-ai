from pydantic_settings import BaseSettings
from typing import List

_WEAK_SECRETS = {
    "change-this-to-a-long-random-secret-key-in-production",
    "change-this-jwt-secret-too",
    "",
}


class Settings(BaseSettings):
    APP_NAME: str = "MathVerse AI"
    DEBUG: bool = False
    FRONTEND_URL: str = "https://mathverseai.org"
    ALLOWED_ORIGINS: str = (
        "https://mathverseai.org,"
        "https://www.mathverseai.org,"
        "https://mathverse-ai-bhwn.vercel.app,"
        "http://localhost:5173,"
        "http://localhost:3000"
    )

    # LLM
    LLM_PROVIDER: str = "none"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_API_KEYS: str = ""  # comma-separated extra keys; rotated automatically when quota is hit
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Database — Railway sets DATABASE_URL automatically for Postgres
    DATABASE_URL: str = "sqlite+aiosqlite:///./mathverse.db"

    # Auth
    SECRET_KEY: str = "change-this-to-a-long-random-secret-key-in-production"
    JWT_SECRET_KEY: str = "change-this-jwt-secret-too"
    JWT_EXPIRE_HOURS: int = 168  # 7 days (was 30 days — reduced for security)

    # Google OAuth — get from console.cloud.google.com
    # This identifier is public browser configuration, not a secret.
    GOOGLE_CLIENT_ID: str = (
        "91461754884-h4kol63caeemh5gj78ip0kl2eo7207si.apps.googleusercontent.com"
    )

    # Admin — comma-separated emails that can access /api/v1/admin/dashboard
    # Example: ADMIN_EMAILS=you@gmail.com,partner@gmail.com
    ADMIN_EMAILS: str = ""

    # Cashfree — get from merchant.cashfree.com → Developers → API Keys
    CASHFREE_APP_ID: str = ""
    CASHFREE_SECRET_KEY: str = ""
    CASHFREE_WEBHOOK_SECRET: str = ""
    CASHFREE_ENV: str = "test"          # "test" or "production"
    CASHFREE_STUDENT_PLAN_ID: str = ""
    CASHFREE_PRO_PLAN_ID: str = ""

    @property
    def origins(self) -> List[str]:
        base = [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]
        # Always allow the configured frontend URL
        if self.FRONTEND_URL not in base:
            base.append(self.FRONTEND_URL)
        return base

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        # Railway provides postgresql:// — asyncpg needs postgresql+asyncpg://
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def has_weak_secrets(self) -> bool:
        return (
            self.SECRET_KEY in _WEAK_SECRETS
            or self.JWT_SECRET_KEY in _WEAK_SECRETS
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
