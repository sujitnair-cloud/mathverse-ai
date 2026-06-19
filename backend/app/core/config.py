from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "MathVerse AI"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # LLM
    LLM_PROVIDER: str = "none"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Database — Railway sets DATABASE_URL automatically for Postgres
    DATABASE_URL: str = "sqlite+aiosqlite:///./mathverse.db"

    # Auth
    SECRET_KEY: str = "change-this-to-a-long-random-secret-key-in-production"
    JWT_SECRET_KEY: str = "change-this-jwt-secret-too"
    JWT_EXPIRE_HOURS: int = 720  # 30 days

    # Google OAuth — get from console.cloud.google.com
    GOOGLE_CLIENT_ID: str = ""

    # Stripe — get from dashboard.stripe.com
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_STUDENT_PRICE_ID: str = ""   # $4.99/mo price ID from Stripe dashboard
    STRIPE_PRO_PRICE_ID: str = ""       # $9.99/mo price ID from Stripe dashboard

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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
