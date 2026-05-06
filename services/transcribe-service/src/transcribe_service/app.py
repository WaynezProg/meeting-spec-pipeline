from fastapi import FastAPI, HTTPException

from .chunking import UnsupportedAudioFormatError, build_meeting_id, validate_audio_path
from .providers import ProviderError, transcribe_with_provider
from .schemas import TranscribeRequest, TranscribeResponse


app = FastAPI(title="Meeting Transcribe Service")


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(request: TranscribeRequest) -> TranscribeResponse:
    try:
        audio_path = validate_audio_path(request.audio_path)
        segments = transcribe_with_provider(request.provider, audio_path, request.language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "AUDIO_NOT_FOUND", "message": str(exc)}) from exc
    except UnsupportedAudioFormatError as exc:
        raise HTTPException(status_code=400, detail={"code": "UNSUPPORTED_AUDIO_FORMAT", "message": str(exc)}) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc

    return TranscribeResponse(
        meeting_id=build_meeting_id(audio_path),
        segments=segments,
        errors=[],
    )
