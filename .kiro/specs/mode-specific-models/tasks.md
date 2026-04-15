# Mode-Specific Models — Tasks (Phase B)

- [ ] T1. `services/model_selector.py` 新規作成 + `resolve_model()` 実装
- [ ] T2. `config/config.py` に `SCENARIO_MODEL` / `CHAT_MODEL` / `WATCH_MODEL` / `FEEDBACK_MODEL` 追加
- [ ] T3. `config/config.py` にモード別モデル用バリデータ追加
- [ ] T4. `routes/chat_routes.py` を `resolve_model("chat", ...)` に置換
- [ ] T5. `routes/scenario_routes.py` の会話/フィードバック箇所を `resolve_model` に置換
- [ ] T6. `routes/watch_routes.py` を `resolve_model("watch", ...)` に置換
- [ ] T7. `services/feedback_service.py` に Ollama 直接利用分岐を追加
- [ ] T8. `.env.example` / `README.md` にハイブリッド例を追加
- [ ] T9. `tests/test_services/test_model_selector.py` 新規作成
- [ ] T10. 既存テスト 1473 + Phase A 10 = 1483 全 PASS を確認
- [ ] T11. ローカル動作確認（モード別に異なるモデルが使われること）
- [ ] T12. commit + push + PR作成
