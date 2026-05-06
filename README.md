# Meeting Spec Pipeline

## OpenClaw Agent Handoff

你是執行這個 repo 的 OpenClaw Agent。你的任務不是一次把錄音變成規格書，而是控制一個可暫停、可補上下文、可追溯來源的 stage workflow。

邊界：

- Plugin 是 cloud/config/runtime surface: `plugins/meeting-transcribe-cloud`
- Skill 是 stage workflow: `skills/meeting-spec-pipeline`
- `transcribe-service` 是 HTTP STT boundary: `services/transcribe-service`

## Agent Execution Contract

每次只執行一個 stage。每個 stage 可暫停，完成後停止，回報產物路徑與下一個 stage 需要問使用者的問題。

Do Not：

- 不要一次問完所有背景、參考文件、規格資料。
- 不要跳過 `meeting_manifest.json` 或覆蓋原始逐字稿。
- 不要自行補 API、DB 欄位、系統名稱、權限規則、流程。

防腦補規則：

- 不確定就寫「待確認」。
- 資訊不足就寫「待補充」。
- 推論內容必須標示「推論，待確認」並附來源。

## Stage Gate Protocol

每個 stage 的固定回報格式：

```text
Stage: <stage_name>
Status: completed | needs_input | failed | partial
Report these artifact paths:
- <path>
Next user question:
- <question for next stage>
Stop after the stage completes.
```

如果 status 是 `needs_input`，只問當前 stage 缺的資料。不要推進下一 stage。

## Install Skill Into OpenClaw

```bash
cp -R skills/meeting-spec-pipeline ~/.openclaw/workspace/skills/meeting-spec-pipeline
openclaw skills info meeting-spec-pipeline --agent main
```

成功條件：

```text
Visible to model: yes
Available as command: yes
```

## Configure Provider

Plugin 只放 provider 設定，不放流程邏輯。不要把 real API key commit 進 repo。

```bash
cp plugins/meeting-transcribe-cloud/config/provider.example.json plugins/meeting-transcribe-cloud/config/provider.local.json
```

使用環境變數：

```bash
export GROQ_API_KEY="..."
export OPENAI_API_KEY="..."
export LOCAL_WHISPER_COMMAND="..."
```

MVP 測試可用 `mock` provider，不需要雲端 key。

## Start transcribe-service

```bash
uv run uvicorn transcribe_service.app:app --app-dir services/transcribe-service/src --host 127.0.0.1 --port 8765
```

服務責任只包含：

- 驗證音檔。
- 呼叫 provider adapter。
- 回傳 timestamped transcript segments。

## Stage Commands

### 1. locate_audio_file

先問使用者：錄音檔在哪裡？

```bash
uv run python skills/meeting-spec-pipeline/scripts/locate_audio_file.py "<audio-or-folder-path>" --workdir workdir
```

Report these artifact paths:

- `workdir/{meeting_id}/manifest/meeting_manifest.json`

Stop after the stage completes.

### 2. transcribe_audio

確認 transcribe-service 已啟動，再執行：

```bash
uv run python skills/meeting-spec-pipeline/scripts/transcribe_audio.py "<manifest-path>" --service-url http://127.0.0.1:8765 --provider groq
```

Report these artifact paths:

- `workdir/{meeting_id}/transcript/transcript_raw.json`
- `workdir/{meeting_id}/transcript/transcript.md`

Stop after the stage completes.

### 3. ask_meeting_context

只問會議背景：

```text
這場會議主題是什麼？
與會者有哪些人？
各與會者的部門、職稱或角色是什麼？
是否有主要發言人？
是否有特定名詞、系統名稱、專案名稱需要注意？
```

把使用者答案存成 JSON 後執行：

```bash
uv run python skills/meeting-spec-pipeline/scripts/save_meeting_context.py "<manifest-path>" "<context-json-path>"
```

Report these artifact paths:

- `workdir/{meeting_id}/manifest/meeting_context.json`

Stop after the stage completes.

### 4. generate_dialogue

```bash
uv run python skills/meeting-spec-pipeline/scripts/generate_dialogue.py "<manifest-path>"
```

Report these artifact paths:

- `workdir/{meeting_id}/dialogue/dialogue.md`
- `workdir/{meeting_id}/dialogue/dialogue_segments.json`

Stop after the stage completes.

### 5. ask_meeting_reference

只問會議記錄參考資料：

```text
是否有會議快記、簡報、流程圖、截圖、相關文件、既有討論紀錄或手寫筆記？
```

若使用者沒有資料，仍可用空清單執行；若有資料，逐份列入：

```bash
uv run python skills/meeting-spec-pipeline/scripts/collect_references.py "<manifest-path>" meeting "<reference-path-1>" "<reference-path-2>"
```

Report these artifact paths:

- `workdir/{meeting_id}/references/meeting_references_manifest.json`
- `workdir/{meeting_id}/references/meeting_reference_summary.md`

Stop after the stage completes.

### 6. generate_meeting_minutes

```bash
uv run python skills/meeting-spec-pipeline/scripts/generate_meeting_minutes.py "<manifest-path>"
```

Report these artifact paths:

- `workdir/{meeting_id}/minutes/meeting_minutes.md`
- `workdir/{meeting_id}/minutes/action_items.json`
- `workdir/{meeting_id}/minutes/open_questions.json`

Stop after the stage completes.

### 7. ask_spec_reference

只問規格參考文件：

```text
是否有舊版需求書、API 文件、DB 文件、系統畫面、權限表、業務規則、流程文件、錯誤案例、測試案例、法規或稽核要求？
```

```bash
uv run python skills/meeting-spec-pipeline/scripts/collect_references.py "<manifest-path>" spec "<reference-path-1>" "<reference-path-2>"
```

Report these artifact paths:

- `workdir/{meeting_id}/references/spec_references_manifest.json`
- `workdir/{meeting_id}/references/spec_reference_summary.md`

Stop after the stage completes.

### 8. generate_requirement_spec

```bash
uv run python skills/meeting-spec-pipeline/scripts/generate_requirement_spec.py "<manifest-path>"
```

Report these artifact paths:

- `workdir/{meeting_id}/spec/requirement_spec.md`
- `workdir/{meeting_id}/spec/requirement_spec.json`
- `workdir/{meeting_id}/spec/traceability_matrix.json`

Stop after the stage completes.

## Validation

```bash
uv run pytest
```

Requirement spec 章節檢查：

```bash
uv run python skills/meeting-spec-pipeline/scripts/validate_outputs.py "workdir/{meeting_id}/spec/requirement_spec.md"
```

## Failure Handling

遇到錯誤時只回報錯誤與下一個最小修復動作，不要硬推進：

- 找不到音檔：請使用者提供正確路徑。
- 多個候選音檔：列出候選檔，請使用者選一個。
- STT 失敗：回報 provider error，不改用其他 provider，除非使用者同意。
- 參考文件無法讀取：記錄 unreadable，繼續處理可讀文件。
- 產物缺章節：執行 validator，修正後再回報完成。
