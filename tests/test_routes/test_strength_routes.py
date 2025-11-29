"""
Strength routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestStrengthAnalysisPage:
    """GET /strength_analysis のテスト"""

    def test_強み分析ページを表示(self, client):
        """強み分析ページの表示"""
        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = True

            response = client.get("/strength_analysis")

            assert response.status_code == 200

    def test_機能無効時は無効ページを表示(self, client):
        """機能無効時は無効化ページを表示"""
        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = False

            response = client.get("/strength_analysis")

            assert response.status_code == 200
            # 機能が無効化されていることを示すメッセージ


class TestAnalyzeStrengths:
    """POST /api/strength_analysis のテスト"""

    def test_チャット履歴から強み分析(self, csrf_client):
        """チャット履歴から強み分析を実行"""
        with csrf_client.session_transaction() as sess:
            sess["chat_history"] = [
                {"human": "こんにちは", "ai": "こんにちは！"},
                {"human": "報告があります", "ai": "はい、お聞きします。"},
            ]

        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = True

            with patch("routes.strength_routes.analyze_user_strengths") as mock_analyze:
                mock_analyze.return_value = {
                    "empathy": 75,
                    "clarity": 80,
                    "active_listening": 70,
                    "adaptability": 65,
                    "positivity": 85,
                    "professionalism": 78,
                }

                with patch(
                    "routes.strength_routes.generate_encouragement_messages"
                ) as mock_messages:
                    mock_messages.return_value = ["素晴らしい結果です！"]

                    with patch("routes.strength_routes.get_top_strengths") as mock_top:
                        mock_top.return_value = [
                            {"name": "ポジティブさ", "score": 85}
                        ]

                        response = csrf_client.post(
                            "/api/strength_analysis", json={"type": "chat"}
                        )

                        assert response.status_code == 200
                        data = response.get_json()
                        assert "scores" in data
                        assert "messages" in data

    def test_シナリオ履歴から強み分析(self, csrf_client):
        """シナリオ履歴から強み分析を実行"""
        with csrf_client.session_transaction() as sess:
            sess["scenario_history"] = {
                "scenario1": [
                    {"human": "お疲れ様です", "ai": "お疲れ様です！"},
                ]
            }

        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = True

            with patch("routes.strength_routes.analyze_user_strengths") as mock_analyze:
                mock_analyze.return_value = {
                    "empathy": 75,
                    "clarity": 80,
                    "active_listening": 70,
                    "adaptability": 65,
                    "positivity": 85,
                    "professionalism": 78,
                }

                with patch(
                    "routes.strength_routes.generate_encouragement_messages"
                ) as mock_messages:
                    mock_messages.return_value = ["素晴らしい！"]

                    with patch("routes.strength_routes.get_top_strengths") as mock_top:
                        mock_top.return_value = [{"name": "共感力", "score": 75}]

                        response = csrf_client.post(
                            "/api/strength_analysis",
                            json={"type": "scenario", "scenario_id": "scenario1"},
                        )

                        assert response.status_code == 200

    def test_全シナリオ履歴から強み分析(self, csrf_client):
        """全シナリオ履歴から強み分析を実行"""
        with csrf_client.session_transaction() as sess:
            sess["scenario_history"] = {
                "scenario1": [{"human": "test1", "ai": "response1"}],
                "scenario2": [{"human": "test2", "ai": "response2"}],
            }

        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = True

            with patch("routes.strength_routes.analyze_user_strengths") as mock_analyze:
                mock_analyze.return_value = {
                    "empathy": 70,
                    "clarity": 70,
                    "active_listening": 70,
                    "adaptability": 70,
                    "positivity": 70,
                    "professionalism": 70,
                }

                with patch(
                    "routes.strength_routes.generate_encouragement_messages"
                ) as mock_messages:
                    mock_messages.return_value = ["良い結果です！"]

                    with patch("routes.strength_routes.get_top_strengths") as mock_top:
                        mock_top.return_value = [{"name": "明確さ", "score": 70}]

                        response = csrf_client.post(
                            "/api/strength_analysis",
                            json={"type": "scenario", "scenario_id": "all"},
                        )

                        assert response.status_code == 200

    def test_履歴がない場合デフォルト値を返す(self, csrf_client):
        """履歴がない場合はデフォルト値を返す"""
        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = True

            response = csrf_client.post(
                "/api/strength_analysis", json={"type": "chat"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert "scores" in data
            # デフォルト値が50
            assert all(score == 50 for score in data["scores"].values())

    def test_機能無効時は403を返す(self, csrf_client):
        """機能無効時は403を返す"""
        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = False

            response = csrf_client.post(
                "/api/strength_analysis", json={"type": "chat"}
            )

            assert response.status_code == 403

    def test_シナリオIDなしでシナリオタイプを指定するとエラー(self, csrf_client):
        """シナリオタイプでシナリオIDなしはエラー"""
        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = True

            response = csrf_client.post(
                "/api/strength_analysis", json={"type": "scenario"}
            )

            assert response.status_code == 400

    def test_不明なセッションタイプでエラー(self, csrf_client):
        """不明なセッションタイプでエラー"""
        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = True

            response = csrf_client.post(
                "/api/strength_analysis", json={"type": "unknown"}
            )

            assert response.status_code == 400

    def test_無効なJSONでエラー(self, csrf_client):
        """無効なJSONでエラー"""
        with patch("routes.strength_routes.is_strength_analysis_enabled") as mock_enabled:
            mock_enabled.return_value = True

            response = csrf_client.post(
                "/api/strength_analysis",
                data="invalid",
                content_type="application/json",
            )

            # 無効なJSONは400または500を返す
            assert response.status_code in [400, 500]


class TestUpdateFeedbackWithStrengthAnalysis:
    """update_feedback_with_strength_analysis関数のテスト"""

    def test_チャットフィードバックに強み分析を追加(self, app):
        """チャットフィードバックに強み分析を追加"""
        from routes.strength_routes import update_feedback_with_strength_analysis

        with app.test_request_context():
            from flask import session

            session["chat_history"] = [
                {"human": "こんにちは", "ai": "こんにちは！"}
            ]

            with patch("routes.strength_routes.analyze_user_strengths") as mock_analyze:
                mock_analyze.return_value = {
                    "empathy": 80,
                    "clarity": 75,
                    "active_listening": 70,
                    "adaptability": 65,
                    "positivity": 85,
                    "professionalism": 78,
                }

                with patch("routes.strength_routes.get_top_strengths") as mock_top:
                    mock_top.return_value = [
                        {"name": "ポジティブさ", "score": 85},
                        {"name": "共感力", "score": 80},
                        {"name": "プロ意識", "score": 78},
                    ]

                    feedback = {"feedback": "良いコミュニケーションでした！"}
                    result = update_feedback_with_strength_analysis(
                        feedback, "chat"
                    )

                    assert "strength_analysis" in result
                    assert "scores" in result["strength_analysis"]
                    assert "top_strengths" in result["strength_analysis"]

    def test_シナリオフィードバックに強み分析を追加(self, app):
        """シナリオフィードバックに強み分析を追加"""
        from routes.strength_routes import update_feedback_with_strength_analysis

        with app.test_request_context():
            from flask import session

            session["scenario_history"] = {
                "scenario1": [{"human": "test", "ai": "response"}]
            }

            with patch("routes.strength_routes.analyze_user_strengths") as mock_analyze:
                mock_analyze.return_value = {"empathy": 70}

                with patch("routes.strength_routes.get_top_strengths") as mock_top:
                    mock_top.return_value = [{"name": "共感力", "score": 70}]

                    feedback = {"feedback": "良い練習でした！"}
                    result = update_feedback_with_strength_analysis(
                        feedback, "scenario", "scenario1"
                    )

                    assert "strength_analysis" in result

    def test_履歴がない場合は強み分析を追加しない(self, app):
        """履歴がない場合は強み分析を追加しない"""
        from routes.strength_routes import update_feedback_with_strength_analysis

        with app.test_request_context():
            feedback = {"feedback": "テスト"}
            result = update_feedback_with_strength_analysis(feedback, "chat")

            # 強み分析は追加されない
            assert "strength_analysis" not in result

    def test_例外が発生しても元のフィードバックを返す(self, app):
        """例外が発生しても元のフィードバックを返す"""
        from routes.strength_routes import update_feedback_with_strength_analysis

        with app.test_request_context():
            from flask import session

            session["chat_history"] = [{"human": "test", "ai": "response"}]

            with patch("routes.strength_routes.analyze_user_strengths") as mock_analyze:
                mock_analyze.side_effect = Exception("Analysis error")

                feedback = {"feedback": "テスト"}
                result = update_feedback_with_strength_analysis(feedback, "chat")

                # 元のフィードバックがそのまま返される
                assert result == feedback
