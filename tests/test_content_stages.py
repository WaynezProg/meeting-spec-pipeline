import json
from pathlib import Path

import httpx

from collect_references import collect_references
from generate_dialogue import generate_dialogue
from generate_meeting_minutes import generate_meeting_minutes
from generate_requirement_spec import generate_requirement_spec
from locate_audio_file import locate_audio_file
from save_meeting_context import save_meeting_context
from transcribe_audio import transcribe_audio


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def prepare_transcribed_meeting(tmp_path: Path) -> Path:
    located = locate_audio_file(str(FIXTURES / "sample_meeting_audio.wav"), tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "meeting_id": "sample-meeting-audio",
                "segments": [
                    {
                        "segment_id": "seg-0001",
                        "start": 0.0,
                        "end": 8.0,
                        "text": "我們今天要討論需求單如何用 AI 摘要，原始內容不能被覆蓋。",
                        "speaker": None,
                        "source_file": "chunk-0001.wav"
                    },
                    {
                        "segment_id": "seg-0002",
                        "start": 8.0,
                        "end": 17.5,
                        "text": "後台需要有審核狀態，API 欄位目前還沒有定義。",
                        "speaker": None,
                        "source_file": "chunk-0001.wav"
                    }
                ],
                "errors": []
            },
        )

    transcribe_audio(
        located["manifest_path"],
        "http://testserver",
        provider="mock",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return Path(located["manifest_path"])


def test_content_stages_generate_required_artifacts(tmp_path):
    manifest_path = prepare_transcribed_meeting(tmp_path)
    context_result = save_meeting_context(manifest_path, FIXTURES / "meeting_context.json")
    assert context_result["status"] == "completed"

    dialogue_result = generate_dialogue(manifest_path)
    assert dialogue_result["status"] == "completed"
    meeting_root = Path(dialogue_result["meeting_root"])
    assert "未知發言者" in (meeting_root / "dialogue/dialogue.md").read_text()

    meeting_ref = collect_references(manifest_path, "meeting", [str(FIXTURES / "meeting_reference.txt")])
    assert meeting_ref["status"] == "completed"
    assert "會議快記" in (meeting_root / "references/meeting_reference_summary.md").read_text()

    minutes_result = generate_meeting_minutes(manifest_path)
    assert minutes_result["status"] == "completed"
    assert "## 待確認事項" in (meeting_root / "minutes/meeting_minutes.md").read_text()
    questions_md = (meeting_root / "minutes/questions.md").read_text()
    assert "### Q-001: API 欄位定義" in questions_md
    assert "- 狀態：待確認" in questions_md
    assert "- 目前依據：dlg-0002、seg-0002" in questions_md

    spec_ref = collect_references(manifest_path, "spec", [str(FIXTURES / "spec_reference.txt")])
    assert spec_ref["status"] == "completed"

    spec_result = generate_requirement_spec(manifest_path)
    assert spec_result["status"] == "completed"
    spec_md = (meeting_root / "spec/requirement_spec.md").read_text()
    assert "## 13. 待確認事項" in spec_md
    trace = json.loads((meeting_root / "spec/traceability_matrix.json").read_text())
    assert trace["requirements"][0]["sources"]
