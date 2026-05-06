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
from validate_outputs import validate_requirement_spec_sections


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def test_end_to_end_mvp_generates_traceable_spec(tmp_path):
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
    save_meeting_context(located["manifest_path"], FIXTURES / "meeting_context.json")
    generate_dialogue(located["manifest_path"])
    collect_references(located["manifest_path"], "meeting", [str(FIXTURES / "meeting_reference.txt")])
    generate_meeting_minutes(located["manifest_path"])
    collect_references(located["manifest_path"], "spec", [str(FIXTURES / "spec_reference.txt")])
    final = generate_requirement_spec(located["manifest_path"])

    root = Path(final["meeting_root"])
    required = [
        "manifest/meeting_manifest.json",
        "transcript/transcript_raw.json",
        "transcript/transcript.md",
        "manifest/meeting_context.json",
        "dialogue/dialogue.md",
        "minutes/meeting_minutes.md",
        "minutes/questions.md",
        "spec/requirement_spec.md",
        "spec/traceability_matrix.json",
    ]
    for relative in required:
        assert (root / relative).exists()

    spec_md = (root / "spec/requirement_spec.md").read_text()
    assert validate_requirement_spec_sections(spec_md) == []
    trace = json.loads((root / "spec/traceability_matrix.json").read_text())
    assert trace["requirements"][0]["sources"] == ["minutes/meeting_minutes.md", "dlg-0001", "seg-0001"]


def test_readme_is_agent_handoff_document():
    readme = (ROOT / "README.md").read_text()
    assert "OpenClaw Agent Handoff" in readme
    assert "Agent Execution Contract" in readme
    assert "Do Not" in readme
    assert "Stage Gate Protocol" in readme
    assert "Fresh Clone Install" in readme
    assert "git clone https://github.com/WaynezProg/meeting-spec-pipeline.git" in readme
    assert "cd meeting-spec-pipeline" in readme
    assert "python3 scripts/install_openclaw.py" in readme
    assert "openclaw plugins inspect meeting-transcribe-cloud --json" in readme
    assert "secrets.providers.meeting-transcribe-cloud" in readme
    assert "plugins.entries.meeting-transcribe-cloud.config" in readme
    assert "source\": \"file\"" in readme
    assert "openclaw config validate --json" in readme
    assert "export GROQ_API_KEY" not in readme
    assert "Stop after the stage completes" in readme
    assert "Report these artifact paths" in readme
    assert "Plugin 是 cloud/config/runtime surface" in readme
    assert "Skill 是 stage workflow" in readme
    assert "transcribe-service" in readme
    assert "每個 stage 可暫停" in readme
    assert "這不是「一鍵錄音變 PRD」黑盒" in readme
    assert "不要一路從錄音跑到需求規格書" in readme
    assert "人工補充插入點固定在 stage boundary" in readme
    assert "provider=auto" in readme
    assert "Groq `whisper-large-v3-turbo` 優先" in readme
    assert "OpenAI `gpt-4o-mini-transcribe`" in readme
    assert "不要 clone 第三方 Groq Whisper repo" in readme
    assert "只有需要講者分離時才加" in readme
    assert "templates/meeting-context.md" in readme
    assert "minutes/questions.md" in readme
