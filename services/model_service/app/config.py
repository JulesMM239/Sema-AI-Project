from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "postgresql+psycopg://sema:sema@db:5432/sema_model"
    redis_url: str = "redis://redis:6379/0"
    data_dir: str = "/data"
    service_port: int = 8010

settings = Settings()
