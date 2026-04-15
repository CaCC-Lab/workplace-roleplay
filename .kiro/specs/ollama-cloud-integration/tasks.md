# Ollama Cloud Integration — Tasks (Phase A)

## Task List

- [ ] T1. `requirements.txt` に `langchain-openai` 追加 + インストール
- [ ] T2. `config/config.py` に `OLLAMA_API_KEY` / `OLLAMA_BASE_URL` フィールド追加
- [ ] T3. `config/config.py` の `validate_model` に `ollama/*` パターン許可を追加
- [ ] T4. `services/llm_service.py` に `create_ollama_llm()` を追加
- [ ] T5. `services/llm_service.py` の `initialize_llm()` に ollama/ 分岐を追加
- [ ] T6. `.env.example` に Ollama 設定セクション追加
- [ ] T7. `README.md` に Ollama Cloud セットアップ手順追加
- [ ] T8. 単体テスト追加（`tests/test_services/test_llm_service_ollama.py`）
- [ ] T9. 既存テストが全件 PASS することを確認（1464 passed 維持）
- [ ] T10. ローカルで `DEFAULT_MODEL=ollama/gemma4:31b-cloud` に切替えて動作確認
- [ ] T11. commit + push + PR作成

## 完了条件
- Phase A の Functional Requirements (FR1-FR6) 全充足
- 既存テスト 1464 passed 維持 + Ollama 経路の新規テスト追加
- ローカルで Ollama Cloud 経由のチャット応答が返る
- Gemini 運用も従来どおり動作（`DEFAULT_MODEL=gemini/...` でリグレッションなし）
