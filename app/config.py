from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración alineada con recu-judicial para PostgreSQL / Cloud SQL:
    - DATABASE_* o DB_* (y `database_url` opcional).
    - Host TCP o socket Unix `/cloudsql/PROYECTO:REGION:INSTANCIA`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="development")
    app_name: str = Field(default="recu-svp-nuevo")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8010)
    log_level: str = Field(default="INFO")

    # Base de datos (mismo criterio que judicial: ver model_post_init)
    database_url: Optional[str] = None
    database_host: Optional[str] = None
    db_host: Optional[str] = None
    database_port: int = 5432
    db_port: int = 5432
    database_name: Optional[str] = None
    db_name: Optional[str] = None
    database_user: Optional[str] = None
    db_user: Optional[str] = None
    database_password: Optional[str] = None
    db_password: Optional[str] = None
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

    svp_ci_texto_abierto_desde_span: bool = Field(
        default=True,
        description=(
            "Si es true, rellena complemento_indirecto_text desde el span cuando el catálogo "
            "permite CI abierto y el motor de encadenamiento dejó CI vacío."
        ),
    )

    ia_console_pretty: bool = Field(default=True)

    # Pool SQLAlchemy (mismo orden de magnitud que recu-judicial app/db/session.py)
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=20)

    def model_post_init(self, __context) -> None:  # noqa: ARG002
        if not self.database_host and self.db_host:
            object.__setattr__(self, "database_host", self.db_host)
        if self.database_port == 5432 and self.db_port != 5432:
            object.__setattr__(self, "database_port", self.db_port)
        if not self.database_name and self.db_name:
            object.__setattr__(self, "database_name", self.db_name)
        if not self.database_user and self.db_user:
            object.__setattr__(self, "database_user", self.db_user)
        if not self.database_password and self.db_password:
            object.__setattr__(self, "database_password", self.db_password)

        url_complete = bool(self.database_url and "@" in self.database_url)
        if not url_complete:
            if not self.database_host:
                raise ValueError("DATABASE_HOST o DB_HOST es requerido")
            if not self.database_name:
                raise ValueError("DATABASE_NAME o DB_NAME es requerido")
            if not self.database_user:
                raise ValueError("DATABASE_USER o DB_USER es requerido")
            if not self.database_password:
                raise ValueError("DATABASE_PASSWORD o DB_PASSWORD es requerido")

    @property
    def sqlalchemy_database_uri(self) -> str:
        """URL síncrona psycopg2; misma lógica que judicial.database_url_sync."""
        if self.database_url and "@" in self.database_url:
            return self.database_url.replace("postgresql://", "postgresql+psycopg2://")

        user = quote_plus(self.database_user)
        password = quote_plus(self.database_password)

        if self.database_host.startswith("/cloudsql/"):
            return (
                f"postgresql+psycopg2://{user}:{password}@/{self.database_name}"
                f"?host={self.database_host}"
            )
        return (
            f"postgresql+psycopg2://{user}:{password}@{self.database_host}:"
            f"{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
