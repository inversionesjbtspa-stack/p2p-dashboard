from __future__ import annotations

import os
from dataclasses import dataclass


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./p2p_dashboard.db")
    binance_api_key: str = os.getenv("BINANCE_API_KEY", "")
    binance_secret_key: str = os.getenv("BINANCE_SECRET_KEY", "")
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    sync_lookback_days: int = int(os.getenv("SYNC_LOOKBACK_DAYS", "30"))
    sync_rows: int = int(os.getenv("SYNC_ROWS", "100"))
    dashboard_username: str = os.getenv("DASHBOARD_USERNAME", "admin")
    dashboard_password: str = os.getenv("DASHBOARD_PASSWORD", "change_me")
    timezone_name: str = os.getenv("TZ", "America/Santiago")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")
    openai_enabled: bool = env_bool("OPENAI_ENABLED", True)
    openai_timeout_seconds: float = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "45"))


settings = Settings()
