# Questions Output Spec

使用時機：任何 stage 發現資訊不足、來源矛盾、或會阻塞下一階段時，輸出或更新 `questions.md`。問題不可混在結論裡帶過。

`questions.md` 必須使用以下格式：

```markdown
# Questions

## 待確認

### Q-001: 待確認事項標題
- 狀態：待確認
- 影響階段：generate_dialogue | generate_meeting_minutes | generate_requirement_spec
- 問題：需要使用者確認的具體問題。
- 為何需要：說明缺口會影響哪個產物。
- 目前依據：列出 transcript segment、dialogue id、meeting reference、spec reference。
- 預設處理：在正式產物標示「待確認」，不可自行補值。

## 待補充

### Q-002: 待補充資料標題
- 狀態：待補充
- 影響階段：generate_requirement_spec
- 問題：需要補哪份文件或哪個欄位。
- 為何需要：說明缺口會影響哪個章節。
- 目前依據：列出來源；沒有來源時寫「無」。
- 預設處理：對應章節寫「待補充」。
```
