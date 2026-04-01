from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development")
    app_name: str = Field(default="recu-svp-nuevo")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8010)
    log_level: str = Field(default="INFO")

    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="recu_judicial")
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="postgres")
    db_schema: str = Field(default="svp")

    openai_api_key: str = Field(default="")
    openai_base_url: str | None = Field(default=None)
    ai_model_cheap: str = Field(default="gpt-4.1-mini")
    ai_model_strong: str = Field(default="gpt-4.1")
    ai_max_tokens: int = Field(default=1000)
    ai_temperature: float = Field(default=0.1)
    ai_timeout: int = Field(default=60)
    ai_max_retries: int = Field(default=2)
    selection_confidence_threshold: float = Field(default=0.75)

    auto_section_strategy: str = Field(default="resuelve_only")
    max_candidates: int = Field(default=5)
    max_antecedent_candidates: int = Field(
        default=10,
        description="Tope de filas candidatas a antecedente (public.actuacion).",
    )
    judicial_actuacion_table: str = Field(
        default="public.actuacion",
        description="Tabla cualificada de actuaciones en recu-judicial.",
    )

    # Bloques JSON indentados en consola (ademas del logger)
    ia_console_pretty: bool = Field(default=True)

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
