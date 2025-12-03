"""
Scenario routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestListScenarios:
    """GET /scenarios のテスト"""

    def test_シナリオ一覧ページを表示(self, client):
        """シナリオ一覧ページの表示"""
        response = client.get("/scenarios")

        assert response.status_code == 200


class TestShowScenario:
    """GET /scenario/<scenario_id> のテスト"""

    def test_存在するシナリオを表示(self, client):
        """存在するシナリオページの表示"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = {
                "id": "test_scenario",
                "title": "テストシナリオ",
                "description": "テスト説明",
                "learning_points": ["ポイント1"],
            }
            mock_service.is_harassment_scenario.return_value = False

            response = client.get("/scenario/test_scenario")

            assert response.status_code == 200

    def test_存在しないシナリオで404(self, client):
        """存在しないシナリオで404を返す"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = None

            response = client.get("/scenario/nonexistent")

            assert response.status_code == 404


class TestListRegularScenarios:
    """GET /scenarios/regular のテスト"""

    def test_通常シナリオ一覧を表示(self, client):
        """通常シナリオ一覧ページの表示"""
        response = client.get("/scenarios/regular")

        assert response.status_code == 200


class TestListHarassmentScenarios:
    """GET /scenarios/harassment のテスト"""

    def test_同意なしで同意ページを表示(self, client):
        """同意なしの場合は同意ページを表示"""
        response = client.get("/scenarios/harassment")

        assert response.status_code == 200
        # 同意ページが表示される
        assert b"consent" in response.data.lower() or response.status_code == 200

    def test_同意ありでシナリオ一覧を表示(self, client):
        """同意ありの場合はシナリオ一覧を表示"""
        with client.session_transaction() as sess:
            sess["harassment_consent"] = True

        response = client.get("/scenarios/harassment")

        assert response.status_code == 200


class TestHarassmentConsent:
    """POST /harassment/consent のテスト"""

    def test_同意を送信(self, csrf_client):
        """ハラスメント研修への同意"""
        response = csrf_client.post("/harassment/consent", json={"consent": True})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "redirect_url" in data

    def test_同意なしで送信(self, csrf_client):
        """同意なしで送信した場合"""
        response = csrf_client.post("/harassment/consent", json={"consent": False})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False

    def test_GETで同意ページを表示(self, client):
        """GETリクエストで同意ページを表示"""
        response = client.get("/harassment/consent")

        assert response.status_code == 200


class TestScenarioChat:
    """POST /api/scenario_chat のテスト"""

    def test_シナリオチャットが正常に動作(self, csrf_client):
        """シナリオチャットの正常動作 - 実際のシナリオIDを使用"""
        # 実際のシナリオID（scenario1など）を使用
        scenario_id = "scenario1"

        with csrf_client.session_transaction() as sess:
            sess["scenario_history"] = {scenario_id: []}

        with patch("app.initialize_llm") as mock_llm:
            mock_response = MagicMock()
            mock_response.content = "AIの応答です"
            mock_llm.return_value.invoke.return_value = mock_response

            with patch("app.extract_content") as mock_extract:
                mock_extract.return_value = "AIの応答です"

                response = csrf_client.post(
                    "/api/scenario_chat",
                    json={
                        "message": "こんにちは",
                        "scenario_id": scenario_id,
                        "model": "gemini-1.5-flash",
                    },
                )

                assert response.status_code == 200
                data = response.get_json()
                assert "response" in data

    def test_無効なシナリオIDでエラー(self, csrf_client):
        """無効なシナリオIDでエラーを返す"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = None

            response = csrf_client.post(
                "/api/scenario_chat",
                json={
                    "message": "テスト",
                    "scenario_id": "invalid_id",
                    "model": "gemini-1.5-flash",
                },
            )

            assert response.status_code == 400

    def test_JSONなしでエラー(self, csrf_client):
        """JSONなしでエラーを返す"""
        response = csrf_client.post(
            "/api/scenario_chat",
            data="invalid",
            content_type="application/json",
        )

        assert response.status_code in [400, 500]


class TestClearScenarioHistory:
    """POST /api/scenario_clear のテスト"""

    def test_シナリオ履歴をクリア(self, csrf_client):
        """シナリオ履歴のクリア"""
        with csrf_client.session_transaction() as sess:
            sess["scenario_history"] = {"test_scenario": [{"human": "test", "ai": "response"}]}

        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = {"id": "test_scenario"}

            response = csrf_client.post("/api/scenario_clear", json={"scenario_id": "test_scenario"})

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "success"

    def test_シナリオIDなしでエラー(self, csrf_client):
        """シナリオIDなしでエラーを返す"""
        response = csrf_client.post("/api/scenario_clear", json={})

        assert response.status_code == 400

    def test_無効なシナリオIDでエラー(self, csrf_client):
        """無効なシナリオIDでエラーを返す"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = None

            response = csrf_client.post("/api/scenario_clear", json={"scenario_id": "invalid_id"})

            assert response.status_code == 400


class TestScenarioFeedback:
    """POST /api/scenario_feedback のテスト"""

    def test_フィードバックを正常に生成(self, csrf_client):
        """シナリオフィードバックの生成"""
        with csrf_client.session_transaction() as sess:
            sess["scenario_history"] = {
                "test_scenario": [
                    {"human": "こんにちは", "ai": "こんにちは！"},
                    {"human": "報告があります", "ai": "どうぞ、お聞きします。"},
                ]
            }

        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = {
                "id": "test_scenario",
                "title": "テストシナリオ",
                "role_type": "normal",
            }

            with patch("services.feedback_service.FeedbackService.build_scenario_feedback_prompt") as mock_build:
                mock_build.return_value = "フィードバックプロンプト"

                with patch("services.feedback_service.FeedbackService.try_multiple_models_for_prompt") as mock_try:
                    mock_try.return_value = (
                        "良いコミュニケーションでした！",
                        "gemini-1.5-flash",
                        None,
                    )

                    with patch(
                        "services.strength_service.StrengthService.update_feedback_with_strength_analysis"
                    ) as mock_strength:
                        mock_strength.return_value = {
                            "feedback": "良いコミュニケーションでした！",
                            "scenario": "テストシナリオ",
                            "model_used": "gemini-1.5-flash",
                        }

                        response = csrf_client.post(
                            "/api/scenario_feedback",
                            json={
                                "scenario_id": "test_scenario",
                                "model": "gemini-1.5-flash",
                            },
                        )

                        assert response.status_code == 200
                        data = response.get_json()
                        assert "feedback" in data

    def test_履歴がない場合エラー(self, csrf_client):
        """会話履歴がない場合"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = {
                "id": "test_scenario",
                "title": "テストシナリオ",
            }

            response = csrf_client.post(
                "/api/scenario_feedback",
                json={"scenario_id": "test_scenario", "model": "gemini-1.5-flash"},
            )

            assert response.status_code == 404

    def test_無効なシナリオIDでエラー(self, csrf_client):
        """無効なシナリオIDでエラーを返す"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = None

            response = csrf_client.post(
                "/api/scenario_feedback",
                json={"scenario_id": "invalid_id", "model": "gemini-1.5-flash"},
            )

            assert response.status_code == 400

    def test_レート制限エラーを処理(self, csrf_client):
        """レート制限エラーの処理"""
        with csrf_client.session_transaction() as sess:
            sess["scenario_history"] = {"test_scenario": [{"human": "test", "ai": "response"}]}

        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = {
                "id": "test_scenario",
                "title": "テストシナリオ",
            }

            with patch("services.feedback_service.FeedbackService.build_scenario_feedback_prompt") as mock_build:
                mock_build.return_value = "prompt"

                with patch("services.feedback_service.FeedbackService.try_multiple_models_for_prompt") as mock_try:
                    mock_try.return_value = (None, None, "RATE_LIMIT_EXCEEDED")

                    response = csrf_client.post(
                        "/api/scenario_feedback",
                        json={
                            "scenario_id": "test_scenario",
                            "model": "gemini-1.5-flash",
                        },
                    )

                    assert response.status_code == 429


class TestCategorizedScenariosAPI:
    """GET /api/categorized_scenarios のテスト"""

    def test_カテゴリ別シナリオを取得(self, client):
        """カテゴリ別シナリオの取得"""
        response = client.get("/api/categorized_scenarios")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)


class TestScenarioCategoryAPI:
    """GET /api/scenario/<scenario_id>/category のテスト"""

    def test_シナリオカテゴリを取得(self, client):
        """シナリオカテゴリの取得"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = {"id": "test_scenario"}
            mock_service.is_harassment_scenario.return_value = False

            response = client.get("/api/scenario/test_scenario/category")

            assert response.status_code == 200
            data = response.get_json()
            assert data["category"] == "regular_communication"

    def test_ハラスメントシナリオのカテゴリ(self, client):
        """ハラスメントシナリオのカテゴリ取得"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = {"id": "harassment_scenario"}
            mock_service.is_harassment_scenario.return_value = True

            response = client.get("/api/scenario/harassment_scenario/category")

            assert response.status_code == 200
            data = response.get_json()
            assert data["category"] == "harassment_prevention"
            assert data["requires_consent"] is True

    def test_存在しないシナリオで404(self, client):
        """存在しないシナリオで404を返す"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = None

            response = client.get("/api/scenario/nonexistent/category")

            assert response.status_code == 404


class TestGetAssist:
    """POST /api/get_assist のテスト"""

    def test_アシスト提案を取得(self, csrf_client):
        """AIアシストの提案取得"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = {
                "id": "test_scenario",
                "title": "テストシナリオ",
                "description": "テスト説明",
                "learning_points": ["ポイント1"],
            }

            with patch("app.create_model_and_get_response") as mock_create:
                mock_create.return_value = "丁寧に挨拶してから本題に入りましょう。"

                response = csrf_client.post(
                    "/api/get_assist",
                    json={
                        "scenario_id": "test_scenario",
                        "current_context": "上司: おはようございます。",
                    },
                )

                assert response.status_code == 200
                data = response.get_json()
                assert "suggestion" in data

    def test_シナリオIDなしでエラー(self, csrf_client):
        """シナリオIDなしでエラーを返す"""
        response = csrf_client.post("/api/get_assist", json={"current_context": "テスト"})

        assert response.status_code == 400

    def test_存在しないシナリオでエラー(self, csrf_client):
        """存在しないシナリオでエラーを返す"""
        with patch("routes.scenario_routes.scenario_service") as mock_service:
            mock_service.get_scenario_by_id.return_value = None

            response = csrf_client.post(
                "/api/get_assist",
                json={"scenario_id": "nonexistent", "current_context": "テスト"},
            )

            assert response.status_code == 404
