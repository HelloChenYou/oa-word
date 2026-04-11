from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_port: int = 8080
    admin_api_token: str | None = None
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auth_secret_key: str = "change-me-in-prod"
    auth_token_expire_sec: int = 12 * 60 * 60
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "admin123456"

    database_url: str = "postgresql+psycopg://proofread:proofread@localhost:5432/proofread"
    redis_url: str = "redis://localhost:6379/0"

    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    default_timeout_sec: int = 600
    rq_job_timeout_sec: int | None = None
    rq_result_ttl_sec: int = 86400
    max_task_text_chars: int = 20000
    max_template_file_bytes: int = 2 * 1024 * 1024
    max_template_text_chars: int = 50000
    max_issues_per_task: int = 200
    max_active_tasks: int = 20
    submit_rate_limit_window_sec: int = 60
    submit_rate_limit_max_requests: int = 10
    max_error_msg_chars: int = 2000
    task_max_retries: int = 1
    retryable_task_error_types: str = "timeout,llm_http_error,unknown_error"

    @property
    def effective_rq_job_timeout_sec(self) -> int:
        if self.rq_job_timeout_sec is not None:
            return self.rq_job_timeout_sec
        return self.default_timeout_sec + 60

    @property
    def use_api_key_llm(self) -> bool:
        return bool(self.llm_api_key and self.effective_llm_base_url and self.effective_llm_model)

    @property
    def admin_auth_enabled(self) -> bool:
        return bool(self.admin_api_token and self.admin_api_token.strip())

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def effective_llm_base_url(self) -> str:
        return (self.llm_base_url or self.ollama_base_url).rstrip("/")

    @property
    def effective_llm_model(self) -> str:
        return self.llm_model or self.ollama_model

    @property
    def retryable_task_error_types_set(self) -> set[str]:
        return {item.strip() for item in self.retryable_task_error_types.split(",") if item.strip()}


settings = Settings()


def validate_runtime_settings() -> None:
    if settings.app_env.lower() == "prod":
        if not settings.admin_auth_enabled and not settings.auth_secret_key.strip():
            raise RuntimeError("AUTH_SECRET_KEY or ADMIN_API_TOKEN must be configured when APP_ENV=prod")
        if settings.auth_secret_key == "change-me-in-prod":
            raise RuntimeError("AUTH_SECRET_KEY must be changed when APP_ENV=prod")
    if not settings.cors_allow_origins_list:
        raise RuntimeError("CORS_ALLOW_ORIGINS must contain at least one origin")
