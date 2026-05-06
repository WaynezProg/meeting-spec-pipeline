import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import ConfigError, get_plugin_config, load_openclaw_config, resolve_provider_field
from .schemas import Segment, ServiceError


GROQ_TRANSCRIPTIONS_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
DEFAULT_TRANSCRIBE_ORDER = ["groq", "openai", "local"]
DEFAULT_DIARIZE_ORDER = ["openai", "local"]
DEFAULT_MODELS = {
    "groq": "whisper-large-v3-turbo",
    "openai": "gpt-4o-mini-transcribe",
    "openai_diarize": "gpt-4o-transcribe-diarize",
}


@dataclass
class ProviderResult:
    segments: list[Segment]
    provider: str
    model: str | None
    fallback_attempts: list[ServiceError]
    diarize: bool


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str, fallback_attempts: list[ServiceError] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.fallback_attempts = fallback_attempts or []


def _provider_config(config: dict[str, Any], provider: str) -> dict[str, Any]:
    value = config.get("providers", {}).get(provider, {})
    return value if isinstance(value, dict) else {}


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


def _model_for(config: dict[str, Any], provider: str, diarize: bool) -> str:
    provider_config = _provider_config(config, provider)
    if provider == "openai" and diarize:
        return str(provider_config.get("diarizeModel") or DEFAULT_MODELS["openai_diarize"])
    return str(provider_config.get("model") or DEFAULT_MODELS[provider])


def _fallback_order(config: dict[str, Any], provider: str, diarize: bool) -> list[str]:
    if provider != "auto":
        return [provider]
    fallback = config.get("fallback", {})
    key = "diarizeOrder" if diarize else "order"
    configured = fallback.get(key) if isinstance(fallback, dict) else None
    if isinstance(configured, list) and configured:
        return [str(item) for item in configured]
    return DEFAULT_DIARIZE_ORDER if diarize else DEFAULT_TRANSCRIBE_ORDER


def _segments_from_payload(payload: dict[str, Any], audio_path: Path, duration: float | None = None) -> list[Segment]:
    raw_segments = payload.get("segments")
    if isinstance(raw_segments, list) and raw_segments:
        segments = []
        for index, item in enumerate(raw_segments, start=1):
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            segments.append(
                Segment(
                    segment_id=f"seg-{index:04d}",
                    start=float(item.get("start") or 0.0),
                    end=float(item.get("end") or item.get("stop") or 0.0),
                    text=text,
                    speaker=item.get("speaker"),
                    source_file=str(audio_path),
                )
            )
        if segments:
            return segments

    text = str(payload.get("text") or "").strip()
    if not text:
        raise ProviderError("EMPTY_TRANSCRIPT", "Transcription response did not contain text")
    return [
        Segment(
            segment_id="seg-0001",
            start=0.0,
            end=float(duration or payload.get("duration") or 0.0),
            text=text,
            speaker=None,
            source_file=str(audio_path),
        )
    ]


def _post_audio_transcription(
    client: httpx.Client,
    *,
    url: str,
    api_key: str,
    audio_path: Path,
    data: dict[str, Any],
) -> dict[str, Any]:
    with audio_path.open("rb") as handle:
        response = client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            data={key: str(value) for key, value in data.items()},
            files={"file": (audio_path.name, handle, "application/octet-stream")},
        )
    if response.status_code >= 400:
        raise ProviderError("STT_API_FAILED", f"{response.status_code}: {response.text}")
    return response.json()


def _transcribe_groq(
    client: httpx.Client,
    openclaw_config: dict[str, Any],
    config: dict[str, Any],
    audio_path: Path,
    language: str,
) -> ProviderResult:
    api_key = _resolve_api_key(openclaw_config, config, "groq", "GROQ_API_KEY")
    if not api_key:
        raise ProviderError("MISSING_API_KEY", "GROQ_API_KEY is required for groq provider")

    model = _model_for(config, "groq", diarize=False)
    payload = _post_audio_transcription(
        client,
        url=GROQ_TRANSCRIPTIONS_URL,
        api_key=api_key,
        audio_path=audio_path,
        data={
            "model": model,
            "language": language,
            "response_format": "verbose_json",
            "temperature": 0,
        },
    )
    return ProviderResult(_segments_from_payload(payload, audio_path), "groq", model, [], False)


def _transcribe_openai(
    client: httpx.Client,
    openclaw_config: dict[str, Any],
    config: dict[str, Any],
    audio_path: Path,
    language: str,
    diarize: bool,
) -> ProviderResult:
    api_key = _resolve_api_key(openclaw_config, config, "openai", "OPENAI_API_KEY")
    if not api_key:
        raise ProviderError("MISSING_API_KEY", "OPENAI_API_KEY is required for openai provider")

    model = _model_for(config, "openai", diarize=diarize)
    data: dict[str, Any] = {"model": model, "language": language}
    if diarize:
        data["response_format"] = "diarized_json"
    else:
        data["response_format"] = "json"
    payload = _post_audio_transcription(
        client,
        url=OPENAI_TRANSCRIPTIONS_URL,
        api_key=api_key,
        audio_path=audio_path,
        data=data,
    )
    usage = payload.get("usage") if isinstance(payload, dict) else None
    duration = usage.get("seconds") if isinstance(usage, dict) else None
    return ProviderResult(_segments_from_payload(payload, audio_path, duration), "openai", model, [], diarize)


def _run_local_command(command: str, audio_path: Path, language: str) -> dict[str, Any]:
    if "{audio_path}" in command or "{language}" in command:
        rendered = command.format(audio_path=str(audio_path), language=language)
        args = shlex.split(rendered)
    else:
        args = [*shlex.split(command), str(audio_path)]
    completed = subprocess.run(args, check=False, capture_output=True, text=True, timeout=3600)
    if completed.returncode != 0:
        raise ProviderError("LOCAL_TRANSCRIBE_FAILED", completed.stderr.strip() or completed.stdout.strip())
    output = completed.stdout.strip()
    if not output:
        raise ProviderError("EMPTY_TRANSCRIPT", "Local transcription command returned no output")
    try:
        parsed = json.loads(output)
        return parsed if isinstance(parsed, dict) else {"text": output}
    except json.JSONDecodeError:
        return {"text": output}


def _transcribe_local(
    openclaw_config: dict[str, Any],
    config: dict[str, Any],
    audio_path: Path,
    language: str,
) -> ProviderResult:
    command = _resolve_local_command(openclaw_config, config)
    if not command:
        raise ProviderError("MISSING_LOCAL_COMMAND", "LOCAL_WHISPER_COMMAND is required for local provider")
    payload = _run_local_command(command, audio_path, language)
    return ProviderResult(_segments_from_payload(payload, audio_path), "local", "local-command", [], False)


def _transcribe_mock(audio_path: Path) -> ProviderResult:
    return ProviderResult(
        [
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
        ],
        "mock",
        "mock",
        [],
        False,
    )


def transcribe_with_provider(
    provider: str,
    audio_path: Path,
    language: str,
    diarize: bool = False,
    client: httpx.Client | None = None,
) -> ProviderResult:
    openclaw_config = load_openclaw_config()
    config = get_plugin_config(openclaw_config)
    order = _fallback_order(config, provider, diarize)
    attempts: list[ServiceError] = []
    owns_client = client is None
    http = client or httpx.Client(timeout=120)

    try:
        for candidate in order:
            try:
                if candidate == "mock":
                    result = _transcribe_mock(audio_path)
                elif candidate == "groq":
                    if diarize:
                        raise ProviderError("DIARIZE_NOT_SUPPORTED", "groq provider does not support diarization")
                    result = _transcribe_groq(http, openclaw_config, config, audio_path, language)
                elif candidate == "openai":
                    result = _transcribe_openai(http, openclaw_config, config, audio_path, language, diarize)
                elif candidate == "local":
                    result = _transcribe_local(openclaw_config, config, audio_path, language)
                else:
                    raise ProviderError("UNSUPPORTED_PROVIDER", f"Unsupported provider: {candidate}")
                result.fallback_attempts = attempts
                return result
            except ProviderError as exc:
                attempts.append(ServiceError(code=exc.code, message=exc.message, source_file=str(audio_path)))
                if provider != "auto":
                    raise
        messages = "; ".join(f"{item.code}: {item.message}" for item in attempts)
        raise ProviderError("STT_API_FAILED", f"All transcription providers failed: {messages}", attempts)
    finally:
        if owns_client:
            http.close()
