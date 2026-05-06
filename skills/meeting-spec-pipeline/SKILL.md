---
name: meeting-spec-pipeline
description: Use when turning a meeting audio recording into transcript, dialogue, meeting minutes, and requirement spec through a pauseable OpenClaw stage-based workflow with traceability and anti-hallucination rules.
---

# Meeting Spec Pipeline

Use this skill for the stage-based workflow: audio file -> raw transcript -> dialogue -> meeting minutes -> requirement spec.

This is not a one-click recording-to-PRD black box. Do not create or call a `run_all`, `one_click`, or "audio to PRD" wrapper. 每個 stage 必須可獨立執行、可中斷、可重跑，並在完成後把 artifacts 寫入 `workdir/{meeting_id}`。

Do not run every stage automatically. 每個 stage 完成後停止, report artifact paths, and ask before the next stage. 人工補充只能插在 stage boundary：context before dialogue, meeting references before minutes, spec references before requirement spec.

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
- If the user asks to continue, run only the next stage implied by `meeting_manifest.json`.
