"""
Session utilities tests for improved coverage.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """テスト用クライアント"""
    return app.test_client()


class TestInitializeSessionHistory:
    """initialize_session_history関数のテスト"""

    def test_新規セッション履歴をリストで初期化(self, app):
        """サブキーなしでリストとして初期化"""
        from utils.session_utils import initialize_session_history

        with app.test_request_context():
            from flask import session

            initialize_session_history("chat_history")

            assert "chat_history" in session
            assert session["chat_history"] == []

    def test_新規セッション履歴を辞書で初期化(self, app):
        """サブキーありで辞書として初期化"""
        from utils.session_utils import initialize_session_history

        with app.test_request_context():
            from flask import session

            initialize_session_history("scenario_history", "scenario1")

            assert "scenario_history" in session
            assert "scenario1" in session["scenario_history"]
            assert session["scenario_history"]["scenario1"] == []

    def test_既存セッションにサブキーを追加(self, app):
        """既存の辞書セッションにサブキーを追加"""
        from utils.session_utils import initialize_session_history

        with app.test_request_context():
            from flask import session

            session["scenario_history"] = {"scenario1": [{"test": "data"}]}
            initialize_session_history("scenario_history", "scenario2")

            assert "scenario1" in session["scenario_history"]
            assert "scenario2" in session["scenario_history"]


class TestAddToSessionHistory:
    """add_to_session_history関数のテスト"""

    def test_リスト履歴にエントリを追加(self, app):
        """リスト形式の履歴にエントリを追加"""
        from utils.session_utils import add_to_session_history

        with app.test_request_context():
            from flask import session

            entry = {"human": "こんにちは", "ai": "こんにちは！"}
            add_to_session_history("chat_history", entry)

            assert len(session["chat_history"]) == 1
            assert "timestamp" in session["chat_history"][0]

    def test_辞書履歴にエントリを追加(self, app):
        """辞書形式の履歴にエントリを追加"""
        from utils.session_utils import add_to_session_history

        with app.test_request_context():
            from flask import session

            entry = {"human": "テスト", "ai": "応答"}
            add_to_session_history("scenario_history", entry, "scenario1")

            assert len(session["scenario_history"]["scenario1"]) == 1

    def test_タイムスタンプ付きエントリ(self, app):
        """既にタイムスタンプがあるエントリ"""
        from utils.session_utils import add_to_session_history

        with app.test_request_context():
            from flask import session

            timestamp = "2024-01-01T10:00:00"
            entry = {"human": "テスト", "ai": "応答", "timestamp": timestamp}
            add_to_session_history("chat_history", entry)

            assert session["chat_history"][0]["timestamp"] == timestamp


class TestClearSessionHistory:
    """clear_session_history関数のテスト"""

    def test_リスト履歴をクリア(self, app):
        """リスト形式の履歴をクリア"""
        from utils.session_utils import clear_session_history

        with app.test_request_context():
            from flask import session

            session["chat_history"] = [{"test": "data"}]
            clear_session_history("chat_history")

            assert session["chat_history"] == []

    def test_辞書履歴をクリア(self, app):
        """辞書形式の履歴をクリア"""
        from utils.session_utils import clear_session_history

        with app.test_request_context():
            from flask import session

            session["scenario_history"] = {"scenario1": [{"test": "data"}]}
            clear_session_history("scenario_history")

            assert session["scenario_history"] == {}

    def test_サブキー指定でクリア(self, app):
        """サブキーを指定してクリア"""
        from utils.session_utils import clear_session_history

        with app.test_request_context():
            from flask import session

            session["scenario_history"] = {
                "scenario1": [{"test": "data"}],
                "scenario2": [{"test": "data2"}],
            }
            clear_session_history("scenario_history", "scenario1")

            assert session["scenario_history"]["scenario1"] == []
            assert len(session["scenario_history"]["scenario2"]) == 1

    def test_存在しないキーのクリア(self, app):
        """存在しないキーをクリアしてもエラーにならない"""
        from utils.session_utils import clear_session_history

        with app.test_request_context():
            # エラーが発生しないことを確認
            clear_session_history("nonexistent_key")


class TestSetSessionStartTime:
    """set_session_start_time関数のテスト"""

    def test_開始時間を設定(self, app):
        """開始時間を設定"""
        from utils.session_utils import set_session_start_time

        with app.test_request_context():
            from flask import session

            set_session_start_time("chat")

            assert "chat_settings" in session
            assert "start_time" in session["chat_settings"]

    def test_サブキー付きで開始時間を設定(self, app):
        """サブキー付きで開始時間を設定"""
        from utils.session_utils import set_session_start_time

        with app.test_request_context():
            from flask import session

            set_session_start_time("scenario", "scenario1")

            assert "scenario_settings" in session
            assert "scenario1" in session["scenario_settings"]
            assert "start_time" in session["scenario_settings"]["scenario1"]

    def test_既存設定を更新(self, app):
        """既存の設定を更新"""
        from utils.session_utils import set_session_start_time

        with app.test_request_context():
            from flask import session

            session["chat_settings"] = {"start_time": "old_time"}
            set_session_start_time("chat")

            assert session["chat_settings"]["start_time"] != "old_time"


class TestGetSessionDuration:
    """get_session_duration関数のテスト"""

    def test_継続時間を取得(self, app):
        """継続時間を取得"""
        from utils.session_utils import get_session_duration

        with app.test_request_context():
            from flask import session

            start_time = (datetime.now() - timedelta(seconds=60)).isoformat()
            session["chat_settings"] = {"start_time": start_time}

            duration = get_session_duration("chat")

            assert duration is not None
            assert duration >= 60

    def test_サブキー付きで継続時間を取得(self, app):
        """サブキー付きで継続時間を取得"""
        from utils.session_utils import get_session_duration

        with app.test_request_context():
            from flask import session

            start_time = (datetime.now() - timedelta(seconds=30)).isoformat()
            session["scenario_settings"] = {"scenario1": {"start_time": start_time}}

            duration = get_session_duration("scenario", "scenario1")

            assert duration is not None
            assert duration >= 30

    def test_設定がない場合はNone(self, app):
        """設定がない場合はNoneを返す"""
        from utils.session_utils import get_session_duration

        with app.test_request_context():
            duration = get_session_duration("nonexistent")

            assert duration is None

    def test_開始時間がない場合はNone(self, app):
        """開始時間がない場合はNoneを返す"""
        from utils.session_utils import get_session_duration

        with app.test_request_context():
            from flask import session

            session["chat_settings"] = {"other": "data"}

            duration = get_session_duration("chat")

            assert duration is None

    def test_サブキーがない場合はNone(self, app):
        """サブキーがない場合はNoneを返す"""
        from utils.session_utils import get_session_duration

        with app.test_request_context():
            from flask import session

            session["scenario_settings"] = {"other_scenario": {"start_time": "test"}}

            duration = get_session_duration("scenario", "scenario1")

            assert duration is None


class TestGetConversationMemory:
    """get_conversation_memory関数のテスト"""

    def test_リスト形式の履歴を取得(self, app):
        """リスト形式の履歴を取得"""
        from utils.session_utils import get_conversation_memory

        with app.test_request_context():
            from flask import session

            session["chat_history"] = [
                {"human": "1", "ai": "1"},
                {"human": "2", "ai": "2"},
            ]

            memory = get_conversation_memory("chat")

            assert len(memory) == 2

    def test_辞書形式の履歴を取得(self, app):
        """辞書形式の履歴を結合して取得"""
        from utils.session_utils import get_conversation_memory

        with app.test_request_context():
            from flask import session

            session["scenario_history"] = {
                "scenario1": [{"human": "1", "ai": "1"}],
                "scenario2": [{"human": "2", "ai": "2"}],
            }

            memory = get_conversation_memory("scenario")

            assert len(memory) == 2

    def test_履歴がない場合は空リスト(self, app):
        """履歴がない場合は空リストを返す"""
        from utils.session_utils import get_conversation_memory

        with app.test_request_context():
            memory = get_conversation_memory("nonexistent")

            assert memory == []

    def test_最大メッセージ数制限(self, app):
        """最大メッセージ数を超える場合は最新のみ返す"""
        from utils.session_utils import get_conversation_memory

        with app.test_request_context():
            from flask import session

            session["chat_history"] = [{"id": i} for i in range(100)]

            memory = get_conversation_memory("chat", max_messages=10)

            assert len(memory) == 10
            assert memory[0]["id"] == 90  # 最新の10件
