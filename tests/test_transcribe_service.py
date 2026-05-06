from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from transcribe_service.app import app
from transcribe_service.chunking import UnsupportedAudioFormatError, validate_audio_path
from transcribe_service.config import load_plugin_config, resolve_secret_value
from transcribe_service.providers import transcribe_with_provider


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def test_validate_audio_path_rejects_missing_file():
    missing = FIXTURES / "missing.wav"
    try:
        validate_audio_path(missing)
    except FileNotFoundError as exc:
        assert "AUDIO_NOT_FOUND" in str(exc)
    else:
        raise AssertionError("missing file should fail")


def test_validate_audio_path_rejects_unsupported_extension(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("not audio")
    try:
        validate_audio_path(bad)
    except UnsupportedAudioFormatError as exc:
        assert "UNSUPPORTED_AUDIO_FORMAT" in str(exc)
    else:
        raise AssertionError("unsupported extension should fail")


def test_transcribe_mock_provider_returns_segments():
    audio = FIXTURES / "sample_meeting_audio.wav"
    client = TestClient(app)
    response = client.post(
        "/transcribe",
        json={
            "audio_path": str(audio),
            "provider": "mock",
            "language": "zh",
            "enable_chunking": True,
            "chunk_minutes": 10
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meeting_id"].endswith("sample_meeting_audio")
    assert payload["segments"][0]["segment_id"] == "seg-0001"
    assert payload["segments"][0]["speaker"] is None
    assert payload["errors"] == []


def test_transcribe_unknown_provider_returns_400():
    audio = FIXTURES / "sample_meeting_audio.wav"
    client = TestClient(app)
    response = client.post(
        "/transcribe",
        json={
            "audio_path": str(audio),
            "provider": "unknown",
            "language": "zh",
            "enable_chunking": True,
            "chunk_minutes": 10
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_PROVIDER"


def test_resolve_secret_value_supports_openclaw_env_secret_ref(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    value = resolve_secret_value(
        {
            "source": "env",
            "provider": "meeting-transcribe-cloud",
            "id": "GROQ_API_KEY",
        },
        {
            "secrets": {
                "providers": {
                    "meeting-transcribe-cloud": {
                        "source": "env",
                        "allowlist": ["GROQ_API_KEY"],
                    }
                }
            }
        },
    )
    assert value == "test-groq-key"


def test_resolve_secret_value_supports_openclaw_file_secret_ref(tmp_path):
    secret_file = tmp_path / "meeting-transcribe-cloud.json"
    secret_file.write_text('{"groq": {"apiKey": "test-groq-key"}}', encoding="utf-8")

    value = resolve_secret_value(
        {
            "source": "file",
            "provider": "meeting-transcribe-cloud",
            "id": "/groq/apiKey",
        },
        {
            "secrets": {
                "providers": {
                    "meeting-transcribe-cloud": {
                        "source": "file",
                        "path": str(secret_file),
                        "mode": "json",
                    }
                }
            }
        },
    )
    assert value == "test-groq-key"


def test_transcribe_service_reads_openclaw_plugin_config(monkeypatch, tmp_path):
    secret_file = tmp_path / "meeting-transcribe-cloud.json"
    secret_file.write_text(
        '{"groq": {"apiKey": "test-groq-key"}, "openai": {"apiKey": "test-openai-key"}}',
        encoding="utf-8",
    )
    config_path = tmp_path / "openclaw.json"
    config_path.write_text(
        f"""
{{
  "secrets": {{
    "providers": {{
      "meeting-transcribe-cloud": {{
        "source": "file",
        "path": "{secret_file}",
        "mode": "json"
      }}
    }}
  }},
  "plugins": {{
    "entries": {{
      "meeting-transcribe-cloud": {{
        "enabled": true,
        "config": {{
          "defaultProvider": "auto",
          "fallback": {{
            "order": ["groq", "openai", "local"],
            "diarizeOrder": ["openai", "local"]
          }},
          "providers": {{
            "groq": {{
              "model": "whisper-large-v3-turbo",
              "apiKey": {{
                "source": "file",
                "provider": "meeting-transcribe-cloud",
                "id": "/groq/apiKey"
              }}
            }},
            "openai": {{
              "model": "gpt-4o-mini-transcribe",
              "diarizeModel": "gpt-4o-transcribe-diarize",
              "apiKey": {{
                "source": "file",
                "provider": "meeting-transcribe-cloud",
                "id": "/openai/apiKey"
              }}
            }}
          }}
        }}
      }}
    }}
  }}
}}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_FILE", str(config_path))

    plugin_config = load_plugin_config()
    assert plugin_config["defaultProvider"] == "auto"
    assert plugin_config["fallback"]["order"] == ["groq", "openai", "local"]


def test_auto_provider_falls_back_from_groq_to_openai_mini(monkeypatch, tmp_path):
    audio = FIXTURES / "sample_meeting_audio.wav"
    secret_file = tmp_path / "meeting-transcribe-cloud.json"
    secret_file.write_text(
        '{"groq": {"apiKey": "test-groq-key"}, "openai": {"apiKey": "test-openai-key"}}',
        encoding="utf-8",
    )
    config_path = tmp_path / "openclaw.json"
    config_path.write_text(
        f"""
{{
  "secrets": {{
    "providers": {{
      "meeting-transcribe-cloud": {{
        "source": "file",
        "path": "{secret_file}",
        "mode": "json"
      }}
    }}
  }},
  "plugins": {{
    "entries": {{
      "meeting-transcribe-cloud": {{
        "enabled": true,
        "config": {{
          "defaultProvider": "auto",
          "fallback": {{
            "order": ["groq", "openai", "local"],
            "diarizeOrder": ["openai", "local"]
          }},
          "providers": {{
            "groq": {{
              "model": "whisper-large-v3-turbo",
              "apiKey": {{"source": "file", "provider": "meeting-transcribe-cloud", "id": "/groq/apiKey"}}
            }},
            "openai": {{
              "model": "gpt-4o-mini-transcribe",
              "diarizeModel": "gpt-4o-transcribe-diarize",
              "apiKey": {{"source": "file", "provider": "meeting-transcribe-cloud", "id": "/openai/apiKey"}}
            }}
          }}
        }}
      }}
    }}
  }}
}}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_FILE", str(config_path))

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode("utf-8", errors="ignore")
        if "api.groq.com" in str(request.url):
            assert "whisper-large-v3-turbo" in body
            return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})
        assert "api.openai.com" in str(request.url)
        assert "gpt-4o-mini-transcribe" in body
        return httpx.Response(200, json={"text": "openai fallback transcript", "usage": {"seconds": 12.0}})

    result = transcribe_with_provider(
        "auto",
        audio,
        "zh",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini-transcribe"
    assert result.segments[0].text == "openai fallback transcript"
    assert result.segments[0].end == 12.0
    assert result.fallback_attempts[0].code == "STT_API_FAILED"


def test_diarize_auto_uses_openai_diarize_without_groq(monkeypatch, tmp_path):
    audio = FIXTURES / "sample_meeting_audio.wav"
    secret_file = tmp_path / "meeting-transcribe-cloud.json"
    secret_file.write_text('{"openai": {"apiKey": "test-openai-key"}}', encoding="utf-8")
    config_path = tmp_path / "openclaw.json"
    config_path.write_text(
        f"""
{{
  "secrets": {{
    "providers": {{
      "meeting-transcribe-cloud": {{
        "source": "file",
        "path": "{secret_file}",
        "mode": "json"
      }}
    }}
  }},
  "plugins": {{
    "entries": {{
      "meeting-transcribe-cloud": {{
        "enabled": true,
        "config": {{
          "defaultProvider": "auto",
          "fallback": {{
            "order": ["groq", "openai", "local"],
            "diarizeOrder": ["openai", "local"]
          }},
          "providers": {{
            "openai": {{
              "model": "gpt-4o-mini-transcribe",
              "diarizeModel": "gpt-4o-transcribe-diarize",
              "apiKey": {{"source": "file", "provider": "meeting-transcribe-cloud", "id": "/openai/apiKey"}}
            }}
          }}
        }}
      }}
    }}
  }}
}}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCLAW_CONFIG_FILE", str(config_path))

    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.openai.com" in str(request.url)
        body = request.content.decode("utf-8", errors="ignore")
        assert "gpt-4o-transcribe-diarize" in body
        assert "diarized_json" in body
        return httpx.Response(
            200,
            json={
                "text": "speaker text",
                "segments": [{"start": 0.0, "end": 2.0, "text": "speaker text", "speaker": "A"}],
            },
        )

    result = transcribe_with_provider(
        "auto",
        audio,
        "zh",
        diarize=True,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result.provider == "openai"
    assert result.model == "gpt-4o-transcribe-diarize"
    assert result.diarize is True
    assert result.segments[0].speaker == "A"
