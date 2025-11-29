"""
Journal routes tests for improved coverage.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_feature_flags():
    """学習履歴機能を有効にするフィクスチャ"""
    mock_flags = MagicMock()
    mock_flags.learning_history_enabled = True
    mock_flags.model_selection_enabled = True
    mock_flags.tts_enabled = False
    mock_flags.strength_analysis_enabled = True
    mock_flags.to_dict.return_value = {
        "learning_history": True,
        "model_selection": True,
        "tts": False,
        "strength_analysis": True,
    }
    return mock_flags


class TestViewJournal:
    """GET /journal のテスト"""

    def test_学習履歴ページを表示_空の履歴(self, client, mock_feature_flags):
        """空の履歴で学習履歴ページを表示"""
        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_feature_flags

            response = client.get("/journal")

            assert response.status_code == 200

    def test_学習履歴ページを表示_シナリオ履歴あり(self, client, mock_feature_flags):
        """シナリオ履歴がある場合の学習履歴ページ表示"""
        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_feature_flags

            with client.session_transaction() as sess:
                sess["scenario_history"] = {
                    "scenario1": [
                        {
                            "human": "こんにちは",
                            "ai": "こんにちは！",
                            "timestamp": datetime.now().isoformat(),
                        }
                    ]
                }
                sess["scenario_feedback"] = {
                    "scenario1": {"score": 80, "comment": "良い対応です"}
                }

            response = client.get("/journal")

            assert response.status_code == 200

    def test_学習履歴ページを表示_雑談履歴あり(self, client, mock_feature_flags):
        """雑談履歴がある場合の学習履歴ページ表示"""
        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_feature_flags

            with client.session_transaction() as sess:
                sess["chat_history"] = [
                    {
                        "human": "今日はいい天気ですね",
                        "ai": "そうですね！",
                        "timestamp": datetime.now().isoformat(),
                    }
                ]

            response = client.get("/journal")

            assert response.status_code == 200

    def test_学習履歴ページ_練習時間計算_シナリオ(self, client, mock_feature_flags):
        """シナリオの練習時間計算"""
        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_feature_flags

            start_time = (datetime.now() - timedelta(minutes=30)).isoformat()
            end_time = datetime.now().isoformat()

            with client.session_transaction() as sess:
                sess["scenario_history"] = {
                    "scenario1": [
                        {"human": "テスト", "ai": "応答", "timestamp": end_time}
                    ]
                }
                sess["scenario_settings"] = {"scenario1": {"start_time": start_time}}

            response = client.get("/journal")

            assert response.status_code == 200

    def test_学習履歴ページ_練習時間計算_雑談(self, client, mock_feature_flags):
        """雑談モードの練習時間計算"""
        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_feature_flags

            start_time = (datetime.now() - timedelta(minutes=15)).isoformat()
            end_time = datetime.now().isoformat()

            with client.session_transaction() as sess:
                sess["chat_history"] = [
                    {"human": "テスト", "ai": "応答", "timestamp": end_time}
                ]
                sess["chat_settings"] = {"start_time": start_time}

            response = client.get("/journal")

            assert response.status_code == 200

    def test_学習履歴ページ_練習時間計算_観戦(self, client, mock_feature_flags):
        """観戦モードの練習時間計算"""
        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_feature_flags

            start_time = (datetime.now() - timedelta(minutes=20)).isoformat()
            end_time = datetime.now().isoformat()

            with client.session_transaction() as sess:
                sess["watch_history"] = [
                    {"speaker": "A", "message": "テスト", "timestamp": end_time}
                ]
                sess["watch_settings"] = {"start_time": start_time}

            response = client.get("/journal")

            assert response.status_code == 200

    def test_学習履歴ページ_練習時間1時間以上(self, client, mock_feature_flags):
        """1時間以上の練習時間表示"""
        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_feature_flags

            start_time = (datetime.now() - timedelta(hours=1, minutes=30)).isoformat()
            end_time = datetime.now().isoformat()

            with client.session_transaction() as sess:
                sess["chat_history"] = [
                    {"human": "テスト", "ai": "応答", "timestamp": end_time}
                ]
                sess["chat_settings"] = {"start_time": start_time}

            response = client.get("/journal")

            assert response.status_code == 200

    def test_学習履歴機能無効時は403(self, client):
        """学習履歴機能が無効の場合は403を返す"""
        mock_flags = MagicMock()
        mock_flags.learning_history_enabled = False

        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_flags

            response = client.get("/journal")

            assert response.status_code == 403

    def test_学習履歴ページ_最終アクティビティ比較(self, client, mock_feature_flags):
        """シナリオとチャットの最終アクティビティ比較"""
        with patch("config.feature_flags.get_feature_flags") as mock_get:
            mock_get.return_value = mock_feature_flags

            older_time = (datetime.now() - timedelta(hours=2)).isoformat()
            newer_time = datetime.now().isoformat()

            with client.session_transaction() as sess:
                sess["scenario_history"] = {
                    "scenario1": [
                        {"human": "テスト", "ai": "応答", "timestamp": older_time}
                    ]
                }
                sess["chat_history"] = [
                    {"human": "テスト", "ai": "応答", "timestamp": newer_time}
                ]

            response = client.get("/journal")

            assert response.status_code == 200
