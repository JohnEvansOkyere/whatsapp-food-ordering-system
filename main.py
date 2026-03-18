from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import orders, webhook, menu
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)

settings = get_settings()

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

# Routers
app.include_router(orders.router)
app.include_router(webhook.router)
app.include_router(menu.router)


@app.get("/")
async def root():
    return {
        "service": "WhatsApp Food Ordering API",
        "status": "running",
        "version": "1.0.0",
        "by": "Veloxa Technology Ltd",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
