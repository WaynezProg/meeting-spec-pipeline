import argparse
import json
from pathlib import Path
from typing import Any

from pipeline_core import SUPPORTED_AUDIO_SUFFIXES, create_manifest, find_audio_candidates


def locate_audio_file(input_path: str, workdir: str | Path = "workdir") -> dict[str, Any]:
    path = Path(input_path).expanduser().resolve()
    root = Path(workdir).expanduser().resolve()

    if not path.exists():
        return {"status": "failed", "errors": [{"code": "AUDIO_NOT_FOUND", "message": str(path)}]}

    candidates = find_audio_candidates(path)
    if not candidates and path.is_file():
        return {
            "status": "failed",
            "errors": [{"code": "UNSUPPORTED_AUDIO_FORMAT", "message": path.suffix.lower()}],
            "supported_formats": sorted(SUPPORTED_AUDIO_SUFFIXES),
        }
    if len(candidates) > 1:
        return {"status": "needs_input", "candidates": [str(candidate) for candidate in candidates]}
    if not candidates:
        return {"status": "failed", "errors": [{"code": "AUDIO_NOT_FOUND", "message": str(path)}]}

    manifest = create_manifest(candidates[0], root)
    return {
        "status": "completed",
        "meeting_id": manifest["meeting_id"],
        "manifest_path": str(Path(manifest["meeting_root"]) / "manifest/meeting_manifest.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("--workdir", default="workdir")
    args = parser.parse_args()
    print(json.dumps(locate_audio_file(args.input_path, args.workdir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
