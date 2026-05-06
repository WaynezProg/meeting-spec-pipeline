import argparse
import json
from pathlib import Path
from typing import Any

import httpx

from pipeline_core import load_json, utc_now, write_json


def _write_transcript_markdown(path: Path, segments: list[dict[str, Any]]) -> None:
    lines = ["# Transcript Raw", ""]
    for segment in segments:
        lines.append(f"[{segment['segment_id']} | {segment['start']}-{segment['end']}]")
        lines.append(segment["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def transcribe_audio(
    manifest_path: str | Path,
    service_url: str,
    provider: str = "auto",
    language: str = "zh",
    enable_chunking: bool = True,
    chunk_minutes: int = 10,
    diarize: bool = False,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_json(manifest_file)
    meeting_root = Path(manifest["meeting_root"])
    audio_path = manifest["audio"]["copied_path"]
    stage = manifest["stages"]["transcribe_audio"]
    stage["status"] = "running"
    stage["started_at"] = utc_now()
    write_json(manifest_file, manifest)

    owns_client = client is None
    http = client or httpx.Client(timeout=120)
    try:
        response = http.post(
            f"{service_url.rstrip('/')}/transcribe",
            json={
                "audio_path": audio_path,
                "provider": provider,
                "language": language,
                "enable_chunking": enable_chunking,
                "chunk_minutes": chunk_minutes,
                "diarize": diarize,
            },
        )
        if response.status_code >= 400:
            detail = response.json().get("detail", {})
            stage["status"] = "failed"
            stage["errors"] = [{"code": detail.get("code", "STT_API_FAILED"), "message": detail.get("message", response.text)}]
            stage["completed_at"] = utc_now()
            write_json(manifest_file, manifest)
            return {"status": "failed", "errors": stage["errors"], "meeting_root": str(meeting_root)}

        payload = response.json()
        raw_path = meeting_root / "transcript/transcript_raw.json"
        md_path = meeting_root / "transcript/transcript.md"
        write_json(raw_path, payload)
        _write_transcript_markdown(md_path, payload["segments"])
        status = "partial" if payload.get("errors") else "completed"
        stage.update(
            {
                "status": status,
                "input_artifacts": ["manifest/meeting_manifest.json", manifest["audio"]["copied_path"]],
                "output_artifacts": ["transcript/transcript_raw.json", "transcript/transcript.md"],
                "completed_at": utc_now(),
                "errors": payload.get("errors", []),
                "provider": payload.get("provider", provider),
                "model": payload.get("model"),
                "fallback_attempts": payload.get("fallback_attempts", []),
                "diarize": payload.get("diarize", diarize),
            }
        )
        write_json(manifest_file, manifest)
        return {"status": status, "meeting_root": str(meeting_root), "manifest_path": str(manifest_file)}
    finally:
        if owns_client:
            http.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--chunk-minutes", type=int, default=10)
    parser.add_argument("--diarize", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            transcribe_audio(
                args.manifest_path,
                args.service_url,
                args.provider,
                args.language,
                True,
                args.chunk_minutes,
                args.diarize,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
