import argparse
import json
from pathlib import Path
from typing import Any

from pipeline_core import load_json, utc_now, write_json


def save_meeting_context(manifest_path: str | Path, context_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_json(manifest_file)
    context = load_json(context_path)
    context.setdefault("topic", "unknown")
    context.setdefault("participants", [])
    context.setdefault("primary_speakers", [])
    context.setdefault("terms", [])
    target = Path(manifest["meeting_root"]) / "manifest/meeting_context.json"
    write_json(target, context)
    manifest["stages"]["ask_meeting_context"].update(
        {
            "status": "completed",
            "input_artifacts": [str(context_path)],
            "output_artifacts": ["manifest/meeting_context.json"],
            "completed_at": utc_now(),
        }
    )
    write_json(manifest_file, manifest)
    return {"status": "completed", "meeting_root": manifest["meeting_root"], "manifest_path": str(manifest_file)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    parser.add_argument("context_path")
    args = parser.parse_args()
    print(json.dumps(save_meeting_context(args.manifest_path, args.context_path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
