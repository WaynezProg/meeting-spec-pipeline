# Meeting Spec Pipeline Design

## 目標

建立一組 OpenClaw Plugin + Skill，讓 Agent 可以把 30 分鐘以上會議錄音分階段整理成可追溯的需求規格書。

此系統不是「一次輸入錄音、自動吐規格書」。正確目標是 stage-based workflow：每個轉換階段都可暫停、補上下文、重跑，且所有後續文件都能追溯到來源 artifact。

## 核心原則

- 原始音檔與原始逐字稿不可覆蓋；後續 artifact 只新增或重建對應 stage 輸出。
- 資訊不足寫「待補充」，無法確認寫「待確認」；推論內容必須標示「推論，待確認」。
- STT provider 只存在於 Plugin / service config，不寫死在 Skill prompt。
- 長錄音先 chunk，再轉錄，再合併；chunk partial failure 要被記錄，不能假裝完整成功。
- OpenClaw 控制流程，transcribe-service 只負責音訊轉逐字稿。

## 專案邊界

### In Scope

- 建立 repo-local project，內含 OpenClaw Skill、Plugin scaffold、transcribe-service 範例實作、prompt templates、schemas、測試與 README。
- MVP 支援 mock provider，讓 end-to-end test 不需要真 API key。
- Plugin 設計支援 `auto`、`groq`、`openai`、`local`、`mock` provider config；成本策略預設為 Groq 優先、OpenAI mini fallback、local 最後。
- Skill 以 command / script 形式提供每個 stage：可單獨執行、可檢查狀態、可重跑。

### Out of Scope

- Diarization 不預設啟用；只有使用者需要講者分離時，才使用 diarize backend。一般情境仍用 meeting context 做 speaker assignment，無法判斷時標示「未知發言者」。
- 不保證真實雲端 STT API 在無 API key 下可跑；真 API path 會有 adapter 與錯誤處理，測試以 mock provider 覆蓋。
- 不把 OpenClaw gateway 設成必要的測試依賴；repo tests 先驗證 Skill/Plugin artifact 與 CLI behavior。

## 架構

系統分三層：

1. `plugins/meeting-transcribe-cloud`
   - 保存 plugin metadata、config schema、provider 設定說明。
   - 提供 transcribe-service 的設定入口與 API key 命名規範。
   - 不負責會議內容整理。

2. `services/transcribe-service`
   - HTTP API：`POST /transcribe`。
   - 接受 `audio_path`、`provider`、`language`、`enable_chunking`、`chunk_minutes`。
   - 負責驗證音檔、ffmpeg chunking、呼叫 provider adapter、輸出 timestamped segments。
   - MVP 內建 `mock` provider 供測試，正式 provider 使用環境變數或 config 檔取得 key。

3. `skills/meeting-spec-pipeline`
   - OpenClaw Skill entrypoint：`SKILL.md`。
   - 指示 Agent 依 stage 執行，不一次問完所有問題。
   - bundled scripts 實作 deterministic artifact 管理：locate audio、寫 manifest、呼叫 transcribe-service、生成 markdown/json skeleton、驗證章節。
   - bundled prompt templates 指導 Agent 生成 dialogue、minutes、spec。

## 目錄結構

```text
meeting-spec-pipeline/
  plugins/
    meeting-transcribe-cloud/
      .codex-plugin/plugin.json
      config/
        provider.schema.json
        provider.example.json
      README.md
  services/
    transcribe-service/
      pyproject.toml
      src/transcribe_service/
        app.py
        chunking.py
        providers.py
        schemas.py
      tests/
  skills/
    meeting-spec-pipeline/
      SKILL.md
      skill.json
      prompt.md
      prompts/
        dialogue.md
        meeting_minutes.md
        requirement_spec.md
      schemas/
        meeting_manifest.schema.json
        meeting_context.schema.json
        transcript_raw.schema.json
        dialogue_segments.schema.json
        action_items.schema.json
        open_questions.schema.json
        requirement_spec.schema.json
        traceability_matrix.schema.json
      scripts/
        locate_audio_file.py
        transcribe_audio.py
        save_meeting_context.py
        generate_dialogue.py
        collect_references.py
        generate_meeting_minutes.py
        generate_requirement_spec.py
        validate_outputs.py
  tests/
    fixtures/
      sample_meeting_audio.wav
      sample_transcribe_response.json
      meeting_context.json
      meeting_reference.txt
      spec_reference.txt
    test_e2e_mvp.py
    test_manifest.py
    test_stage_validation.py
  README.md
  pyproject.toml
```

## 工作目錄結構

每個會議建立獨立 workspace：

```text
workdir/{meeting_id}/
  source/
    original_audio.*
    chunks/
  transcript/
    transcript_raw.json
    transcript.md
  dialogue/
    dialogue.md
    dialogue_segments.json
  references/
    meeting_references_manifest.json
    meeting_reference_summary.md
    spec_references_manifest.json
    spec_reference_summary.md
  minutes/
    meeting_minutes.md
    action_items.json
    open_questions.json
  spec/
    requirement_spec.md
    requirement_spec.json
    traceability_matrix.json
  manifest/
    meeting_manifest.json
    meeting_context.json
```

`meeting_manifest.json` 是 workflow state source of truth。每個 stage 寫入：

- `stage`
- `status`: `not_started | needs_input | running | completed | failed | partial`
- `input_artifacts`
- `output_artifacts`
- `started_at`
- `completed_at`
- `errors`
- `source_trace`

## Stage Workflow

### 1. locate_audio_file

輸入：使用者提供音檔或資料夾路徑。

行為：

- 支援副檔名：`.mp3`、`.m4a`、`.wav`、`.mp4`。
- 如果是資料夾，搜尋支援格式；多個候選檔時回報清單並要求使用者選一個。
- 建立 `meeting_id`，格式：`YYYYMMDD-HHMMSS-{safe_stem}`。
- 建立 workdir 結構。
- 儲存原始音檔路徑、大小、mtime、格式、sha256。
- 複製或 symlink 原始檔到 `source/original_audio.*`。MVP 預設複製，避免原路徑消失。

輸出：

- `manifest/meeting_manifest.json`

### 2. transcribe_audio

輸入：

- `meeting_manifest.json`
- transcribe-service URL
- provider，預設 `groq`

行為：

- 呼叫 `POST /transcribe`，不在 Skill 內直接呼叫 Groq/OpenAI/local Whisper。
- service 依設定切 chunk；Skill 只保存 service 回傳結果。
- 保留 `segment_id`、`start`、`end`、`text`、`speaker`、`source_file`。
- 不修飾 STT 文字。

輸出：

- `transcript/transcript_raw.json`
- `transcript/transcript.md`

### 3. ask_meeting_context

輸入：使用者回答會議背景。

必問：

- 會議主題
- 與會者
- 各與會者部門、職稱或角色
- 主要發言人
- 特定名詞、系統名稱、專案名稱

行為：

- 不要求完整才能繼續。
- 未提供欄位寫 `unknown` 或 `[]`，生成文件時對應標示未知。

輸出：

- `manifest/meeting_context.json`

### 4. generate_dialogue

輸入：

- `transcript/transcript.md`
- `transcript/transcript_raw.json`
- `manifest/meeting_context.json`

行為：

- 依逐字稿與 context 推斷 speaker。
- 無法判斷寫「未知發言者」。
- 修正明顯 STT 錯字，但不得改變語意。
- 保留可回溯 timestamp 與 raw segment id。

輸出：

- `dialogue/dialogue.md`
- `dialogue/dialogue_segments.json`

### 5. ask_meeting_reference

輸入：使用者提供會議參考資料路徑或明確表示沒有。

行為：

- 支援文字、Markdown、JSON、CSV；PDF/DOCX 可先標示為需額外 parser。
- 逐份記錄可讀/不可讀狀態。
- 摘要參考資料，只能標示其可補強的會議議題，不覆蓋逐字稿。

輸出：

- `references/meeting_references_manifest.json`
- `references/meeting_reference_summary.md`

### 6. generate_meeting_minutes

輸入：

- `dialogue/dialogue.md`
- `references/meeting_reference_summary.md`
- `manifest/meeting_context.json`

行為：

- 產生會議資訊、重點、議題、結論、決議、待辦、負責人、時程、風險、爭議、待確認。
- 補充資料與逐字稿矛盾時，寫差異，不直接覆蓋。
- 無法確認寫「待確認」。

輸出：

- `minutes/meeting_minutes.md`
- `minutes/action_items.json`
- `minutes/open_questions.json`

### 7. ask_spec_reference

輸入：使用者提供規格參考文件路徑或明確表示沒有。

行為：

- 逐份摘要。
- 記錄每份文件影響哪些規格章節。
- 不可從檔名推論不存在的 API、DB 欄位、權限規則。

輸出：

- `references/spec_references_manifest.json`
- `references/spec_reference_summary.md`

### 8. generate_requirement_spec

輸入：

- `minutes/meeting_minutes.md`
- `minutes/action_items.json`
- `minutes/open_questions.json`
- `references/spec_reference_summary.md`

固定章節：

0. 文件資訊
1. 專案概述
2. 範圍定義
3. 現行流程與痛點 AS-IS
4. 目標流程 TO-BE
5. 功能需求
6. AI 判斷與生成需求
7. 後台介面需求
8. 系統整合需求
9. 資料與狀態設計
10. 權限、稽核與資安
11. 非功能需求
12. 驗收標準
13. 待確認事項
14. 分期建議
15. 附錄

行為：

- 只能根據已存在 artifact 生成。
- 不足處寫「待補充」。
- 推論內容標示「推論，待確認」。
- 第 13 章集中列出所有待確認事項。
- `traceability_matrix.json` 對每個需求記錄來源：minute section、dialogue segment、transcript segment、reference file。

輸出：

- `spec/requirement_spec.md`
- `spec/requirement_spec.json`
- `spec/traceability_matrix.json`

## 使用者互動設計

Skill 不一次問完所有問題。OpenClaw Agent 只在 stage 前詢問該 stage 所需 input：

- 逐字稿前：錄音檔在哪裡？
- 對話稿前：與會者與會議背景是什麼？
- 會議記錄前：是否有會議快記、簡報、流程圖等資料？
- 需求規格書前：是否有 API、DB、畫面、權限、舊規格等參考文件？

每個 stage 執行完成後停止，回報 artifact path 與下一步建議。使用者要繼續時再啟動下一 stage。

## Prompt Template 規則

所有生成 prompt 都要包含：

- 不確定就寫「待確認」。
- 資訊不足就寫「待補充」。
- 不要創造沒有來源的事實。
- 不要自行新增未被提及的系統、欄位、API、權限、流程。
- 若依上下文推論，必須標示「推論，待確認」。
- 必須保留 source reference，例如 transcript segment id、dialogue segment id、reference file path。

## transcribe-service API

### `POST /transcribe`

Request:

```json
{
  "audio_path": "string",
  "provider": "groq",
  "language": "zh",
  "enable_chunking": true,
  "chunk_minutes": 10
}
```

Response:

```json
{
  "meeting_id": "string",
  "segments": [
    {
      "segment_id": "seg-0001",
      "start": 0.0,
      "end": 10.5,
      "text": "string",
      "speaker": null,
      "source_file": "string"
    }
  ],
  "errors": []
}
```

Provider adapter contract:

- `provider = mock`: 回傳 deterministic fixture segments。
- `provider = auto`: 依序嘗試 Groq `whisper-large-v3-turbo`、OpenAI `gpt-4o-mini-transcribe`、local。
- `provider = groq`: 使用 OpenClaw SecretRef 解析 Groq key，呼叫官方 `/audio/transcriptions` API。
- `provider = openai`: 使用 OpenClaw SecretRef 解析 OpenAI key，呼叫官方 `/audio/transcriptions` API。
- `provider = local`: 呼叫本機 Whisper command 或 local HTTP endpoint，設定放在 plugin config。

API key 不寫進 repo，不寫進 prompt，不寫進 transcript artifact。

## Error Handling

- 找不到音檔：stage status `failed`，errors 寫 `AUDIO_NOT_FOUND`。
- 格式不支援：stage status `failed`，errors 寫 `UNSUPPORTED_AUDIO_FORMAT`。
- 多個候選音檔：stage status `needs_input`，列出候選檔。
- 音檔過長：service 啟用 chunking；若未啟用則回 `AUDIO_TOO_LONG_REQUIRES_CHUNKING`。
- STT API 失敗：stage status `failed` 或 `partial`，保留成功 chunk 與失敗 chunk。
- chunk 部分失敗：輸出 partial transcript，manifest 寫 `partial`，不允許後續 stage 默認完整。
- 參考文件無法讀取：manifest 記錄該檔 `unreadable`，摘要中列為無法讀取。
- 使用者未提供必要上下文：允許繼續，context 欄位寫 `unknown`，生成時標示未知。
- 產出文件缺少必要章節：`validate_outputs.py` 回非 0 exit code，stage status `failed`。

## Testing Strategy

測試不依賴真雲端 API。

- unit tests：manifest 建立、audio format validation、stage state transition、section validation。
- service tests：`POST /transcribe` mock provider、unsupported provider、missing audio、chunk metadata。
- e2e MVP test：fixture audio path -> locate -> mock transcribe -> save context -> generate dialogue -> collect no references -> minutes -> spec。
- prompt artifact tests：確認三個生成 prompt 都包含防腦補規則。
- README smoke：文件要能讓 OpenClaw agent 知道如何安裝、設定 provider、啟動 service、逐 stage 呼叫。

## MVP 成功條件

- `uv run pytest` 全綠。
- 可用 mock provider 跑出：
  - `meeting_manifest.json`
  - `transcript.md`
  - `meeting_context.json`
  - `dialogue.md`
  - `meeting_minutes.md`
  - `requirement_spec.md`
  - `traceability_matrix.json`
- README 清楚區分：
  - Plugin 是 cloud/config/runtime surface。
  - Skill 是 OpenClaw stage workflow。
  - transcribe-service 是可長跑 HTTP service。
  - 每個 stage 可暫停，不會強迫一路做到完成。

## Implementation Decisions

- Provider 設定使用 OpenClaw `secrets.providers.meeting-transcribe-cloud` + `plugins.entries.meeting-transcribe-cloud.config`；不再使用 repo-local `provider.local.json`。
- local Whisper provider 使用 command adapter；`provider=auto` 只有在 Groq / OpenAI 失敗後才 fallback 到 local，指定單一 provider 時不 fallback。
