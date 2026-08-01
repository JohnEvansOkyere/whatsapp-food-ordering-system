from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import admin, auth, customer_auth, menu, orders, public, webhook
from app.services.rate_limit import rate_limit_sensitive_routes
from app.database import get_supabase
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)

settings = get_settings()
if settings.app_environment.lower() == "production" and (
    settings.staff_auth_secret == "local-demo-secret-change-before-production"
    or settings.staff_demo_password == "ChangeMe123!"
    or settings.customer_auth_secret
    == "local-customer-secret-change-before-production"
):
    raise RuntimeError(
        "Production requires unique STAFF_AUTH_SECRET, STAFF_DEMO_PASSWORD and "
        "CUSTOMER_AUTH_SECRET values"
    )
deploy_sha = os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or "unknown"

app = FastAPI(
    title="WhatsApp Food Ordering API",
    description="Backend for WhatsApp food ordering system — Veloxa Technology Ltd",
    version="1.0.0",
)

# CORS — allow menu web app to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(rate_limit_sensitive_routes)

# Routers
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(customer_auth.router)
app.include_router(admin.router)
app.include_router(orders.router)
app.include_router(webhook.router)
app.include_router(menu.router)

logging.getLogger(__name__).info(
    "Starting API build commit=%s whatsapp_sender=text",
    deploy_sha[:7] if deploy_sha != "unknown" else deploy_sha,
)


@app.get("/")
async def root():
    return {
        "service": "WhatsApp Food Ordering API",
        "status": "running",
        "version": "1.0.0",
        "commit": deploy_sha,
        "whatsapp_sender": "text",
        "by": "Veloxa Technology Ltd",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    checks = {
        "database": False,
        "whatsapp_configured": bool(
            settings.meta_access_token and settings.meta_phone_number_id
        ),
    }
    try:
        get_supabase().table("branches").select("id").limit(1).execute()
        checks["database"] = True
    except Exception as exc:
        logging.getLogger(__name__).warning("Readiness database check failed: %s", exc)

    ready = all(checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )
