from pathlib import Path

from locate_audio_file import locate_audio_file
from pipeline_core import load_json


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def test_locate_audio_creates_manifest_and_workdir(tmp_path):
    result = locate_audio_file(str(FIXTURES / "sample_meeting_audio.wav"), tmp_path)
    manifest_path = Path(result["manifest_path"])
    assert manifest_path.exists()

    manifest = load_json(manifest_path)
    assert manifest["meeting_id"].endswith("sample_meeting_audio")
    assert manifest["stages"]["locate_audio_file"]["status"] == "completed"
    assert manifest["audio"]["original_path"].endswith("sample_meeting_audio.wav")
    assert Path(manifest["audio"]["copied_path"]).exists()


def test_locate_audio_rejects_missing_file(tmp_path):
    result = locate_audio_file(str(FIXTURES / "missing.wav"), tmp_path)
    assert result["status"] == "failed"
    assert result["errors"][0]["code"] == "AUDIO_NOT_FOUND"


def test_locate_audio_folder_with_multiple_candidates_needs_input(tmp_path):
    folder = tmp_path / "audio"
    folder.mkdir()
    (folder / "a.wav").write_text("a")
    (folder / "b.mp3").write_text("b")
    result = locate_audio_file(str(folder), tmp_path)
    assert result["status"] == "needs_input"
    assert len(result["candidates"]) == 2
