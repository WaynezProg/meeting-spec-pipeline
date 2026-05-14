import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx


def _headers() -> dict[str, str]:
    token = os.getenv("STT_API_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def transcribe_via_stt_queue(
    audio_path: str | Path,
    language: str = "zh",
    base_url: str = "http://127.0.0.1:8787",
    poll_interval_sec: float = 2.0,
    timeout_sec: float = 3600.0,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    audio = Path(audio_path).expanduser().resolve()
    if not audio.exists():
        raise FileNotFoundError(f"AUDIO_NOT_FOUND: {audio}")

    owns_client = client is None
    http = client or httpx.Client(timeout=120)
    try:
        with audio.open("rb") as handle:
            submit = http.post(
                f"{base_url.rstrip('/')}/stt/jobs",
                headers=_headers(),
                data={"source": "meeting-spec-pipeline", "language": language},
                files={"audio": (audio.name, handle, "application/octet-stream")},
            )
        submit.raise_for_status()
        job_id = submit.json()["id"]

        deadline = time.monotonic() + timeout_sec
        last_payload: dict[str, Any] = {}
        while time.monotonic() < deadline:
            poll = http.get(f"{base_url.rstrip('/')}/stt/jobs/{job_id}", headers=_headers())
            poll.raise_for_status()
            payload = poll.json()
            last_payload = payload if isinstance(payload, dict) else {}
            status = last_payload.get("status")
            if status == "done":
                text = str(last_payload.get("text") or "").strip()
                if not text:
                    raise RuntimeError(f"EMPTY_TRANSCRIPT: {job_id}")
                return {
                    "text": text,
                    "provider": "local-stt-queue",
                    "model": last_payload.get("model"),
                    "duration": last_payload.get("duration_sec"),
                    "job_id": job_id,
                }
            if status == "failed":
                code = last_payload.get("error_code") or "STT_QUEUE_FAILED"
                message = last_payload.get("error_message") or f"STT queue job failed: {job_id}"
                raise RuntimeError(f"{code}: {message}")
            time.sleep(poll_interval_sec)
        raise TimeoutError(f"STT_QUEUE_TIMEOUT: {job_id}: {last_payload}")
    finally:
        if owns_client:
            http.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--base-url", default=os.getenv("STT_BASE_URL", "http://127.0.0.1:8787"))
    parser.add_argument("--poll-interval-sec", type=float, default=float(os.getenv("STT_POLL_INTERVAL_SEC", "2")))
    parser.add_argument("--timeout-sec", type=float, default=float(os.getenv("STT_TIMEOUT_SEC", "3600")))
    args = parser.parse_args()
    try:
        result = transcribe_via_stt_queue(
            args.audio_path,
            language=args.language,
            base_url=args.base_url,
            poll_interval_sec=args.poll_interval_sec,
            timeout_sec=args.timeout_sec,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
