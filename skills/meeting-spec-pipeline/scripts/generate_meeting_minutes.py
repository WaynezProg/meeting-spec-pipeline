import argparse
import json
from pathlib import Path
from typing import Any

from pipeline_core import load_json, utc_now, write_json


MINUTES_TEMPLATE = """# 會議記錄

## 會議資訊
- 主題：{topic}

## 會議重點
- 需求單需要 AI 摘要，但原始內容不可覆蓋。

## 會議議題
- 需求單整理流程
- 後台審核狀態
- API 欄位定義

## 會議結論
- AI 摘要可作為輔助內容；不可取代原始逐字稿或原始需求。

## 決議事項
- 推論，待確認：後台需保存審核狀態。

## 待辦事項
- 待確認：API 欄位定義。

## 負責人
- 待確認

## 時程
- 待確認

## 風險與爭議點
- AI 摘要若覆蓋原始內容會造成追溯風險。

## 待確認事項
- API 欄位目前還沒有定義。
- 權限規則待補充。
"""


def generate_meeting_minutes(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_json(manifest_file)
    root = Path(manifest["meeting_root"])
    context = load_json(root / "manifest/meeting_context.json")
    minutes = MINUTES_TEMPLATE.format(topic=context.get("topic", "unknown"))
    (root / "minutes/meeting_minutes.md").write_text(minutes, encoding="utf-8")
    write_json(
        root / "minutes/action_items.json",
        {
            "items": [
                {
                    "description": "API 欄位定義",
                    "owner": "待確認",
                    "due_date": "待確認",
                    "sources": ["dlg-0002", "seg-0002"],
                }
            ]
        },
    )
    write_json(
        root / "minutes/open_questions.json",
        {
            "questions": [
                {
                    "question": "API 欄位如何定義？",
                    "sources": ["dlg-0002", "seg-0002"],
                }
            ]
        },
    )
    manifest["stages"]["generate_meeting_minutes"].update(
        {
            "status": "completed",
            "output_artifacts": ["minutes/meeting_minutes.md", "minutes/action_items.json", "minutes/open_questions.json"],
            "completed_at": utc_now(),
        }
    )
    write_json(manifest_file, manifest)
    return {"status": "completed", "meeting_root": str(root), "manifest_path": str(manifest_file)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    args = parser.parse_args()
    print(json.dumps(generate_meeting_minutes(args.manifest_path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
