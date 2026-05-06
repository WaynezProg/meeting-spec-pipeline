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
