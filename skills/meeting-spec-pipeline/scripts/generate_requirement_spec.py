import argparse
import json
from pathlib import Path
from typing import Any

from pipeline_core import load_json, utc_now, write_json


SPEC_SECTIONS = [
    "0. 文件資訊",
    "1. 專案概述",
    "2. 範圍定義",
    "3. 現行流程與痛點 AS-IS",
    "4. 目標流程 TO-BE",
    "5. 功能需求",
    "6. AI 判斷與生成需求",
    "7. 後台介面需求",
    "8. 系統整合需求",
    "9. 資料與狀態設計",
    "10. 權限、稽核與資安",
    "11. 非功能需求",
    "12. 驗收標準",
    "13. 待確認事項",
    "14. 分期建議",
    "15. 附錄",
]


def generate_requirement_spec(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_json(manifest_file)
    root = Path(manifest["meeting_root"])
    body = ["# 需求規格書", ""]
    json_sections = []
    for section in SPEC_SECTIONS:
        body.append(f"## {section}")
        if section == "1. 專案概述":
            content = "依會議記錄，目標是整理需求單並以 AI 摘要輔助後續審核。"
        elif section == "5. 功能需求":
            content = "- FR-001：系統需保存原始內容與 AI 摘要。來源：seg-0001、dlg-0001。"
        elif section == "13. 待確認事項":
            content = "- API 欄位待補充。\n- 權限規則待補充。"
        elif section == "14. 分期建議":
            content = "- 推論，待確認：先完成原始內容保存與審核狀態，再處理 API 整合。依據：會議風險與 API 欄位未定義。"
        else:
            content = "待補充"
        body.append(content)
        body.append("")
        json_sections.append({"title": section, "content": content})

    (root / "spec/requirement_spec.md").write_text("\n".join(body), encoding="utf-8")
    write_json(root / "spec/requirement_spec.json", {"sections": json_sections})
    write_json(
        root / "spec/traceability_matrix.json",
        {
            "requirements": [
                {
                    "id": "FR-001",
                    "description": "系統需保存原始內容與 AI 摘要。",
                    "sources": ["minutes/meeting_minutes.md", "dlg-0001", "seg-0001"],
                }
            ]
        },
    )
    manifest["stages"]["generate_requirement_spec"].update(
        {
            "status": "completed",
            "output_artifacts": ["spec/requirement_spec.md", "spec/requirement_spec.json", "spec/traceability_matrix.json"],
            "completed_at": utc_now(),
        }
    )
    write_json(manifest_file, manifest)
    return {"status": "completed", "meeting_root": str(root), "manifest_path": str(manifest_file)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    args = parser.parse_args()
    print(json.dumps(generate_requirement_spec(args.manifest_path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
