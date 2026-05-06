import argparse
import json
from pathlib import Path
from typing import Any

from pipeline_core import load_json, utc_now, write_json


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".json", ".csv"}


def collect_references(manifest_path: str | Path, reference_type: str, paths: list[str]) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_json(manifest_file)
    root = Path(manifest["meeting_root"])
    entries = []
    summary_lines = [f"# {reference_type} reference summary", ""]
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists() or path.suffix.lower() not in SUPPORTED_TEXT_SUFFIXES:
            entries.append({"path": str(path), "status": "unreadable"})
            summary_lines.append(f"- 無法讀取：{path}")
            continue
        text = path.read_text(encoding="utf-8")
        entries.append({"path": str(path), "status": "readable", "sections_impacted": []})
        summary_lines.append(f"## {path.name}")
        summary_lines.append(text.strip())
        summary_lines.append("")

    if reference_type == "meeting":
        manifest_name = "meeting_references_manifest.json"
        summary_name = "meeting_reference_summary.md"
        stage_name = "ask_meeting_reference"
    elif reference_type == "spec":
        manifest_name = "spec_references_manifest.json"
        summary_name = "spec_reference_summary.md"
        stage_name = "ask_spec_reference"
    else:
        raise ValueError("reference_type must be meeting or spec")

    write_json(root / f"references/{manifest_name}", {"references": entries})
    (root / f"references/{summary_name}").write_text("\n".join(summary_lines), encoding="utf-8")
    manifest["stages"][stage_name].update(
        {
            "status": "completed",
            "input_artifacts": paths,
            "output_artifacts": [f"references/{manifest_name}", f"references/{summary_name}"],
            "completed_at": utc_now(),
        }
    )
    write_json(manifest_file, manifest)
    return {"status": "completed", "meeting_root": str(root), "manifest_path": str(manifest_file)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    parser.add_argument("reference_type", choices=["meeting", "spec"])
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    print(json.dumps(collect_references(args.manifest_path, args.reference_type, args.paths), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
