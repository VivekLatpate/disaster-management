from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://disaster:disaster_password@localhost:5432/disaster"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    storage_dir: str = "./uploads"
    max_image_size_bytes: int = 10 * 1024 * 1024
    firecrawl_api_key: str | None = None
    weatherapi: str | None = None
    weatherapi_base_url: str = "https://api.weatherapi.com/v1"
    assemblyai_api_key: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()

