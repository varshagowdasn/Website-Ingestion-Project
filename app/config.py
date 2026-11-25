from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_region: str = "us-east-1"
    s3_endpoint_url: str | None = "http://localhost:4566"
    s3_bucket: str = "website-assets"
    s3_prefix: str = "website/"
    site_root: str = "./data/site"
    base_url: str = "http://127.0.0.1:8000"
    ingestion_lookback_hours: int = 24
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
