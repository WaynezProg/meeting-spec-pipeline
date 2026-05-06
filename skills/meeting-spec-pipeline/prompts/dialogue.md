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
