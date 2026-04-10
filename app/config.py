from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_port: int = 8080

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

    @property
    def effective_rq_job_timeout_sec(self) -> int:
        if self.rq_job_timeout_sec is not None:
            return self.rq_job_timeout_sec
        return self.default_timeout_sec + 60

    @property
    def use_api_key_llm(self) -> bool:
        return bool(self.llm_api_key and self.effective_llm_base_url and self.effective_llm_model)

    @property
    def effective_llm_base_url(self) -> str:
        return (self.llm_base_url or self.ollama_base_url).rstrip("/")

    @property
    def effective_llm_model(self) -> str:
        return self.llm_model or self.ollama_model


settings = Settings()
