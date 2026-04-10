from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_port: int = 8080

    database_url: str = "postgresql+psycopg://proofread:proofread@localhost:5432/proofread"
    redis_url: str = "redis://localhost:6379/0"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    default_timeout_sec: int = 300


settings = Settings()
