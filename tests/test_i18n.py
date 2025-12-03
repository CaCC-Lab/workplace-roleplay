"""
国際化（i18n）機能のテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.i18n import (
    MESSAGES,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    translate,
    t,
    get_error_message,
)


class TestTranslate:
    """translate関数のテスト"""

    def test_translate_japanese(self):
        """日本語翻訳のテスト"""
        result = translate("welcome", "ja")
        assert result == "ようこそ！"

    def test_translate_english(self):
        """英語翻訳のテスト"""
        result = translate("welcome", "en")
        assert result == "Welcome!"

    def test_translate_with_fallback(self):
        """フォールバックのテスト"""
        result = translate("nonexistent_key", "ja")
        assert result == "nonexistent_key"

    def test_translate_with_params(self):
        """パラメータ付き翻訳のテスト"""
        result = translate("message_too_long", "ja", max_length=1000)
        assert "1000" in result
        assert "文字" in result

    def test_translate_english_with_params(self):
        """英語でのパラメータ付き翻訳のテスト"""
        result = translate("message_too_long", "en", max_length=1000)
        assert "1000" in result
        assert "characters" in result

    def test_shortcut_function(self):
        """ショートカット関数のテスト"""
        result = t("welcome", "ja")
        assert result == "ようこそ！"


class TestGetErrorMessage:
    """get_error_message関数のテスト"""

    def test_csrf_error_japanese(self):
        """CSRFエラーの日本語メッセージ"""
        result = get_error_message("CSRF_TOKEN_INVALID", "ja")
        assert "セキュリティトークン" in result

    def test_csrf_error_english(self):
        """CSRFエラーの英語メッセージ"""
        result = get_error_message("CSRF_TOKEN_INVALID", "en")
        assert "Security token" in result

    def test_rate_limit_error(self):
        """レート制限エラーのメッセージ"""
        result = get_error_message("RATE_LIMIT_EXCEEDED", "ja")
        assert "リクエスト制限" in result

    def test_unknown_error_code(self):
        """不明なエラーコードのフォールバック"""
        result = get_error_message("UNKNOWN_ERROR", "ja")
        assert "内部エラー" in result


class TestMessages:
    """メッセージ定義のテスト"""

    def test_all_messages_have_both_languages(self):
        """全メッセージが両言語で定義されているか"""
        for key, translations in MESSAGES.items():
            assert "ja" in translations, f"'{key}' missing Japanese translation"
            assert "en" in translations, f"'{key}' missing English translation"

    def test_supported_languages(self):
        """サポート言語の確認"""
        assert "ja" in SUPPORTED_LANGUAGES
        assert "en" in SUPPORTED_LANGUAGES

    def test_default_language(self):
        """デフォルト言語の確認"""
        assert DEFAULT_LANGUAGE == "ja"


class TestMessageContent:
    """メッセージ内容のテスト"""

    def test_validation_messages(self):
        """入力検証メッセージの存在確認"""
        assert "message_required" in MESSAGES
        assert "message_too_long" in MESSAGES
        assert "inappropriate_content" in MESSAGES

    def test_chat_messages(self):
        """チャット関連メッセージの存在確認"""
        assert "chat_started" in MESSAGES
        assert "history_cleared" in MESSAGES
        assert "no_conversation_yet" in MESSAGES

    def test_error_messages(self):
        """エラーメッセージの存在確認"""
        assert "csrf_token_invalid" in MESSAGES
        assert "internal_error" in MESSAGES
        assert "rate_limit_exceeded" in MESSAGES
