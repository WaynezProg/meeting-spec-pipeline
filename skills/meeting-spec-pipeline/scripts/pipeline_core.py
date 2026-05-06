import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4"}
STAGE_NAMES = [
    "locate_audio_file",
    "transcribe_audio",
    "ask_meeting_context",
    "generate_dialogue",
    "ask_meeting_reference",
    "generate_meeting_minutes",
    "ask_spec_reference",
    "generate_requirement_spec",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_stem(path: Path) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", path.stem).strip("_").lower()
    return safe or "meeting"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_workdir_tree(meeting_root: Path) -> None:
    for relative in [
        "source/chunks",
        "transcript",
        "dialogue",
        "references",
        "minutes",
        "spec",
        "manifest",
    ]:
        (meeting_root / relative).mkdir(parents=True, exist_ok=True)


def empty_stages() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "status": "not_started",
            "input_artifacts": [],
            "output_artifacts": [],
            "started_at": None,
            "completed_at": None,
            "errors": [],
        }
        for name in STAGE_NAMES
    }


def create_manifest(audio_path: Path, workdir: Path) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    meeting_id = f"{timestamp}-{safe_stem(audio_path)}"
    meeting_root = workdir / meeting_id
    ensure_workdir_tree(meeting_root)
    final_audio = meeting_root / "source" / f"original_audio{audio_path.suffix.lower()}"
    shutil.copy2(audio_path, final_audio)
    stat = audio_path.stat()
    manifest = {
        "meeting_id": meeting_id,
        "meeting_root": str(meeting_root),
        "created_at": utc_now(),
        "audio": {
            "original_path": str(audio_path),
            "copied_path": str(final_audio),
            "suffix": audio_path.suffix.lower(),
            "size_bytes": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "sha256": sha256_file(audio_path),
        },
        "stages": empty_stages(),
    }
    manifest["stages"]["locate_audio_file"].update(
        {
            "status": "completed",
            "output_artifacts": ["manifest/meeting_manifest.json"],
            "started_at": manifest["created_at"],
            "completed_at": utc_now(),
        }
    )
    write_json(meeting_root / "manifest/meeting_manifest.json", manifest)
    return manifest


def find_audio_candidates(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES:
        return [path]
    if path.is_dir():
        return sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES)
    return []
