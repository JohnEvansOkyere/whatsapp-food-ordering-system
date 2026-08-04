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

    # SMS — carries the tracking link alongside the WhatsApp receipt, and the
    # verification codes for phone sign-in. Disabled by default so no live SMS
    # is sent until someone turns it on deliberately.
    #
    # SMS_PROVIDERS is an ordered failover chain: each is tried in turn until
    # one accepts the message, and providers with no credentials are skipped.
    # Sender IDs must be telco-approved on the account (max 11 characters).
    sms_enabled: bool = False
    sms_providers: str = "moolre"

    arkesel_api_url: str = "https://sms.arkesel.com/sms/api"
    arkesel_api_key: str = ""
    arkesel_sender_id: str = "Veloxa"

    moolre_api_url: str = "https://api.moolre.com/open/sms/send"
    moolre_vas_key: str = ""
    moolre_sender_id: str = "Veloxa"

    # App
    menu_web_app_url: str = "https://your-menu-app.vercel.app"
    public_web_url: str = "http://localhost:3000"
    owner_whatsapp: str
    restaurant_name: str = "HallMark Cafe"
    customer_support_whatsapp: str = "+233544954643"
    staff_auth_secret: str = "local-demo-secret-change-before-production"
    customer_auth_secret: str = "local-customer-secret-change-before-production"
    customer_token_ttl_minutes: int = 43200  # 30 days
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

    @property
    def sms_providers_list(self) -> list[str]:
        """Providers to try, in order. Blank entries are dropped."""
        return [p.strip().lower() for p in self.sms_providers.split(",") if p.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
