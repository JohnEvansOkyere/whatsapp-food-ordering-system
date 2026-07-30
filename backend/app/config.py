from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_key: str

    # Meta WhatsApp
    meta_access_token: str
    meta_phone_number_id: str
    meta_verify_token: str
    meta_app_secret: str = ""

    # AI — primary: Groq, fallback: OpenAI, third: Gemini
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: str
    gemini_model: str = "gemini-1.5-flash"

    # App
    menu_web_app_url: str = "https://your-menu-app.vercel.app"
    public_web_url: str = "http://localhost:3000"
    owner_whatsapp: str
    restaurant_name: str = "Accra Eats"
    customer_support_whatsapp: str = "+233544954643"
    staff_auth_secret: str = "local-demo-secret-change-before-production"
    staff_demo_password: str = "ChangeMe123!"
    staff_token_ttl_minutes: int = 720
    enforce_business_hours: bool = False
    rate_limit_enabled: bool = True
    app_environment: str = "development"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
