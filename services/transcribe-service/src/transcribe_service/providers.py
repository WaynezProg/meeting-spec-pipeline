import os
from pathlib import Path

from .schemas import Segment


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def transcribe_with_provider(provider: str, audio_path: Path, language: str) -> list[Segment]:
    if provider == "mock":
        return [
            Segment(
                segment_id="seg-0001",
                start=0.0,
                end=8.0,
                text="我們今天要討論需求單如何用 AI 摘要，原始內容不能被覆蓋。",
                speaker=None,
                source_file=str(audio_path),
            ),
            Segment(
                segment_id="seg-0002",
                start=8.0,
                end=17.5,
                text="後台需要有審核狀態，API 欄位目前還沒有定義。",
                speaker=None,
                source_file=str(audio_path),
            ),
        ]
    if provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            raise ProviderError("MISSING_API_KEY", "GROQ_API_KEY is required for groq provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "groq adapter boundary is defined but not implemented in MVP")
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ProviderError("MISSING_API_KEY", "OPENAI_API_KEY is required for openai provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "openai adapter boundary is defined but not implemented in MVP")
    if provider == "local":
        if not os.getenv("LOCAL_WHISPER_COMMAND"):
            raise ProviderError("MISSING_LOCAL_COMMAND", "LOCAL_WHISPER_COMMAND is required for local provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "local adapter boundary is defined but not implemented in MVP")
    raise ProviderError("UNSUPPORTED_PROVIDER", f"Unsupported provider: {provider}")
