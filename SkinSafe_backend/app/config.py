from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_host: str
    database_port: int = 5432
    database_name: str
    database_user: str
    database_password: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
