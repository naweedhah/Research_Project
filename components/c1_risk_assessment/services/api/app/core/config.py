from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "packages" / "contracts").is_dir() or (parent / "docker-compose.yml").is_file():
            return parent
    if Path("/contracts").exists():
        return Path("/app")
    return here.parents[min(4, len(here.parents) - 1)]


ROOT = _repo_root()
CONTRACTS = Path("/contracts") if Path("/contracts").exists() else ROOT / "packages" / "contracts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(str(ROOT / ".env"), ".env"), extra="ignore")

    app_env: str = "development"
    app_name: str = "Child Nutrition Intelligence Platform"
    frontend_url: str = "http://localhost:3000"
    cors_extra_origins: str = ""
    api_url: str = "http://localhost:8000"
    inference_url: str = "http://localhost:8001"

    database_url: str = "postgresql+psycopg://cnip:cnip_dev_password@localhost:5432/cnip"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-access-secret-dev-only"
    jwt_refresh_secret: str = "change-me-refresh-secret-dev-only"
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 7
    encryption_key: str = "change-me-32-byte-fernet-or-hex-dev"

    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str | None = None

    model_mode: str = "demo"
    model_artifact_path: str = "/artifacts/active"
    embedding_dim: int = 128

    notification_provider: str = "mock"
    sms_api_key: str = ""
    email_api_key: str = ""

    fhir_enabled: bool = False
    fhir_base_url: str = ""
    fhir_version: str = "R4"
    hospital_adapter: str = "mock"

    c2_explainability_url: str = ""
    c3_counterfactual_url: str = ""
    c4_drift_url: str = ""
    c2_integration_token: str = ""
    c3_integration_token: str = ""
    c4_integration_token: str = ""
    integration_mode: str = "mock"
    integration_timeout_seconds: float = 8.0
    integration_max_retries: int = 5

    log_level: str = "INFO"
    log_json: bool = True
    seed_on_start: bool = False

    contracts_dir: Path = CONTRACTS
    failed_login_limit: int = 8
    lockout_minutes: int = 15

    @property
    def access_ttl(self) -> timedelta:
        return timedelta(minutes=self.jwt_access_minutes)

    @property
    def refresh_ttl(self) -> timedelta:
        return timedelta(days=self.jwt_refresh_days)

    @property
    def is_dev(self) -> bool:
        return self.app_env in {"development", "dev", "test"}

    @property
    def cors_origins(self) -> list[str]:
        extras = [origin.strip() for origin in self.cors_extra_origins.split(",") if origin.strip()]
        return list(
            dict.fromkeys(
                [
                    self.frontend_url,
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    *extras,
                ]
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
