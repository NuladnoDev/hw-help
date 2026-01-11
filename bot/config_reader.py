from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    bot_token: SecretStr
    creator_id: int = 0  # Добавьте CREATOR_ID в .env
    supabase_url: str
    supabase_key: SecretStr

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


config = Settings()
