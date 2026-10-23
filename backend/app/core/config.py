"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # LLM
    LLM_API_KEY: str = ""
    LLM_PROVIDER: str = "anthropic"  # openai, anthropic, gemini, ollama
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    LLM_BASE_URL: str = ""  # optional override for OpenAI-compatible / Ollama endpoints
    LLM_MAX_TOKENS: int = 4096

    # Auth
    JWT_SECRET: str = "devops-tower-dev-secret-change-in-prod"
    JWT_EXPIRY_HOURS: int = 24
    OAUTH_CLIENT_ID: str = ""
    OAUTH_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_URI: str = ""
    SAML_IDP_ENTITY: str = ""
    SAML_IDP_CERT: str = ""
    SAML_ACS_URL: str = ""

    # Storage
    DATA_DIR: str = "./data"
    LOG_DIR: str = "./logs"

    # Deployment
    DEPLOY_HEALTH_CHECK_INTERVAL: int = 10
    DEPLOY_ROLLBACK_THRESHOLD: float = 0.05
    CANARY_STEPS: str = "5,25,50,100"

    @property
    def canary_steps_list(self) -> list[int]:
        return [int(s) for s in self.CANARY_STEPS.split(",") if s.strip()]


settings = Settings()
