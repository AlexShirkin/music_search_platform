from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql://app:app@localhost:5432/music_search",
        alias="DATABASE_URL",
    )
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")

    s3_endpoint: str = Field(default="http://localhost:9000", alias="S3_ENDPOINT")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="music-search", alias="S3_BUCKET")
    s3_use_ssl: bool = Field(default=False, alias="S3_USE_SSL")

    musicnn_embedding_path: str = Field(
        default="models/musicnn/musicnn_embedding.onnx",
        alias="MUSICNN_EMBEDDING_PATH",
    )
    musicnn_prediction_path: str = Field(
        default="models/musicnn/musicnn_prediction.onnx",
        alias="MUSICNN_PREDICTION_PATH",
    )

    search_api_url: str = Field(default="http://localhost:8000", alias="SEARCH_API_URL")
    web_ui_origin: str = Field(default="http://localhost:3000", alias="WEB_UI_ORIGIN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
