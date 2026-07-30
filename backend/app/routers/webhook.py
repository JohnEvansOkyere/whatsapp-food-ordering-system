"""
WhatsApp webhook routes.

Both `/webhook/*` and `/webhooks/*` remain available during the route-family
cutover so existing provider configuration does not break.
"""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.config import get_settings
from app.services import session_store as store
from app.services.groq_service import handle_incoming_message
from app.services.whatsapp import send_text_message
from app.services.logging_utils import mask_phone

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


async def _verify_whatsapp_webhook(
    hub_mode: str | None,
    hub_challenge: str | None,
    hub_verify_token: str | None,
):
    settings = get_settings()

    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        logger.info("WhatsApp webhook verified")
        return int(hub_challenge)

    logger.warning("Webhook verification failed - token mismatch")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.get("/webhook/whatsapp")
@router.get("/webhooks/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    return await _verify_whatsapp_webhook(hub_mode, hub_challenge, hub_verify_token)


@router.post("/webhook/whatsapp")
@router.post("/webhooks/whatsapp")
async def receive_message(request: Request):
    raw_body = await request.body()
    settings = get_settings()
    if settings.meta_app_secret:
        supplied_signature = request.headers.get("x-hub-signature-256", "")
        expected_signature = "sha256=" + hmac.new(
            settings.meta_app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
    try:
        body = json.loads(raw_body)
    except Exception:
        return {"status": "invalid_json"}

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]["value"]

        if "messages" not in changes:
            return {"status": "no_message"}

        message = changes["messages"][0]
        message_id: str = message.get("id", "")
        sender: str = message["from"]
        msg_type: str = message.get("type", "")

        if message_id and store.has_processed_message(message_id):
            logger.info(
                "Ignoring duplicate WhatsApp message id=%s from %s",
                message_id,
                mask_phone(sender),
            )
            return {"status": "duplicate_ignored"}

        branch_id: str | None = None
        referral = message.get("referral", {})
        if referral:
            ref_source = referral.get("ref", "")
            if ref_source.startswith("branch_"):
                branch_id = ref_source.replace("branch_", "")
                store.set_branch_id(sender, branch_id)

        if msg_type == "text":
            text: str = message["text"]["body"].strip()
            if not text:
                return {"status": "empty_message"}

            reply = await handle_incoming_message(sender, text, branch_id)
            await send_text_message(sender, reply)
            if message_id:
                store.mark_message_processed(message_id)
        elif msg_type in ("image", "audio", "video", "document"):
            await send_text_message(
                sender,
                "Hi! I can only read text messages right now. Type *Hi* to start ordering.",
            )
            if message_id:
                store.mark_message_processed(message_id)
        else:
            logger.debug("Ignored message type '%s' from %s", msg_type, mask_phone(sender))
    except (KeyError, IndexError) as exc:
        logger.warning("Webhook payload parse warning: %s", exc)
    except Exception as exc:
        logger.error("Webhook handler error: %s", exc, exc_info=True)

    return {"status": "ok"}
