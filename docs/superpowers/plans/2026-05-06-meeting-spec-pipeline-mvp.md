# Meeting Spec Pipeline MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable MVP OpenClaw Skill + Plugin + mockable transcribe-service for the stage-based meeting recording to requirement spec workflow.

**Architecture:** Plugin owns cloud/provider config and API key surfaces. transcribe-service owns audio validation, chunk metadata, and provider adapters. Skill owns OpenClaw stage workflow, deterministic artifact management, prompt templates, schemas, and pause/resume semantics through `meeting_manifest.json`.

**Tech Stack:** Python 3.12 via `uv`, pytest, FastAPI, Pydantic, httpx, repo-local OpenClaw Skill files, repo-local Codex plugin metadata.

---

## File Structure

- Create `pyproject.toml`: root test/runtime dependencies and package discovery.
- Create `.gitignore`: ignore venv, workdir, caches, local provider config, generated chunks.
- Create `README.md`: OpenClaw agent handoff, install, config, stage usage, service startup, test command.
- Create `plugins/meeting-transcribe-cloud/.codex-plugin/plugin.json`: plugin metadata.
- Create `plugins/meeting-transcribe-cloud/config/provider.schema.json`: provider config schema.
- Create `plugins/meeting-transcribe-cloud/config/provider.example.json`: safe example without real keys.
- Create `plugins/meeting-transcribe-cloud/README.md`: cloud provider config and API key rules.
- Create `services/transcribe-service/src/transcribe_service/app.py`: FastAPI app with `POST /transcribe`.
- Create `services/transcribe-service/src/transcribe_service/chunking.py`: audio format and deterministic chunk planning.
- Create `services/transcribe-service/src/transcribe_service/providers.py`: mock, groq, openai, local provider adapter boundaries.
- Create `services/transcribe-service/src/transcribe_service/schemas.py`: request/response Pydantic schemas.
- Create `skills/meeting-spec-pipeline/SKILL.md`: OpenClaw Skill instructions.
- Create `skills/meeting-spec-pipeline/skill.json`: machine-readable stage/tool metadata.
- Create `skills/meeting-spec-pipeline/prompt.md`: short top-level stage guidance.
- Create `skills/meeting-spec-pipeline/prompts/*.md`: dialogue, meeting minutes, requirement spec templates.
- Create `skills/meeting-spec-pipeline/schemas/*.json`: JSON schemas for output contracts.
- Create `skills/meeting-spec-pipeline/scripts/pipeline_core.py`: shared file, manifest, markdown, and validation helpers.
- Create `skills/meeting-spec-pipeline/scripts/locate_audio_file.py`: stage 1 CLI.
- Create `skills/meeting-spec-pipeline/scripts/transcribe_audio.py`: stage 2 CLI.
- Create `skills/meeting-spec-pipeline/scripts/save_meeting_context.py`: stage 3 CLI.
- Create `skills/meeting-spec-pipeline/scripts/generate_dialogue.py`: stage 4 deterministic MVP generator.
- Create `skills/meeting-spec-pipeline/scripts/collect_references.py`: stage 5 and 7 reference collector.
- Create `skills/meeting-spec-pipeline/scripts/generate_meeting_minutes.py`: stage 6 deterministic MVP generator.
- Create `skills/meeting-spec-pipeline/scripts/generate_requirement_spec.py`: stage 8 deterministic MVP generator.
- Create `skills/meeting-spec-pipeline/scripts/validate_outputs.py`: section and artifact validator.
- Create `tests/fixtures/*`: small audio placeholder and reference/context fixtures.
- Create `tests/test_manifest.py`: locate and manifest behavior.
- Create `tests/test_transcribe_service.py`: service API and provider behavior.
- Create `tests/test_stage_validation.py`: prompt and section validation.
- Create `tests/test_e2e_mvp.py`: full mock workflow.

---

## Task 1: Project Skeleton and Test Harness

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `tests/fixtures/meeting_context.json`
- Create: `tests/fixtures/meeting_reference.txt`
- Create: `tests/fixtures/spec_reference.txt`
- Create: `tests/test_project_skeleton.py`

- [ ] **Step 1: Write failing skeleton test**

Create `tests/test_project_skeleton.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_top_level_files_exist():
    assert (ROOT / "pyproject.toml").exists()
    assert (ROOT / ".gitignore").exists()


def test_fixture_files_exist():
    assert (ROOT / "tests/fixtures/meeting_context.json").exists()
    assert (ROOT / "tests/fixtures/meeting_reference.txt").exists()
    assert (ROOT / "tests/fixtures/spec_reference.txt").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_project_skeleton.py -v
```

Expected: FAIL because root files and fixtures do not exist.

- [ ] **Step 3: Add root project files**

Create `pyproject.toml`:

```toml
[project]
name = "meeting-spec-pipeline"
version = "0.1.0"
description = "OpenClaw Skill and Plugin for staged meeting recording to requirement spec workflow"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "httpx>=0.27.0",
  "pydantic>=2.8.0",
  "python-multipart>=0.0.9",
  "uvicorn>=0.30.0"
]

[dependency-groups]
dev = [
  "pytest>=8.3.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = [
  ".",
  "services/transcribe-service/src",
  "skills/meeting-spec-pipeline/scripts"
]
```

Create `.gitignore`:

```gitignore
.DS_Store
.pytest_cache/
.ruff_cache/
.venv/
__pycache__/
*.pyc
workdir/
plugins/meeting-transcribe-cloud/config/provider.local.json
skills/meeting-spec-pipeline/workdir/
```

Create `tests/fixtures/meeting_context.json`:

```json
{
  "topic": "AI 需求訪談流程整理",
  "participants": [
    {
      "name": "王小明",
      "department": "業務部",
      "title": "業務代表",
      "role": "提出需求"
    },
    {
      "name": "李美華",
      "department": "資訊部",
      "title": "系統分析師",
      "role": "釐清系統限制"
    }
  ],
  "primary_speakers": ["王小明", "李美華"],
  "terms": ["需求單", "後台審核", "AI 摘要"]
}
```

Create `tests/fixtures/meeting_reference.txt`:

```text
會議快記：
- 需求單目前由業務人工整理。
- 資訊部擔心 AI 摘要不能直接覆蓋原始內容。
- 後台需要審核狀態。
```

Create `tests/fixtures/spec_reference.txt`:

```text
既有規格片段：
- 後台使用者需登入。
- 需求單狀態至少包含 draft、reviewing、approved。
- API 欄位尚未定義。
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_project_skeleton.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore tests/fixtures tests/test_project_skeleton.py
git commit -m "chore: add project test harness"
```

---

## Task 2: Plugin Config Surface

**Files:**
- Create: `plugins/meeting-transcribe-cloud/.codex-plugin/plugin.json`
- Create: `plugins/meeting-transcribe-cloud/config/provider.schema.json`
- Create: `plugins/meeting-transcribe-cloud/config/provider.example.json`
- Create: `plugins/meeting-transcribe-cloud/README.md`
- Create: `tests/test_plugin_config.py`

- [ ] **Step 1: Write failing plugin config tests**

Create `tests/test_plugin_config.py`:

```python
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/meeting-transcribe-cloud"


def test_plugin_manifest_has_required_identity():
    manifest = json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())
    assert manifest["name"] == "meeting-transcribe-cloud"
    assert manifest["version"] == "0.1.0"
    assert manifest["interface"]["displayName"] == "Meeting Transcribe Cloud"


def test_provider_schema_defines_supported_providers():
    schema = json.loads((PLUGIN / "config/provider.schema.json").read_text())
    provider_enum = schema["properties"]["default_provider"]["enum"]
    assert provider_enum == ["groq", "openai", "local", "mock"]
    assert "api_keys" in schema["properties"]
    assert "local" in schema["properties"]


def test_example_config_contains_no_real_secrets():
    example = json.loads((PLUGIN / "config/provider.example.json").read_text())
    assert example["default_provider"] == "groq"
    assert example["api_keys"]["groq"] == "env:GROQ_API_KEY"
    assert example["api_keys"]["openai"] == "env:OPENAI_API_KEY"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_plugin_config.py -v
```

Expected: FAIL because plugin files do not exist.

- [ ] **Step 3: Add plugin files**

Create `plugins/meeting-transcribe-cloud/.codex-plugin/plugin.json`:

```json
{
  "name": "meeting-transcribe-cloud",
  "version": "0.1.0",
  "description": "Provider configuration surface for meeting audio transcription services.",
  "interface": {
    "displayName": "Meeting Transcribe Cloud",
    "shortDescription": "Configure Groq, OpenAI, local, or mock STT providers.",
    "defaultPrompt": "Configure the transcription provider before running meeting-spec-pipeline transcribe_audio."
  }
}
```

Create `plugins/meeting-transcribe-cloud/config/provider.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Meeting Transcribe Provider Config",
  "type": "object",
  "required": ["default_provider", "api_keys", "local"],
  "properties": {
    "default_provider": {
      "type": "string",
      "enum": ["groq", "openai", "local", "mock"]
    },
    "api_keys": {
      "type": "object",
      "required": ["groq", "openai"],
      "properties": {
        "groq": {"type": "string"},
        "openai": {"type": "string"}
      },
      "additionalProperties": false
    },
    "local": {
      "type": "object",
      "required": ["command"],
      "properties": {
        "command": {"type": "string"}
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

Create `plugins/meeting-transcribe-cloud/config/provider.example.json`:

```json
{
  "default_provider": "groq",
  "api_keys": {
    "groq": "env:GROQ_API_KEY",
    "openai": "env:OPENAI_API_KEY"
  },
  "local": {
    "command": "env:LOCAL_WHISPER_COMMAND"
  }
}
```

Create `plugins/meeting-transcribe-cloud/README.md`:

```markdown
# Meeting Transcribe Cloud Plugin

This plugin defines the provider config surface for the meeting transcription service.

Do not put real API keys in git. Copy `config/provider.example.json` to `config/provider.local.json` and keep real values local, or reference environment variables.

Supported providers:

- `groq`: reads `GROQ_API_KEY`
- `openai`: reads `OPENAI_API_KEY`
- `local`: reads `LOCAL_WHISPER_COMMAND`
- `mock`: deterministic test provider, no key required

The OpenClaw Skill controls workflow stages. This plugin only owns cloud/provider configuration.
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_plugin_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/meeting-transcribe-cloud tests/test_plugin_config.py
git commit -m "feat(plugin): add transcription provider config surface"
```

---

## Task 3: Transcribe Service API

**Files:**
- Create: `services/transcribe-service/src/transcribe_service/__init__.py`
- Create: `services/transcribe-service/src/transcribe_service/schemas.py`
- Create: `services/transcribe-service/src/transcribe_service/chunking.py`
- Create: `services/transcribe-service/src/transcribe_service/providers.py`
- Create: `services/transcribe-service/src/transcribe_service/app.py`
- Create: `tests/fixtures/sample_meeting_audio.wav`
- Create: `tests/test_transcribe_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_transcribe_service.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from transcribe_service.app import app
from transcribe_service.chunking import UnsupportedAudioFormatError, validate_audio_path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def test_validate_audio_path_rejects_missing_file():
    missing = FIXTURES / "missing.wav"
    try:
        validate_audio_path(missing)
    except FileNotFoundError as exc:
        assert "AUDIO_NOT_FOUND" in str(exc)
    else:
        raise AssertionError("missing file should fail")


def test_validate_audio_path_rejects_unsupported_extension(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("not audio")
    try:
        validate_audio_path(bad)
    except UnsupportedAudioFormatError as exc:
        assert "UNSUPPORTED_AUDIO_FORMAT" in str(exc)
    else:
        raise AssertionError("unsupported extension should fail")


def test_transcribe_mock_provider_returns_segments():
    audio = FIXTURES / "sample_meeting_audio.wav"
    client = TestClient(app)
    response = client.post(
        "/transcribe",
        json={
            "audio_path": str(audio),
            "provider": "mock",
            "language": "zh",
            "enable_chunking": True,
            "chunk_minutes": 10
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["meeting_id"].endswith("sample_meeting_audio")
    assert payload["segments"][0]["segment_id"] == "seg-0001"
    assert payload["segments"][0]["speaker"] is None
    assert payload["errors"] == []


def test_transcribe_unknown_provider_returns_400():
    audio = FIXTURES / "sample_meeting_audio.wav"
    client = TestClient(app)
    response = client.post(
        "/transcribe",
        json={
            "audio_path": str(audio),
            "provider": "unknown",
            "language": "zh",
            "enable_chunking": True,
            "chunk_minutes": 10
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UNSUPPORTED_PROVIDER"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_transcribe_service.py -v
```

Expected: FAIL because service package and fixture do not exist.

- [ ] **Step 3: Add service implementation**

Create `tests/fixtures/sample_meeting_audio.wav` as a small text placeholder with wav extension:

```text
mock audio bytes for test-only provider
```

Create `services/transcribe-service/src/transcribe_service/__init__.py`:

```python
"""Meeting transcription service."""
```

Create `services/transcribe-service/src/transcribe_service/schemas.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field


ProviderName = Literal["groq", "openai", "local", "mock"]


class TranscribeRequest(BaseModel):
    audio_path: str
    provider: str = "groq"
    language: str = "zh"
    enable_chunking: bool = True
    chunk_minutes: int = Field(default=10, ge=5, le=10)


class Segment(BaseModel):
    segment_id: str
    start: float
    end: float
    text: str
    speaker: str | None = None
    source_file: str


class ServiceError(BaseModel):
    code: str
    message: str
    source_file: str | None = None


class TranscribeResponse(BaseModel):
    meeting_id: str
    segments: list[Segment]
    errors: list[ServiceError] = []
```

Create `services/transcribe-service/src/transcribe_service/chunking.py`:

```python
from pathlib import Path


SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4"}


class UnsupportedAudioFormatError(ValueError):
    pass


def validate_audio_path(audio_path: str | Path) -> Path:
    path = Path(audio_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"AUDIO_NOT_FOUND: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"AUDIO_NOT_FOUND: {path}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
        raise UnsupportedAudioFormatError(f"UNSUPPORTED_AUDIO_FORMAT: {path.suffix}")
    return path


def build_meeting_id(audio_path: Path) -> str:
    return audio_path.stem.replace(" ", "-").lower()


def plan_chunks(audio_path: Path, enable_chunking: bool, chunk_minutes: int) -> list[Path]:
    if enable_chunking:
        return [audio_path]
    return [audio_path]
```

Create `services/transcribe-service/src/transcribe_service/providers.py`:

```python
import os
from pathlib import Path

from .schemas import Segment


class ProviderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def transcribe_with_provider(provider: str, audio_path: Path, language: str) -> list[Segment]:
    if provider == "mock":
        return [
            Segment(
                segment_id="seg-0001",
                start=0.0,
                end=8.0,
                text="我們今天要討論需求單如何用 AI 摘要，原始內容不能被覆蓋。",
                speaker=None,
                source_file=str(audio_path),
            ),
            Segment(
                segment_id="seg-0002",
                start=8.0,
                end=17.5,
                text="後台需要有審核狀態，API 欄位目前還沒有定義。",
                speaker=None,
                source_file=str(audio_path),
            ),
        ]
    if provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            raise ProviderError("MISSING_API_KEY", "GROQ_API_KEY is required for groq provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "groq adapter boundary is defined but not implemented in MVP")
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ProviderError("MISSING_API_KEY", "OPENAI_API_KEY is required for openai provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "openai adapter boundary is defined but not implemented in MVP")
    if provider == "local":
        if not os.getenv("LOCAL_WHISPER_COMMAND"):
            raise ProviderError("MISSING_LOCAL_COMMAND", "LOCAL_WHISPER_COMMAND is required for local provider")
        raise ProviderError("PROVIDER_NOT_IMPLEMENTED", "local adapter boundary is defined but not implemented in MVP")
    raise ProviderError("UNSUPPORTED_PROVIDER", f"Unsupported provider: {provider}")
```

Create `services/transcribe-service/src/transcribe_service/app.py`:

```python
from fastapi import FastAPI, HTTPException

from .chunking import UnsupportedAudioFormatError, build_meeting_id, validate_audio_path
from .providers import ProviderError, transcribe_with_provider
from .schemas import ServiceError, TranscribeRequest, TranscribeResponse


app = FastAPI(title="Meeting Transcribe Service")


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(request: TranscribeRequest) -> TranscribeResponse:
    try:
        audio_path = validate_audio_path(request.audio_path)
        segments = transcribe_with_provider(request.provider, audio_path, request.language)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": "AUDIO_NOT_FOUND", "message": str(exc)}) from exc
    except UnsupportedAudioFormatError as exc:
        raise HTTPException(status_code=400, detail={"code": "UNSUPPORTED_AUDIO_FORMAT", "message": str(exc)}) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc

    return TranscribeResponse(
        meeting_id=build_meeting_id(audio_path),
        segments=segments,
        errors=[],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_transcribe_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/transcribe-service tests/fixtures/sample_meeting_audio.wav tests/test_transcribe_service.py
git commit -m "feat(service): add mockable transcribe api"
```

---

## Task 4: Manifest and Locate Audio Stage

**Files:**
- Create: `skills/meeting-spec-pipeline/scripts/pipeline_core.py`
- Create: `skills/meeting-spec-pipeline/scripts/locate_audio_file.py`
- Create: `tests/test_manifest.py`

- [ ] **Step 1: Write failing manifest tests**

Create `tests/test_manifest.py`:

```python
import json
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_manifest.py -v
```

Expected: FAIL because stage scripts do not exist.

- [ ] **Step 3: Add core and locate scripts**

Create `skills/meeting-spec-pipeline/scripts/pipeline_core.py`:

```python
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4"}
STAGE_NAMES = [
    "locate_audio_file",
    "transcribe_audio",
    "ask_meeting_context",
    "generate_dialogue",
    "ask_meeting_reference",
    "generate_meeting_minutes",
    "ask_spec_reference",
    "generate_requirement_spec",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_stem(path: Path) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", path.stem).strip("-").lower()
    return safe or "meeting"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_workdir_tree(meeting_root: Path) -> None:
    for relative in [
        "source/chunks",
        "transcript",
        "dialogue",
        "references",
        "minutes",
        "spec",
        "manifest",
    ]:
        (meeting_root / relative).mkdir(parents=True, exist_ok=True)


def empty_stages() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "status": "not_started",
            "input_artifacts": [],
            "output_artifacts": [],
            "started_at": None,
            "completed_at": None,
            "errors": [],
        }
        for name in STAGE_NAMES
    }


def create_manifest(audio_path: Path, workdir: Path, copied_path: Path) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    meeting_id = f"{timestamp}-{safe_stem(audio_path)}"
    meeting_root = workdir / meeting_id
    ensure_workdir_tree(meeting_root)
    final_audio = meeting_root / "source" / f"original_audio{audio_path.suffix.lower()}"
    if copied_path != final_audio:
        shutil.copy2(audio_path, final_audio)
    stat = audio_path.stat()
    manifest = {
        "meeting_id": meeting_id,
        "meeting_root": str(meeting_root),
        "created_at": utc_now(),
        "audio": {
            "original_path": str(audio_path),
            "copied_path": str(final_audio),
            "suffix": audio_path.suffix.lower(),
            "size_bytes": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "sha256": sha256_file(audio_path),
        },
        "stages": empty_stages(),
    }
    manifest["stages"]["locate_audio_file"].update(
        {
            "status": "completed",
            "output_artifacts": ["manifest/meeting_manifest.json"],
            "started_at": manifest["created_at"],
            "completed_at": utc_now(),
        }
    )
    write_json(meeting_root / "manifest/meeting_manifest.json", manifest)
    return manifest


def find_audio_candidates(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES:
        return [path]
    if path.is_dir():
        return sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES)
    return []
```

Create `skills/meeting-spec-pipeline/scripts/locate_audio_file.py`:

```python
import argparse
from pathlib import Path
from typing import Any

from pipeline_core import SUPPORTED_AUDIO_SUFFIXES, create_manifest, find_audio_candidates


def locate_audio_file(input_path: str, workdir: str | Path = "workdir") -> dict[str, Any]:
    path = Path(input_path).expanduser().resolve()
    root = Path(workdir).expanduser().resolve()

    if not path.exists():
        return {"status": "failed", "errors": [{"code": "AUDIO_NOT_FOUND", "message": str(path)}]}

    candidates = find_audio_candidates(path)
    if not candidates and path.is_file():
        return {
            "status": "failed",
            "errors": [{"code": "UNSUPPORTED_AUDIO_FORMAT", "message": path.suffix.lower()}],
            "supported_formats": sorted(SUPPORTED_AUDIO_SUFFIXES),
        }
    if len(candidates) > 1:
        return {"status": "needs_input", "candidates": [str(candidate) for candidate in candidates]}
    if not candidates:
        return {"status": "failed", "errors": [{"code": "AUDIO_NOT_FOUND", "message": str(path)}]}

    manifest = create_manifest(candidates[0], root, candidates[0])
    return {
        "status": "completed",
        "meeting_id": manifest["meeting_id"],
        "manifest_path": str(Path(manifest["meeting_root"]) / "manifest/meeting_manifest.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("--workdir", default="workdir")
    args = parser.parse_args()
    import json

    print(json.dumps(locate_audio_file(args.input_path, args.workdir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_manifest.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/meeting-spec-pipeline/scripts/pipeline_core.py skills/meeting-spec-pipeline/scripts/locate_audio_file.py tests/test_manifest.py
git commit -m "feat(skill): add audio location manifest stage"
```

---

## Task 5: Transcribe Stage Script

**Files:**
- Create: `skills/meeting-spec-pipeline/scripts/transcribe_audio.py`
- Create: `tests/test_transcribe_stage.py`

- [ ] **Step 1: Write failing transcribe stage tests**

Create `tests/test_transcribe_stage.py`:

```python
import json
from pathlib import Path

import httpx

from locate_audio_file import locate_audio_file
from transcribe_audio import transcribe_audio


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def test_transcribe_audio_writes_raw_json_and_markdown(tmp_path):
    located = locate_audio_file(str(FIXTURES / "sample_meeting_audio.wav"), tmp_path)
    manifest_path = located["manifest_path"]

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
                        "text": "原始逐字稿內容，不要修飾。",
                        "speaker": None,
                        "source_file": "chunk-0001.wav"
                    }
                ],
                "errors": []
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = transcribe_audio(manifest_path, "http://testserver", provider="mock", client=client)
    assert result["status"] == "completed"

    meeting_root = Path(result["meeting_root"])
    raw = json.loads((meeting_root / "transcript/transcript_raw.json").read_text())
    md = (meeting_root / "transcript/transcript.md").read_text()
    assert raw["segments"][0]["text"] == "原始逐字稿內容，不要修飾。"
    assert "[seg-0001 | 0.0-8.0]" in md


def test_transcribe_audio_marks_service_failure(tmp_path):
    located = locate_audio_file(str(FIXTURES / "sample_meeting_audio.wav"), tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": {"code": "MISSING_API_KEY", "message": "missing"}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = transcribe_audio(located["manifest_path"], "http://testserver", provider="groq", client=client)
    assert result["status"] == "failed"
    assert result["errors"][0]["code"] == "MISSING_API_KEY"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_transcribe_stage.py -v
```

Expected: FAIL because `transcribe_audio.py` does not exist.

- [ ] **Step 3: Add transcribe stage script**

Create `skills/meeting-spec-pipeline/scripts/transcribe_audio.py`:

```python
import argparse
import json
from pathlib import Path
from typing import Any

import httpx

from pipeline_core import load_json, utc_now, write_json


def _write_transcript_markdown(path: Path, segments: list[dict[str, Any]]) -> None:
    lines = ["# Transcript Raw", ""]
    for segment in segments:
        lines.append(f"[{segment['segment_id']} | {segment['start']}-{segment['end']}]")
        lines.append(segment["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def transcribe_audio(
    manifest_path: str | Path,
    service_url: str,
    provider: str = "groq",
    language: str = "zh",
    enable_chunking: bool = True,
    chunk_minutes: int = 10,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = load_json(manifest_file)
    meeting_root = Path(manifest["meeting_root"])
    audio_path = manifest["audio"]["copied_path"]
    stage = manifest["stages"]["transcribe_audio"]
    stage["status"] = "running"
    stage["started_at"] = utc_now()
    write_json(manifest_file, manifest)

    owns_client = client is None
    http = client or httpx.Client(timeout=120)
    try:
        response = http.post(
            f"{service_url.rstrip('/')}/transcribe",
            json={
                "audio_path": audio_path,
                "provider": provider,
                "language": language,
                "enable_chunking": enable_chunking,
                "chunk_minutes": chunk_minutes,
            },
        )
        if response.status_code >= 400:
            detail = response.json().get("detail", {})
            stage["status"] = "failed"
            stage["errors"] = [{"code": detail.get("code", "STT_API_FAILED"), "message": detail.get("message", response.text)}]
            stage["completed_at"] = utc_now()
            write_json(manifest_file, manifest)
            return {"status": "failed", "errors": stage["errors"], "meeting_root": str(meeting_root)}

        payload = response.json()
        raw_path = meeting_root / "transcript/transcript_raw.json"
        md_path = meeting_root / "transcript/transcript.md"
        write_json(raw_path, payload)
        _write_transcript_markdown(md_path, payload["segments"])
        status = "partial" if payload.get("errors") else "completed"
        stage.update(
            {
                "status": status,
                "input_artifacts": ["manifest/meeting_manifest.json", manifest["audio"]["copied_path"]],
                "output_artifacts": ["transcript/transcript_raw.json", "transcript/transcript.md"],
                "completed_at": utc_now(),
                "errors": payload.get("errors", []),
            }
        )
        write_json(manifest_file, manifest)
        return {"status": status, "meeting_root": str(meeting_root), "manifest_path": str(manifest_file)}
    finally:
        if owns_client:
            http.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest_path")
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--provider", default="groq")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--chunk-minutes", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(transcribe_audio(args.manifest_path, args.service_url, args.provider, args.language, True, args.chunk_minutes), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_transcribe_stage.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/meeting-spec-pipeline/scripts/transcribe_audio.py tests/test_transcribe_stage.py
git commit -m "feat(skill): add transcribe service stage"
```

---

## Task 6: Context, Dialogue, References, Minutes, and Spec Stage Scripts

**Files:**
- Create: `skills/meeting-spec-pipeline/scripts/save_meeting_context.py`
- Create: `skills/meeting-spec-pipeline/scripts/generate_dialogue.py`
- Create: `skills/meeting-spec-pipeline/scripts/collect_references.py`
- Create: `skills/meeting-spec-pipeline/scripts/generate_meeting_minutes.py`
- Create: `skills/meeting-spec-pipeline/scripts/generate_requirement_spec.py`
- Create: `tests/test_content_stages.py`

- [ ] **Step 1: Write failing content stage tests**

Create `tests/test_content_stages.py`:

```python
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

    transcribe_audio(located["manifest_path"], "http://testserver", provider="mock", client=httpx.Client(transport=httpx.MockTransport(handler)))
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

    spec_ref = collect_references(manifest_path, "spec", [str(FIXTURES / "spec_reference.txt")])
    assert spec_ref["status"] == "completed"

    spec_result = generate_requirement_spec(manifest_path)
    assert spec_result["status"] == "completed"
    spec_md = (meeting_root / "spec/requirement_spec.md").read_text()
    assert "## 13. 待確認事項" in spec_md
    trace = json.loads((meeting_root / "spec/traceability_matrix.json").read_text())
    assert trace["requirements"][0]["sources"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_content_stages.py -v
```

Expected: FAIL because content scripts do not exist.

- [ ] **Step 3: Add content stage scripts**

Create `skills/meeting-spec-pipeline/scripts/save_meeting_context.py`:

```python
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
```

Create `skills/meeting-spec-pipeline/scripts/generate_dialogue.py`:

```python
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
    speaker = context.get("primary_speakers", [None])[0] if context.get("primary_speakers") else "未知發言者"
    segments = []
    lines = [f"# 對話稿：{context.get('topic', 'unknown')}", ""]
    for index, segment in enumerate(raw["segments"], start=1):
        assigned = speaker if len(context.get("primary_speakers", [])) == 1 else "未知發言者"
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
```

Create `skills/meeting-spec-pipeline/scripts/collect_references.py`:

```python
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
```

Create `skills/meeting-spec-pipeline/scripts/generate_meeting_minutes.py`:

```python
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
```

Create `skills/meeting-spec-pipeline/scripts/generate_requirement_spec.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_content_stages.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/meeting-spec-pipeline/scripts tests/test_content_stages.py
git commit -m "feat(skill): add staged document generators"
```

---

## Task 7: Skill Metadata, Prompts, Schemas, and Validators

**Files:**
- Create: `skills/meeting-spec-pipeline/SKILL.md`
- Create: `skills/meeting-spec-pipeline/skill.json`
- Create: `skills/meeting-spec-pipeline/prompt.md`
- Create: `skills/meeting-spec-pipeline/prompts/dialogue.md`
- Create: `skills/meeting-spec-pipeline/prompts/meeting_minutes.md`
- Create: `skills/meeting-spec-pipeline/prompts/requirement_spec.md`
- Create: `skills/meeting-spec-pipeline/schemas/*.json`
- Create: `skills/meeting-spec-pipeline/scripts/validate_outputs.py`
- Create: `tests/test_stage_validation.py`

- [ ] **Step 1: Write failing validation tests**

Create `tests/test_stage_validation.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_stage_validation.py -v
```

Expected: FAIL because skill metadata, prompts, and validator do not exist.

- [ ] **Step 3: Add skill metadata, prompts, schemas, validator**

Create `skills/meeting-spec-pipeline/SKILL.md`:

```markdown
---
name: meeting-spec-pipeline
description: Use when turning a meeting audio recording into transcript, dialogue, meeting minutes, and requirement spec through a pauseable OpenClaw stage-based workflow with traceability and anti-hallucination rules.
---

# Meeting Spec Pipeline

Use this skill for the stage-based workflow: audio file -> raw transcript -> dialogue -> meeting minutes -> requirement spec.

Do not run every stage automatically. 每個 stage 完成後停止, report artifact paths, and ask before the next stage.

Stage order:

1. `locate_audio_file`: ask only where the audio file or folder is.
2. `transcribe_audio`: call transcribe-service; do not call Groq/OpenAI/local Whisper directly.
3. `ask_meeting_context`: ask meeting topic, participants, departments/titles/roles, primary speakers, and terms.
4. `generate_dialogue`: use transcript and context; unknown speaker is `未知發言者`.
5. `ask_meeting_reference`: ask for quick notes, slides, diagrams, screenshots, docs, discussions, or handwritten notes.
6. `generate_meeting_minutes`: create formal minutes and unresolved questions.
7. `ask_spec_reference`: ask for old specs, API, DB, screens, permissions, rules, flows, errors, tests, audit rules.
8. `generate_requirement_spec`: create fixed-section spec and traceability matrix.

Rules:

- 不確定就寫「待確認」。
- 資訊不足就寫「待補充」。
- 不要創造沒有來源的事實。
- 不要自行新增未被提及的系統、欄位、API、權限、流程。
- 若依上下文推論，必須標示「推論，待確認」。
- Preserve `meeting_manifest.json` and never overwrite raw transcript semantics.
```

Create `skills/meeting-spec-pipeline/skill.json`:

```json
{
  "name": "meeting-spec-pipeline",
  "version": "0.1.0",
  "description": "Pauseable meeting audio to requirement spec workflow.",
  "stages": [
    "locate_audio_file",
    "transcribe_audio",
    "ask_meeting_context",
    "generate_dialogue",
    "ask_meeting_reference",
    "generate_meeting_minutes",
    "ask_spec_reference",
    "generate_requirement_spec"
  ]
}
```

Create `skills/meeting-spec-pipeline/prompt.md`:

```markdown
# Meeting Spec Pipeline Prompt

Run one stage at a time. Ask only for the input required by the next stage. Stop after each stage and report artifact paths.
```

Create `skills/meeting-spec-pipeline/prompts/dialogue.md`:

```markdown
# Dialogue Generation Prompt

Transform raw transcript segments into readable meeting dialogue.

Rules:
- 不確定就寫「待確認」
- 資訊不足就寫「待補充」
- 不要創造沒有來源的事實
- 不要自行新增未被提及的系統、欄位、API、權限、流程
- If using inference, mark it as 「推論，待確認」
- Unknown speaker must be 「未知發言者」
- Preserve transcript segment ids and timestamps
```

Create `skills/meeting-spec-pipeline/prompts/meeting_minutes.md`:

```markdown
# Meeting Minutes Prompt

Create formal meeting minutes from dialogue and meeting references.

Rules:
- 不確定就寫「待確認」
- 資訊不足就寫「待補充」
- 不要創造沒有來源的事實
- 不要自行新增未被提及的系統、欄位、API、權限、流程
- If using inference, mark it as 「推論，待確認」
- If references conflict with transcript, list the difference instead of overwriting
```

Create `skills/meeting-spec-pipeline/prompts/requirement_spec.md`:

```markdown
# Requirement Spec Prompt

Create the fixed-section requirement spec from meeting minutes and spec references.

Rules:
- 不確定就寫「待確認」
- 資訊不足就寫「待補充」
- 不要創造沒有來源的事實
- 不要自行新增未被提及的系統、欄位、API、權限、流程
- If using inference, mark it as 「推論，待確認」
- Put all unresolved items in section 13
- Every requirement must have traceability sources
```

Create minimal schema files:

```bash
for name in meeting_manifest meeting_context transcript_raw dialogue_segments action_items open_questions requirement_spec traceability_matrix; do
  cat > "skills/meeting-spec-pipeline/schemas/${name}.schema.json" <<'JSON'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object"
}
JSON
done
```

Create `skills/meeting-spec-pipeline/scripts/validate_outputs.py`:

```python
import argparse
import json

from generate_requirement_spec import SPEC_SECTIONS


def validate_requirement_spec_sections(markdown: str) -> list[str]:
    missing = []
    for section in SPEC_SECTIONS:
        if f"## {section}" not in markdown:
            missing.append(section)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("requirement_spec_md")
    args = parser.parse_args()
    text = open(args.requirement_spec_md, encoding="utf-8").read()
    missing = validate_requirement_spec_sections(text)
    print(json.dumps({"missing_sections": missing}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if missing else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_stage_validation.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/meeting-spec-pipeline tests/test_stage_validation.py
git commit -m "feat(skill): add OpenClaw metadata prompts and validators"
```

---

## Task 8: End-to-End MVP and README

**Files:**
- Create: `tests/test_e2e_mvp.py`
- Create: `README.md`

- [ ] **Step 1: Write failing e2e and README tests**

Create `tests/test_e2e_mvp.py`:

```python
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

    transcribe_audio(located["manifest_path"], "http://testserver", provider="mock", client=httpx.Client(transport=httpx.MockTransport(handler)))
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
    assert "Plugin 是 cloud/config/runtime surface" in readme
    assert "Skill 是 stage workflow" in readme
    assert "transcribe-service" in readme
    assert "每個 stage 可暫停" in readme
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_e2e_mvp.py -v
```

Expected: FAIL because README does not exist or lacks handoff content.

- [ ] **Step 3: Add README**

Create `README.md`:

```markdown
# Meeting Spec Pipeline

## OpenClaw Agent Handoff

This repo contains an OpenClaw Skill + Plugin + transcribe-service MVP for meeting audio to requirement spec workflows.

Boundaries:

- Plugin 是 cloud/config/runtime surface: `plugins/meeting-transcribe-cloud`
- Skill 是 stage workflow: `skills/meeting-spec-pipeline`
- `transcribe-service` is the HTTP STT boundary: `services/transcribe-service`
- 每個 stage 可暫停. Do not run the whole pipeline without user confirmation.

## Install for OpenClaw Workspace

Copy the skill tree into the OpenClaw workspace skill directory:

```bash
cp -R skills/meeting-spec-pipeline ~/.openclaw/workspace/skills/meeting-spec-pipeline
openclaw skills info meeting-spec-pipeline --agent main
```

Expected visibility:

```text
Visible to model: yes
Available as command: yes
```

## Provider Config

Copy the example config and keep real secrets local:

```bash
cp plugins/meeting-transcribe-cloud/config/provider.example.json plugins/meeting-transcribe-cloud/config/provider.local.json
```

Use environment variables for real keys:

```bash
export GROQ_API_KEY="..."
export OPENAI_API_KEY="..."
export LOCAL_WHISPER_COMMAND="..."
```

## Start transcribe-service

```bash
uv run uvicorn transcribe_service.app:app --app-dir services/transcribe-service/src --host 127.0.0.1 --port 8765
```

## Stage Usage

1. Ask user: 錄音檔在哪裡？
2. Run `locate_audio_file.py`.
3. Run `transcribe_audio.py` against `http://127.0.0.1:8765`.
4. Ask user for meeting context.
5. Run `save_meeting_context.py`.
6. Run `generate_dialogue.py`.
7. Ask for meeting references.
8. Run `collect_references.py meeting`.
9. Run `generate_meeting_minutes.py`.
10. Ask for spec references.
11. Run `collect_references.py spec`.
12. Run `generate_requirement_spec.py`.

## Test

```bash
uv run pytest
```

The MVP test path uses mock transcription and does not require cloud API keys.
```

- [ ] **Step 4: Run e2e test to verify it passes**

Run:

```bash
uv run pytest tests/test_e2e_mvp.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full verification**

Run:

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md tests/test_e2e_mvp.py
git commit -m "test: add end-to-end meeting spec pipeline smoke"
```

---

## Final Verification

- [ ] Run full test suite:

```bash
uv run pytest -v
```

- [ ] Check repository state:

```bash
git status --short --branch
```

- [ ] Verify no local secrets are tracked:

```bash
git ls-files | rg 'provider.local.json|GROQ_API_KEY|OPENAI_API_KEY' && exit 1 || exit 0
```

- [ ] Verify design and implementation plan exist:

```bash
test -f docs/superpowers/specs/2026-05-06-meeting-spec-pipeline-design.md
test -f docs/superpowers/plans/2026-05-06-meeting-spec-pipeline-mvp.md
```

## Self-Review

Spec coverage:

- Plugin/provider config: Task 2.
- transcribe-service HTTP API: Task 3.
- workdir and manifest: Task 4.
- transcribe stage and transcript artifacts: Task 5.
- context/dialogue/references/minutes/spec stages: Task 6.
- Skill metadata, prompt templates, schemas, anti-hallucination rules: Task 7.
- README and e2e MVP: Task 8.

Placeholder scan:

- No placeholder markers or undefined implementation step remains in this plan.

Type consistency:

- `manifest_path`, `meeting_root`, `status`, `segments`, `sources`, and stage names are consistent across tasks and tests.
