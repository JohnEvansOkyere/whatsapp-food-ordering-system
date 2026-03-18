from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str

    meta_access_token: str
    meta_phone_number_id: str
    meta_verify_token: str

    owner_whatsapp: str
    restaurant_name: str = "Accra Eats"

    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
