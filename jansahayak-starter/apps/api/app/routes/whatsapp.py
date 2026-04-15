from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from xml.sax.saxutils import escape

from ..core.config import get_settings
from ..models.schemas import WhatsAppWebhookRequest
from ..services.orchestrator import Orchestrator

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
orchestrator = Orchestrator()


@router.post("/webhook")
def webhook(payload: WhatsAppWebhookRequest):
    """Demo JSON endpoint used by the web UI simulation."""
    response = orchestrator.answer(
        message=payload.message,
        session_id=payload.from_number,
        channel="whatsapp",
        language_code=None,
        location_hint=None,
    )
    return {
        "to": payload.from_number,
        "channel": "whatsapp-mock",
        "reply": response["answer"],
        "meta": {
            "detected_language": response["detected_language"],
            "location": response["location"],
        },
    }


@router.post("/twilio", response_class=PlainTextResponse)
async def twilio_webhook(request: Request):
    """
    Real Twilio WhatsApp webhook.
    Configure this URL in Twilio Console → Messaging → Sandbox settings.
    Twilio sends form-encoded POST data; we reply with TwiML XML.
    """
    settings = get_settings()

    form = await request.form()
    from_number: str = form.get("From", "")
    body: str = form.get("Body", "")
    message_sid: str = form.get("MessageSid", "")
    media_count_raw: str = form.get("NumMedia", "0")
    media_content_type_0: str = form.get("MediaContentType0", "")

    if not from_number:
        raise HTTPException(status_code=400, detail="Missing From field")

    # Validate Twilio signature in production only.
    # Skipped in DEBUG mode because behind ngrok the request URL seen by the
    # server is http://localhost:8000/... while Twilio signs the public ngrok URL.
    if settings.twilio_account_sid and settings.twilio_auth_token and not settings.debug:
        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(settings.twilio_auth_token)
            signature = request.headers.get("X-Twilio-Signature", "")
            # Reconstruct the public URL using forwarded headers (set by ngrok/proxy)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
            forwarded_host = request.headers.get("X-Forwarded-Host", request.url.netloc)
            public_url = f"{forwarded_proto}://{forwarded_host}{request.url.path}"
            params = dict(form)
            if not validator.validate(public_url, params, signature):
                raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        except ImportError:
            pass  # twilio not installed, skip validation

    try:
        media_count = int(media_count_raw or "0")
    except ValueError:
        media_count = 0

    incoming_message = (body or "").strip()

    # Twilio WhatsApp voice notes are sent as media with empty Body.
    if not incoming_message and media_count > 0 and media_content_type_0.startswith("audio/"):
        reply_text = (
            "I received your voice note, but voice-note transcription is not enabled yet. "
            "Please send your message as text for now."
        )
    elif not incoming_message:
        reply_text = "Please send a text message so I can help you."
    else:
        response = orchestrator.answer(
            message=incoming_message,
            session_id=from_number,
            channel="whatsapp",
            language_code=None,
            location_hint=None,
        )
        reply_text = response["answer"]

    twiml = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        f"<Response><Message>{escape(reply_text)}</Message></Response>"
    )
    return PlainTextResponse(content=twiml, media_type="application/xml")
