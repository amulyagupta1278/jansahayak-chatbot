from fastapi import APIRouter

from ..models.schemas import SpeechToTextRequest, VoiceRequest, VoiceResponse
from ..services.request_inspector import inspector
from ..services.sarvam_service import SarvamService

router = APIRouter(prefix="/voice", tags=["voice"])
service = SarvamService()


@router.post("/tts", response_model=VoiceResponse)
def tts(payload: VoiceRequest):
    result = service.text_to_speech(payload.text, payload.language_code)
    response = VoiceResponse(**result)
    inspector.record(
        path="/voice/tts",
        method="POST",
        channel="voice-tts",
        request_data=payload.model_dump(),
        response_data=response.model_dump(),
    )
    return response


@router.post("/stt")
def stt(payload: SpeechToTextRequest):
    response = service.speech_to_text(
        transcript_hint=payload.transcript_hint,
        language_code=payload.language_code,
        audio_base64=payload.audio_base64,
        mime_type=payload.mime_type,
    )
    inspector.record(
        path="/voice/stt",
        method="POST",
        channel="voice-stt",
        request_data=payload.model_dump(),
        response_data=response,
    )
    return response
