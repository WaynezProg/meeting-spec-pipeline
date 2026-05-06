import json
import os
from pathlib import Path
from typing import Any


PLUGIN_ID = "meeting-transcribe-cloud"


class ConfigError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def default_openclaw_config_path() -> Path:
    override = os.getenv("OPENCLAW_CONFIG_FILE")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".openclaw" / "openclaw.json"


def load_openclaw_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path).expanduser().resolve() if config_path else default_openclaw_config_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_plugin_config(config_path: str | Path | None = None) -> dict[str, Any]:
    payload = load_openclaw_config(config_path)
    return get_plugin_config(payload)


def get_plugin_config(payload: dict[str, Any]) -> dict[str, Any]:
    return (
        payload.get("plugins", {})
        .get("entries", {})
        .get(PLUGIN_ID, {})
        .get("config", {})
    )


def _expand_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _read_json_path(payload: dict[str, Any], secret_path: str) -> str | None:
    current: Any = payload
    for part in secret_path.lstrip("/").split("/"):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    if isinstance(current, str) and current.strip():
        return current.strip()
    return None


def _resolve_file_secret(ref: dict[str, Any], openclaw_config: dict[str, Any]) -> str:
    provider_name = str(ref.get("provider") or "default")
    secret_id = str(ref.get("id") or "")
    provider = (
        openclaw_config.get("secrets", {})
        .get("providers", {})
        .get(provider_name)
    )
    if not isinstance(provider, dict) or provider.get("source") != "file":
        raise ConfigError("MISSING_SECRET_PROVIDER", f"File SecretRef provider is not configured: {provider_name}")

    raw_path = provider.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConfigError("INVALID_SECRET_PROVIDER", f"File SecretRef provider has no path: {provider_name}")

    secret_file = _expand_path(raw_path)
    if not secret_file.exists():
        raise ConfigError("MISSING_SECRET_FILE", f"Secret file does not exist: {secret_file}")

    raw = secret_file.read_text(encoding="utf-8")
    if provider.get("mode") == "singleValue":
        if secret_id != "value":
            raise ConfigError("INVALID_SECRET_ID", "singleValue file SecretRef must use id=value")
        resolved = raw.strip()
        if not resolved:
            raise ConfigError("MISSING_SECRET_VALUE", f"File SecretRef is empty: {provider_name}:{secret_id}")
        return resolved

    payload = json.loads(raw)
    resolved = _read_json_path(payload, secret_id)
    if not resolved:
        raise ConfigError("MISSING_SECRET_VALUE", f"File SecretRef is not available: {provider_name}:{secret_id}")
    return resolved


def _resolve_env_secret(ref: dict[str, Any], openclaw_config: dict[str, Any]) -> str:
    provider_name = str(ref.get("provider") or "default")
    secret_id = str(ref.get("id") or "")
    provider = (
        openclaw_config.get("secrets", {})
        .get("providers", {})
        .get(provider_name)
    )
    if isinstance(provider, dict) and provider.get("source") == "env":
        allowlist = provider.get("allowlist")
        if isinstance(allowlist, list) and allowlist and secret_id not in allowlist:
            raise ConfigError("SECRET_REF_NOT_ALLOWLISTED", f"Environment SecretRef is not allowlisted: {secret_id}")

    resolved = os.getenv(secret_id)
    if not resolved:
        raise ConfigError("MISSING_SECRET_VALUE", f"Environment SecretRef is not available: {secret_id}")
    return resolved


def resolve_secret_value(value: Any, openclaw_config: dict[str, Any] | None = None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        raise ConfigError("INVALID_SECRET_REF", "Secret value must be a string or OpenClaw SecretRef object")

    payload = openclaw_config or {}
    source = value.get("source")
    if source == "env":
        return _resolve_env_secret(value, payload)
    if source == "file":
        return _resolve_file_secret(value, payload)
    raise ConfigError("UNSUPPORTED_SECRET_REF_SOURCE", f"Unsupported SecretRef source for transcribe-service MVP: {source}")


def resolve_provider_field(
    config: dict[str, Any],
    provider: str,
    field: str,
    openclaw_config: dict[str, Any] | None = None,
) -> str | None:
    providers = config.get("providers", {})
    provider_config = providers.get(provider, {})
    return resolve_secret_value(provider_config.get(field), openclaw_config)
