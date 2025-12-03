"""
ユーティリティ関数のテスト
"""
import pytest
from datetime import datetime, timedelta
from flask import Flask, session

from utils.session_utils import (
    initialize_session_history,
    add_to_session_history,
    clear_session_history,
    set_session_start_time,
    get_session_duration,
    get_conversation_memory,
)
from utils.formatters import escape_for_json, format_datetime, format_duration, format_file_size, truncate_text
from utils.validators import (
    validate_message_content,
    validate_scenario_id,
    validate_model_name,
    validate_voice_name,
    validate_json_data,
    sanitize_input,
)
from utils.constants import DEFAULT_CHAT_MODEL, AVAILABLE_MODELS, AVAILABLE_VOICES


@pytest.fixture
def app():
    """テスト用のFlaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    return app


class TestSessionUtils:
    """セッションユーティリティのテスト"""

    def test_initialize_session_history(self, app):
        """セッション履歴の初期化テスト"""
        with app.test_request_context():
            # リスト形式の初期化
            initialize_session_history("test_history")
            assert "test_history" in session
            assert isinstance(session["test_history"], list)

            # 辞書形式の初期化（サブキー付き）
            initialize_session_history("test_dict", "sub_key")
            assert "test_dict" in session
            assert isinstance(session["test_dict"], dict)
            assert "sub_key" in session["test_dict"]
            assert isinstance(session["test_dict"]["sub_key"], list)

    def test_add_to_session_history(self, app):
        """セッション履歴への追加テスト"""
        with app.test_request_context():
            # リストへの追加
            entry = {"message": "test"}
            add_to_session_history("test_history", entry)

            assert len(session["test_history"]) == 1
            assert session["test_history"][0]["message"] == "test"
            assert "timestamp" in session["test_history"][0]

    def test_clear_session_history(self, app):
        """セッション履歴のクリアテスト"""
        with app.test_request_context():
            # データを追加
            add_to_session_history("test_history", {"message": "test"})
            assert len(session["test_history"]) == 1

            # クリア
            clear_session_history("test_history")
            assert len(session["test_history"]) == 0

    def test_session_duration(self, app):
        """セッション継続時間のテスト"""
        with app.test_request_context():
            # 開始時間を設定
            set_session_start_time("test_session")

            # 継続時間を取得（すぐなのでほぼ0秒）
            duration = get_session_duration("test_session")
            assert duration is not None
            assert duration >= 0
            assert duration < 1  # 1秒未満のはず


class TestFormatters:
    """フォーマッターのテスト"""

    def test_escape_for_json(self):
        """JSON用エスケープのテスト"""
        assert escape_for_json('test"quote') == 'test\\"quote'
        assert escape_for_json("test\nline") == "test\\nline"
        assert escape_for_json("test\\slash") == "test\\\\slash"

    def test_format_datetime(self):
        """日時フォーマットのテスト"""
        # ISO形式の日時
        iso_time = "2024-01-15T14:30:00"
        formatted = format_datetime(iso_time)
        assert formatted == "2024年01月15日 14:30"

        # None の場合
        assert format_datetime(None) == "なし"

        # 無効な形式
        assert format_datetime("invalid") == "invalid"

    def test_format_duration(self):
        """時間フォーマットのテスト"""
        assert format_duration(30) == "30秒"
        assert format_duration(90) == "1分30秒"
        assert format_duration(3600) == "1時間"
        assert format_duration(3660) == "1時間1分"
        assert format_duration(None) == "不明"

    def test_format_file_size(self):
        """ファイルサイズフォーマットのテスト"""
        assert format_file_size(100) == "100.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"

    def test_truncate_text(self):
        """テキスト切り詰めのテスト"""
        long_text = "a" * 150
        truncated = truncate_text(long_text, 100)
        assert len(truncated) == 100
        assert truncated.endswith("...")

        short_text = "short"
        assert truncate_text(short_text, 100) == short_text


class TestValidators:
    """バリデーターのテスト"""

    def test_validate_message_content(self):
        """メッセージ内容の検証テスト"""
        # 正常なメッセージ
        valid, error = validate_message_content("Hello")
        assert valid
        assert error is None

        # 空のメッセージ
        valid, error = validate_message_content("")
        assert not valid
        assert "メッセージが空です" in error

        # HTMLタグを含むメッセージ
        valid, error = validate_message_content("<script>alert()</script>")
        assert not valid
        assert "HTMLタグは使用できません" in error

        # 長すぎるメッセージ
        long_message = "a" * 5000
        valid, error = validate_message_content(long_message)
        assert not valid
        assert "長すぎます" in error

    def test_validate_scenario_id(self):
        """シナリオID検証のテスト"""
        # 正常なID
        valid, error = validate_scenario_id("scenario_123")
        assert valid

        # 無効な文字を含むID
        valid, error = validate_scenario_id("scenario@123")
        assert not valid

    def test_validate_model_name(self):
        """モデル名検証のテスト"""
        # 正常なモデル名
        valid, error = validate_model_name("gemini-1.5-flash")
        assert valid

        # 無効なモデル名
        valid, error = validate_model_name("invalid-model")
        assert not valid

    def test_sanitize_input(self):
        """入力サニタイズのテスト"""
        # 制御文字を含むテキスト
        text_with_control = "test\x00\x1Ftext"
        sanitized = sanitize_input(text_with_control)
        assert "\x00" not in sanitized
        assert "\x1F" not in sanitized

        # 連続する空白
        text_with_spaces = "test    multiple    spaces"
        sanitized = sanitize_input(text_with_spaces)
        assert "    " not in sanitized
        assert sanitized == "test multiple spaces"


class TestConstants:
    """定数のテスト"""

    def test_default_values(self):
        """デフォルト値のテスト"""
        assert DEFAULT_CHAT_MODEL in AVAILABLE_MODELS
        assert isinstance(AVAILABLE_VOICES, list)
        assert len(AVAILABLE_VOICES) > 0

    def test_voice_categories(self):
        """音声カテゴリのテスト"""
        from utils.constants import FEMALE_VOICES, MALE_VOICES, NEUTRAL_VOICES

        # 重複がないことを確認
        all_voices = FEMALE_VOICES + MALE_VOICES + NEUTRAL_VOICES
        assert len(all_voices) == len(set(all_voices))

        # AVAILABLE_VOICESと一致することを確認
        assert set(all_voices) == set(AVAILABLE_VOICES)
