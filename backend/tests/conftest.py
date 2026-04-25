import os
import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key")
os.environ.setdefault("META_ACCESS_TOKEN", "test-meta-token")
os.environ.setdefault("META_PHONE_NUMBER_ID", "123456")
os.environ.setdefault("META_VERIFY_TOKEN", "verify-token")
os.environ.setdefault("GROQ_API_KEY", "groq-test")
os.environ.setdefault("OPENAI_API_KEY", "openai-test")
os.environ.setdefault("GEMINI_API_KEY", "gemini-test")
os.environ.setdefault("OWNER_WHATSAPP", "233000000000")

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture
def app():
    from app.main import app

    return app
