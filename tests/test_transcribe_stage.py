import json
from pathlib import Path

import httpx

from locate_audio_file import locate_audio_file
from transcribe_audio import transcribe_audio


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def test_transcribe_audio_writes_raw_json_and_markdown(tmp_path):
    located = locate_audio_file(str(FIXTURES / "sample_meeting_audio.wav"), tmp_path)
    manifest_path = located["manifest_path"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "meeting_id": "sample-meeting-audio",
                "segments": [
                    {
                        "segment_id": "seg-0001",
                        "start": 0.0,
                        "end": 8.0,
                        "text": "原始逐字稿內容，不要修飾。",
                        "speaker": None,
                        "source_file": "chunk-0001.wav"
                    }
                ],
                "errors": []
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = transcribe_audio(manifest_path, "http://testserver", provider="mock", client=client)
    assert result["status"] == "completed"

    meeting_root = Path(result["meeting_root"])
    raw = json.loads((meeting_root / "transcript/transcript_raw.json").read_text())
    md = (meeting_root / "transcript/transcript.md").read_text()
    assert raw["segments"][0]["text"] == "原始逐字稿內容，不要修飾。"
    assert "[seg-0001 | 0.0-8.0]" in md


def test_transcribe_audio_marks_service_failure(tmp_path):
    located = locate_audio_file(str(FIXTURES / "sample_meeting_audio.wav"), tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": {"code": "MISSING_API_KEY", "message": "missing"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = transcribe_audio(located["manifest_path"], "http://testserver", provider="groq", client=client)
    assert result["status"] == "failed"
    assert result["errors"][0]["code"] == "MISSING_API_KEY"
