import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/meeting-transcribe-cloud"
sys.path.insert(0, str(ROOT / "scripts"))
from install_openclaw import next_backup_path, patch_plugin_config  # noqa: E402


def test_plugin_manifest_has_required_identity():
    manifest = json.loads((PLUGIN / "openclaw.plugin.json").read_text())
    assert manifest["id"] == "meeting-transcribe-cloud"
    assert manifest["name"] == "Meeting Transcribe Cloud"
    assert manifest["version"] == "0.1.0"
    assert manifest["entry"] == "index.js"
    assert "configSchema" in manifest


def test_provider_schema_defines_supported_providers():
    schema = json.loads((PLUGIN / "openclaw.plugin.json").read_text())["configSchema"]
    provider_enum = schema["properties"]["defaultProvider"]["enum"]
    assert provider_enum == ["groq", "openai", "local", "mock"]
    assert "providers" in schema["properties"]
    secret_ref = schema["$defs"]["secretRef"]
    assert secret_ref["properties"]["source"]["enum"] == ["env", "file", "exec"]
    assert schema["properties"]["providers"]["properties"]["groq"]["properties"]["apiKey"]["oneOf"][1]["$ref"] == "#/$defs/secretRef"


def test_example_config_contains_no_real_secrets():
    example = json.loads((PLUGIN / "config/openclaw-entry.example.json").read_text())
    config = example["config"]
    assert example["enabled"] is True
    assert config["defaultProvider"] == "groq"
    assert config["providers"]["groq"]["apiKey"] == {
        "source": "file",
        "provider": "meeting-transcribe-cloud",
        "id": "/groq/apiKey",
    }
    assert config["providers"]["openai"]["apiKey"] == {
        "source": "file",
        "provider": "meeting-transcribe-cloud",
        "id": "/openai/apiKey",
    }


def test_secret_provider_example_uses_openclaw_file_provider():
    provider = json.loads((PLUGIN / "config/openclaw-secrets-provider.example.json").read_text())
    assert provider == {
        "source": "file",
        "path": "~/.openclaw/secrets/meeting-transcribe-cloud.json",
        "mode": "json",
    }


def test_secret_file_example_contains_only_placeholders():
    secrets = json.loads((PLUGIN / "config/meeting-transcribe-cloud.secrets.example.json").read_text())
    assert secrets["groq"]["apiKey"] == "replace-with-groq-api-key"
    assert secrets["openai"]["apiKey"] == "replace-with-openai-api-key"
    assert secrets["local"]["command"] == "replace-with-local-whisper-command"


def test_install_helper_appends_plugin_without_overwriting_existing_config(tmp_path):
    existing = {
        "plugins": {
            "load": {"paths": ["/existing/plugin"]},
            "allow": ["existing-plugin"],
            "entries": {"existing-plugin": {"enabled": True}},
        }
    }
    patched = patch_plugin_config(existing, tmp_path / "plugins" / "meeting-transcribe-cloud")

    assert patched["plugins"]["load"]["paths"] == [
        "/existing/plugin",
        str(tmp_path / "plugins" / "meeting-transcribe-cloud"),
    ]
    assert patched["plugins"]["allow"] == ["existing-plugin", "meeting-transcribe-cloud"]
    assert patched["plugins"]["entries"]["existing-plugin"]["enabled"] is True
    assert patched["plugins"]["entries"]["meeting-transcribe-cloud"]["enabled"] is True
    assert patched["plugins"]["entries"]["meeting-transcribe-cloud"]["config"] == {
        "defaultProvider": "mock",
        "providers": {"mock": {}},
    }


def test_install_helper_preserves_existing_plugin_config(tmp_path):
    existing_config = {
        "defaultProvider": "groq",
        "providers": {
            "groq": {
                "apiKey": {
                    "source": "file",
                    "provider": "meeting-transcribe-cloud",
                    "id": "/groq/apiKey",
                }
            }
        },
    }
    existing = {
        "plugins": {
            "entries": {
                "meeting-transcribe-cloud": {
                    "enabled": False,
                    "config": existing_config,
                }
            }
        }
    }
    patched = patch_plugin_config(existing, tmp_path / "plugins" / "meeting-transcribe-cloud")

    assert patched["plugins"]["entries"]["meeting-transcribe-cloud"]["enabled"] is True
    assert patched["plugins"]["entries"]["meeting-transcribe-cloud"]["config"] == existing_config


def test_install_helper_does_not_overwrite_existing_backup(tmp_path):
    config_path = tmp_path / "openclaw.json"
    first_backup = tmp_path / "openclaw.json.meeting-spec-pipeline.bak"
    first_backup.write_text("existing backup", encoding="utf-8")

    assert next_backup_path(config_path) == tmp_path / "openclaw.json.meeting-spec-pipeline.bak.1"
