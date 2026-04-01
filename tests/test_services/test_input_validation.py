"""
主要 POST エンドポイントの入力検証とレート制限

参照: utils/security.RateLimiter, utils/security.SecurityUtils, services/message_validator
"""

from __future__ import annotations

from utils.security import SecurityUtils


class TestInputValidation:
    def test_scenario_chat_empty_json_object_returns_error(self, csrf_client):
        # Given: 空オブジェクト JSON
        # When: POST /api/scenario_chat
        # Then: 4xx とエラー（シナリオID不正など）
        response = csrf_client.post("/api/scenario_chat", json={})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_scenario_feedback_missing_scenario_id_returns_error(self, csrf_client):
        # Given: scenario_id を含まない JSON
        # When: POST /api/scenario_feedback
        # Then: 400 とシナリオID必須メッセージ
        response = csrf_client.post(
            "/api/scenario_feedback",
            json={"model": "gemini-1.5-flash"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "シナリオID" in data.get("error", "")

    def test_chat_rejects_overlong_message(self, csrf_client):
        # Given: チャットセッション初期化済み
        # When: 10000文字超のメッセージで POST /api/chat
        # Then: 400（SecurityUtils.MAX_MESSAGE_LENGTH 超過）
        with csrf_client.session_transaction() as sess:
            sess["chat_settings"] = {
                "system_prompt": "テスト用システムプロンプト",
                "model": "gemini-1.5-flash",
                "partner_type": "colleague",
                "situation": "break",
                "topic": "general",
            }

        long_text = "a" * (SecurityUtils.MAX_MESSAGE_LENGTH + 1)
        response = csrf_client.post(
            "/api/chat",
            json={"message": long_text, "model": "gemini-1.5-flash"},
        )
        assert response.status_code == 400
        body = response.get_json()
        err_text = str(body)
        assert "10000" in err_text or "長すぎ" in err_text

    def test_quiz_answer_rejects_string_user_answer(self, client):
        # Given: 有効なクイズ辞書
        # When: user_answer が整数に変換できない文字列
        # Then: 400 と user_answer must be int（既存の int 成功パスとは別）
        quiz = {
            "question": "テスト",
            "choices": ["A", "B", "C"],
            "correct_answer": 0,
        }
        response = client.post(
            "/api/quiz/answer",
            json={
                "quiz": quiz,
                "user_answer": "not_an_integer",
                "context": [],
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "user_answer" in data.get("error", "").lower() or "int" in data.get("error", "").lower()

    def test_gamification_dashboard_post_returns_405(self, client):
        # Given: /api/gamification/dashboard は GET のみ
        # When: POST
        # Then: 405
        response = client.post("/api/gamification/dashboard", json={})
        assert response.status_code == 405

    def test_gamification_dashboard_rate_limit_returns_429(self, client, monkeypatch):
        # Given: ダッシュボード用 RateLimiter を厳しくする
        # When: 短時間に max を超える GET
        # Then: 429 Rate limit exceeded
        from routes import gamification_routes as gr

        lim = gr._gamification_dashboard_limiter
        monkeypatch.setattr(lim, "max_requests", 2)
        lim.requests.clear()

        for _ in range(2):
            r = client.get("/api/gamification/dashboard")
            assert r.status_code == 200

        r429 = client.get("/api/gamification/dashboard")
        assert r429.status_code == 429
        data = r429.get_json()
        assert "error" in data
        assert "429" in str(r429.status_code) or "Rate limit" in data.get("error", "")
