import argparse
import json
from pathlib import Path
from typing import Any

from pipeline_core import load_json, utc_now, write_json


def generate_dialogue(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_json(manifest_file)
    root = Path(manifest["meeting_root"])
    raw = load_json(root / "transcript/transcript_raw.json")
    context = load_json(root / "manifest/meeting_context.json")
    primary_speakers = context.get("primary_speakers", [])
    segments = []
    lines = [f"# 對話稿：{context.get('topic', 'unknown')}", ""]
    for index, segment in enumerate(raw["segments"], start=1):
        assigned = primary_speakers[0] if len(primary_speakers) == 1 else "未知發言者"
        dialogue_id = f"dlg-{index:04d}"
        lines.append(f"## {dialogue_id} [{segment['start']}-{segment['end']}]")
        lines.append(f"**{assigned}**：{segment['text']}")
        lines.append("")
        segments.append(
            {
                "dialogue_id": dialogue_id,
                "speaker": assigned,
                "text": segment["text"],
                "start": segment["start"],
                "end": segment["end"],
                "source_segment_id": segment["segment_id"],
            }
        )
    (root / "dialogue/dialogue.md").write_text("\n".join(lines), encoding="utf-8")
    write_json(root / "dialogue/dialogue_segments.json", {"segments": segments})
    manifest["stages"]["generate_dialogue"].update(
        {
            "status": "completed",
            "input_artifacts": ["transcript/transcript_raw.json", "manifest/meeting_context.json"],
            "output_artifacts": ["dialogue/dialogue.md", "dialogue/dialogue_segments.json"],
            "completed_at": utc_now(),
        }
    )
    write_json(manifest_file, manifest)
    return {"status": "completed", "meeting_root": str(root), "manifest_path": str(manifest_file)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    args = parser.parse_args()
    print(json.dumps(generate_dialogue(args.manifest_path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
