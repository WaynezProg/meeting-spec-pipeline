import os
from pathlib import Path

from .config import ConfigError, get_plugin_config, load_openclaw_config, resolve_provider_field
from .schemas import Segment


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _resolve_api_key(openclaw_config: dict, config: dict, provider: str, env_name: str) -> str | None:
    try:
        configured = resolve_provider_field(config, provider, "apiKey", openclaw_config)
    except ConfigError as exc:
        raise ProviderError(exc.code, exc.message) from exc
    return configured or os.getenv(env_name)


def _resolve_local_command(openclaw_config: dict, config: dict) -> str | None:
    try:
        configured = resolve_provider_field(config, "local", "command", openclaw_config)
    except ConfigError as exc:
        raise ProviderError(exc.code, exc.message) from exc
    return configured or os.getenv("LOCAL_WHISPER_COMMAND")


def transcribe_with_provider(provider: str, audio_path: Path, language: str) -> list[Segment]:
    openclaw_config = load_openclaw_config()
    config = get_plugin_config(openclaw_config)
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
        if not _resolve_api_key(openclaw_config, config, "groq", "GROQ_API_KEY"):
            raise ProviderError("MISSING_API_KEY", "GROQ_API_KEY is required for groq provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "groq adapter boundary is defined but not implemented in MVP")
    if provider == "openai":
        if not _resolve_api_key(openclaw_config, config, "openai", "OPENAI_API_KEY"):
            raise ProviderError("MISSING_API_KEY", "OPENAI_API_KEY is required for openai provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "openai adapter boundary is defined but not implemented in MVP")
    if provider == "local":
        if not _resolve_local_command(openclaw_config, config):
            raise ProviderError("MISSING_LOCAL_COMMAND", "LOCAL_WHISPER_COMMAND is required for local provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "local adapter boundary is defined but not implemented in MVP")
    raise ProviderError("UNSUPPORTED_PROVIDER", f"Unsupported provider: {provider}")
