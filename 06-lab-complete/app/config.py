import os
from dataclasses import dataclass
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("AGENT_API_KEY", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rate_limit: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    daily_budget: Decimal = Decimal(os.getenv("DAILY_BUDGET_USD", "1"))
    monthly_budget: Decimal = Decimal(os.getenv("MONTHLY_BUDGET_USD", "30"))
    port: int = int(os.getenv("PORT", "8000"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
