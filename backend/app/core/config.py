from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_db_url(url: str) -> str:
    # Render (and Heroku-style) Postgres connection strings use the "postgres://" scheme,
    # which SQLAlchemy no longer accepts directly — rewrite to the psycopg2 dialect URL.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://tranable:tranable_dev@localhost:5432/tranable"
    app_name: str = "Tranable Logistics Platform"
    env: str = "dev"

    model_config = SettingsConfigDict(env_file=".env")

    def model_post_init(self, __context) -> None:
        self.database_url = _normalize_db_url(self.database_url)


settings = Settings()
