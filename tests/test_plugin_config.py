import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/meeting-transcribe-cloud"


def test_plugin_manifest_has_required_identity():
    manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
    assert manifest["name"] == "meeting-transcribe-cloud"
    assert manifest["version"] == "0.1.0"
    assert manifest["interface"]["displayName"] == "Meeting Transcribe Cloud"


def test_provider_schema_defines_supported_providers():
    schema = json.loads((PLUGIN / "config/provider.schema.json").read_text())
    provider_enum = schema["properties"]["default_provider"]["enum"]
    assert provider_enum == ["groq", "openai", "local", "mock"]
    assert "api_keys" in schema["properties"]
    assert "local" in schema["properties"]


def test_example_config_contains_no_real_secrets():
    example = json.loads((PLUGIN / "config/provider.example.json").read_text())
    assert example["default_provider"] == "groq"
    assert example["api_keys"]["groq"] == "env:GROQ_API_KEY"
    assert example["api_keys"]["openai"] == "env:OPENAI_API_KEY"
