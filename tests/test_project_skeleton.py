from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_top_level_files_exist():
    assert (ROOT / "pyproject.toml").exists()
    assert (ROOT / ".gitignore").exists()


def test_fixture_files_exist():
    assert (ROOT / "tests/fixtures/meeting_context.json").exists()
    assert (ROOT / "tests/fixtures/meeting_reference.txt").exists()
    assert (ROOT / "tests/fixtures/spec_reference.txt").exists()
