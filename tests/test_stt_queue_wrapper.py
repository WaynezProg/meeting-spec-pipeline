from pathlib import Path

import httpx

from stt_queue_transcribe import transcribe_via_stt_queue


def test_stt_queue_wrapper_submits_and_polls_until_done(tmp_path: Path):
    audio = tmp_path / "meeting.wav"
    audio.write_bytes(b"fake-audio")
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "POST" and request.url.path == "/stt/jobs":
            body = request.content.decode("utf-8", errors="ignore")
            assert "language" in body
            assert "zh" in body
            return httpx.Response(200, json={"id": "stt_test_001", "status": "queued"})
        if request.method == "GET" and request.url.path == "/stt/jobs/stt_test_001":
            if calls.count("GET /stt/jobs/stt_test_001") == 1:
                return httpx.Response(200, json={"id": "stt_test_001", "status": "processing"})
            return httpx.Response(
                200,
                json={
                    "id": "stt_test_001",
                    "status": "done",
                    "text": "逐字稿完成",
                    "model": "large-v3-turbo-q5_0",
                    "duration_sec": 12.5,
                },
            )
        return httpx.Response(404, json={"detail": "not found"})

    result = transcribe_via_stt_queue(
        audio,
        language="zh",
        base_url="http://stt.test",
        poll_interval_sec=0,
        timeout_sec=5,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert result == {
        "text": "逐字稿完成",
        "provider": "local-stt-queue",
        "model": "large-v3-turbo-q5_0",
        "duration": 12.5,
        "job_id": "stt_test_001",
    }

