"""
WhatsApp Webhook Router.

GET  /webhook/whatsapp  — Meta verification handshake
POST /webhook/whatsapp  — Incoming customer messages

QR codes carry branch_id as a query param in the wa.me link.
When customer scans and sends first message, we extract it from
the referral payload Meta sends.

Always returns 200 to Meta — non-200 causes Meta to retry endlessly.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Query
from app.config import get_settings
from app.services.groq_service import handle_incoming_message
from app.services.whatsapp import send_text_message
from app.services import session_store as store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta webhook verification — called once on setup."""
    settings = get_settings()

    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        logger.info("WhatsApp webhook verified")
        return int(hub_challenge)

    logger.warning("Webhook verification failed — token mismatch")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/whatsapp")
async def receive_message(request: Request):
    """
    Receive and process incoming WhatsApp messages.
    Extracts sender, message text, and optional branch_id from QR referral.
    """
    try:
        body = await request.json()
    except Exception:
        return {"status": "invalid_json"}

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]["value"]

        # Ignore delivery receipts and read notifications
        if "messages" not in changes:
            return {"status": "no_message"}

        message = changes["messages"][0]
        sender: str = message["from"]
        msg_type: str = message.get("type", "")

        # Extract branch_id from QR referral payload (Meta sends this
        # when customer scans a wa.me link with ?ref=branch_XXXXX)
        branch_id: str | None = None
        referral = message.get("referral", {})
        if referral:
            ref_source = referral.get("ref", "")
            if ref_source.startswith("branch_"):
                branch_id = ref_source.replace("branch_", "")
                store.set_branch_id(sender, branch_id)

        # Handle text messages
        if msg_type == "text":
            text: str = message["text"]["body"].strip()
            if not text:
                return {"status": "empty_message"}

            reply = await handle_incoming_message(sender, text, branch_id)
            await send_text_message(sender, reply)

        # Handle image/audio/video — politely decline for now
        elif msg_type in ("image", "audio", "video", "document"):
            await send_text_message(
                sender,
                "Hi! I can only read text messages right now. "
                "Type *Hi* to start ordering. 😊"
            )

        # Ignore other types silently
        else:
            logger.debug(f"Ignored message type '{msg_type}' from {sender}")

    except (KeyError, IndexError) as e:
        logger.warning(f"Webhook payload parse warning: {e}")
    except Exception as e:
        logger.error(f"Webhook handler error: {e}", exc_info=True)

    # Always 200 — Meta will retry on anything else
    return {"status": "ok"}
