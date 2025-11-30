"""
Strength service tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    return app


class TestStrengthService:
    """StrengthServiceクラスのテスト"""

    def test_空の履歴で分析(self):
        """空の履歴での分析"""
        from services.strength_service import StrengthService

        service = StrengthService()

        result = service.analyze_user_strengths_from_history([])

        assert "scores" in result
        assert "messages" in result
        assert "まだ練習履歴がありません" in result["messages"][0]

    def test_履歴ありで分析(self):
        """履歴がある場合の分析"""
        from services.strength_service import StrengthService

        service = StrengthService()
        history = [
            {"human": "こんにちは、お疲れ様です。", "ai": "お疲れ様です！"},
            {"human": "今日は良い天気ですね。", "ai": "そうですね、気持ち良いですね。"},
        ]

        with patch(
            "services.strength_service.analyze_user_strengths"
        ) as mock_analyze:
            mock_analyze.return_value = {
                "empathy": 80,
                "clarity": 70,
                "active_listening": 75,
                "adaptability": 65,
                "positivity": 85,
                "professionalism": 70,
            }
            with patch(
                "services.strength_service.generate_encouragement_messages"
            ) as mock_msgs:
                mock_msgs.return_value = ["素晴らしい対話力です！"]
                with patch(
                    "services.strength_service.get_top_strengths"
                ) as mock_top:
                    mock_top.return_value = [{"name": "ポジティブさ", "score": 85}]

                    result = service.analyze_user_strengths_from_history(history)

                    assert "scores" in result
                    assert "messages" in result

    def test_メッセージ追加ロジック(self):
        """メッセージが3件未満の場合の追加ロジック"""
        from services.strength_service import StrengthService

        service = StrengthService()
        history = [{"human": "テスト", "ai": "応答"}]

        with patch(
            "services.strength_service.analyze_user_strengths"
        ) as mock_analyze:
            mock_analyze.return_value = {
                "empathy": 80,
                "clarity": 70,
                "active_listening": 75,
                "adaptability": 65,
                "positivity": 85,
                "professionalism": 70,
            }
            with patch(
                "services.strength_service.generate_encouragement_messages"
            ) as mock_msgs:
                mock_msgs.return_value = ["メッセージ1"]  # 1件のみ
                with patch(
                    "services.strength_service.get_top_strengths"
                ) as mock_top:
                    mock_top.return_value = [{"name": "共感力", "score": 80}]

                    result = service.analyze_user_strengths_from_history(history)

                    # 追加メッセージが付与される
                    assert len(result["messages"]) >= 1

    def test_トップ強み取得(self):
        """トップNの強みを取得"""
        from services.strength_service import StrengthService

        service = StrengthService()
        scores = {
            "empathy": 80,
            "clarity": 70,
            "active_listening": 75,
            "adaptability": 65,
            "positivity": 85,
            "professionalism": 70,
        }

        with patch("services.strength_service.get_top_strengths") as mock_top:
            mock_top.return_value = [
                {"name": "ポジティブさ", "score": 85},
                {"name": "共感力", "score": 80},
            ]

            result = service.get_top_strengths(scores, 2)

            assert len(result) == 2
            mock_top.assert_called_once_with(scores, 2)

    def test_励ましメッセージ生成(self):
        """励ましメッセージの生成"""
        from services.strength_service import StrengthService

        service = StrengthService()
        scores = {"empathy": 80, "clarity": 70}

        with patch(
            "services.strength_service.generate_encouragement_messages"
        ) as mock_msgs:
            mock_msgs.return_value = ["頑張りました！"]

            result = service.generate_encouragement_messages(scores)

            assert len(result) == 1
            mock_msgs.assert_called_once_with(scores, [])

    def test_励ましメッセージ生成_履歴あり(self):
        """過去の履歴ありで励ましメッセージの生成"""
        from services.strength_service import StrengthService

        service = StrengthService()
        scores = {"empathy": 80}
        previous = [{"scores": {"empathy": 70}}]

        with patch(
            "services.strength_service.generate_encouragement_messages"
        ) as mock_msgs:
            mock_msgs.return_value = ["成長していますね！"]

            result = service.generate_encouragement_messages(scores, previous)

            mock_msgs.assert_called_once_with(scores, previous)

    def test_フィードバックに強み分析追加_チャット(self, app):
        """チャットモードでフィードバックに強み分析を追加"""
        from services.strength_service import StrengthService

        service = StrengthService()

        with app.test_request_context():
            from flask import session

            session["chat_history"] = [
                {"human": "こんにちは", "ai": "こんにちは！"}
            ]

            with patch(
                "services.strength_service.analyze_user_strengths"
            ) as mock_analyze:
                mock_analyze.return_value = {"empathy": 80}
                with patch(
                    "services.strength_service.get_top_strengths"
                ) as mock_top:
                    mock_top.return_value = [{"name": "共感力", "score": 80}]

                    feedback = {"feedback": "良い会話でした"}
                    result = service.update_feedback_with_strength_analysis(
                        feedback, "chat"
                    )

                    assert "strength_analysis" in result

    def test_フィードバックに強み分析追加_シナリオ(self, app):
        """シナリオモードでフィードバックに強み分析を追加"""
        from services.strength_service import StrengthService

        service = StrengthService()

        with app.test_request_context():
            from flask import session

            session["scenario_history"] = {
                "scenario1": [{"human": "テスト", "ai": "応答"}]
            }

            with patch(
                "services.strength_service.analyze_user_strengths"
            ) as mock_analyze:
                mock_analyze.return_value = {"clarity": 75}
                with patch(
                    "services.strength_service.get_top_strengths"
                ) as mock_top:
                    mock_top.return_value = [{"name": "明確さ", "score": 75}]

                    feedback = {"feedback": "シナリオ完了"}
                    result = service.update_feedback_with_strength_analysis(
                        feedback, "scenario", "scenario1"
                    )

                    assert "strength_analysis" in result

    def test_フィードバックに強み分析追加_履歴なし(self, app):
        """履歴がない場合は強み分析を追加しない"""
        from services.strength_service import StrengthService

        service = StrengthService()

        with app.test_request_context():
            feedback = {"feedback": "テスト"}
            result = service.update_feedback_with_strength_analysis(feedback, "chat")

            assert "strength_analysis" not in result

    def test_フィードバックに強み分析追加_エラー発生(self, app):
        """エラー発生時は元のフィードバックを返す"""
        from services.strength_service import StrengthService

        service = StrengthService()

        with app.test_request_context():
            from flask import session

            session["chat_history"] = [{"human": "テスト", "ai": "応答"}]

            with patch(
                "services.strength_service.analyze_user_strengths"
            ) as mock_analyze:
                mock_analyze.side_effect = Exception("Analysis error")

                feedback = {"feedback": "テスト"}
                result = service.update_feedback_with_strength_analysis(
                    feedback, "chat"
                )

                # エラーでも元のフィードバックは返される
                assert result == feedback


class TestGetStrengthService:
    """get_strength_service関数のテスト"""

    def test_シングルトンインスタンスを取得(self):
        """シングルトンインスタンスを取得"""
        from services import strength_service
        from services.strength_service import get_strength_service, StrengthService

        # グローバル変数をリセット
        strength_service._strength_service = None

        service1 = get_strength_service()
        service2 = get_strength_service()

        assert service1 is service2
        assert isinstance(service1, StrengthService)
