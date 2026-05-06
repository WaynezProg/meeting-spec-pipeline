from pathlib import Path

from fastapi.testclient import TestClient

from transcribe_service.app import app
from transcribe_service.chunking import UnsupportedAudioFormatError, validate_audio_path


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
