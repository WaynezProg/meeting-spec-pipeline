import json
from pathlib import Path

from generate_requirement_spec import SPEC_SECTIONS
from validate_outputs import validate_requirement_spec_sections


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/meeting-spec-pipeline"


ANTI_HALLUCINATION_RULES = [
    "不確定就寫「待確認」",
    "資訊不足就寫「待補充」",
    "不要創造沒有來源的事實",
    "不要自行新增未被提及的系統、欄位、API、權限、流程",
    "推論，待確認",
]


def test_skill_entrypoint_exists_and_mentions_stage_pause():
    text = (SKILL / "SKILL.md").read_text()
    assert "stage-based workflow" in text
    assert "每個 stage 完成後停止" in text
    assert "not a one-click recording-to-PRD black box" in text
    assert "Do not create or call a `run_all`" in text
    assert "人工補充只能插在 stage boundary" in text


def test_skill_metadata_forbids_run_all_mode():
    metadata = json.loads((SKILL / "skill.json").read_text())
    assert metadata["execution_model"]["mode"] == "stage_gated"
    assert metadata["execution_model"]["allow_run_all"] is False
    assert metadata["execution_model"]["human_input_between_stages"] is True
    assert metadata["execution_model"]["resume_source"] == "meeting_manifest.json"


def test_prompt_forbids_one_click_pipeline():
    text = (SKILL / "prompt.md").read_text()
    assert "Never run the whole pipeline automatically" in text
    assert "never use a one-click audio-to-PRD wrapper" in text
    assert "Allow human context or reference files only at stage boundaries" in text


def test_no_one_click_stage_script_exists():
    scripts = [path.name for path in (SKILL / "scripts").glob("*.py")]
    forbidden_names = {"run_all.py", "one_click.py", "audio_to_prd.py", "recording_to_prd.py"}
    assert forbidden_names.isdisjoint(scripts)


def test_prompts_include_anti_hallucination_rules():
    for prompt_name in ["dialogue.md", "meeting_minutes.md", "requirement_spec.md"]:
        text = (SKILL / "prompts" / prompt_name).read_text()
        for rule in ANTI_HALLUCINATION_RULES:
            assert rule in text


def test_requirement_spec_section_validator():
    markdown = "\n".join(["# 需求規格書", ""] + [f"## {section}\n內容" for section in SPEC_SECTIONS])
    assert validate_requirement_spec_sections(markdown) == []
    missing = markdown.replace("## 13. 待確認事項\n內容", "")
    assert "13. 待確認事項" in validate_requirement_spec_sections(missing)
