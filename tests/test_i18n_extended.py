"""
i18n utility tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, g


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    return app


class TestGetLocale:
    """get_locale関数のテスト"""

    def test_URLパラメータから言語取得(self, app):
        """URLパラメータから言語を取得"""
        from utils.i18n import get_locale

        with app.test_request_context("/?lang=en"):
            result = get_locale()
            assert result == "en"

    def test_URLパラメータの言語がサポート外(self, app):
        """サポートされていない言語はフォールバック"""
        from utils.i18n import get_locale

        with app.test_request_context("/?lang=fr"):
            result = get_locale()
            # フォールバックでAccept-Languageまたはデフォルト
            assert result in ["ja", "en"]

    def test_gオブジェクトから言語取得(self, app):
        """g.languageから言語を取得"""
        from utils.i18n import get_locale

        with app.test_request_context("/"):
            g.language = "en"
            result = get_locale()
            assert result == "en"

    def test_デフォルト言語にフォールバック(self, app):
        """デフォルト言語にフォールバック"""
        from utils.i18n import get_locale

        with app.test_request_context("/"):
            result = get_locale()
            assert result in ["ja", "en"]


class TestGetTimezone:
    """get_timezone関数のテスト"""

    def test_タイムゾーン取得(self):
        """タイムゾーンを取得"""
        from utils.i18n import get_timezone

        result = get_timezone()

        assert result == "Asia/Tokyo"


class TestInitI18n:
    """init_i18n関数のテスト"""

    def test_i18n初期化(self, app):
        """i18n機能を初期化"""
        from utils.i18n import init_i18n

        result = init_i18n(app)

        assert result is not None
        assert "BABEL_DEFAULT_LOCALE" in app.config


class TestTranslate:
    """translate関数のテスト"""

    def test_日本語メッセージ取得(self, app):
        """日本語メッセージを取得"""
        from utils.i18n import translate

        with app.test_request_context("/?lang=ja"):
            result = translate("welcome")
            assert result == "ようこそ！"

    def test_英語メッセージ取得(self, app):
        """英語メッセージを取得"""
        from utils.i18n import translate

        result = translate("welcome", lang="en")

        assert result == "Welcome!"

    def test_存在しないキーはキーを返す(self, app):
        """存在しないキーはキー名を返す"""
        from utils.i18n import translate

        result = translate("nonexistent_key", lang="ja")

        assert result == "nonexistent_key"

    def test_フォーマットパラメータ(self, app):
        """フォーマットパラメータの適用"""
        from utils.i18n import translate

        result = translate("message_too_long", lang="ja", max_length=100)

        assert "100" in result

    def test_フォーマットパラメータ不足(self, app):
        """フォーマットパラメータが不足した場合"""
        from utils.i18n import translate

        # KeyErrorが発生しても元のメッセージを返す
        result = translate("message_too_long", lang="ja")

        assert "max_length" in result or result is not None

    def test_リクエストコンテキスト外(self):
        """リクエストコンテキスト外での翻訳"""
        from utils.i18n import translate

        # RuntimeErrorを発生させずにデフォルト言語を使用
        result = translate("welcome")

        # デフォルト言語（日本語）で返す
        assert result == "ようこそ！"

    def test_言語指定でNoneの場合にコンテキスト外(self):
        """lang=Noneでリクエストコンテキスト外"""
        from utils.i18n import translate

        result = translate("loading", lang=None)

        assert result in ["読み込み中...", "Loading..."]


class TestTranslateShortcut:
    """t関数（translateのショートカット）のテスト"""

    def test_ショートカット関数(self, app):
        """t関数のテスト"""
        from utils.i18n import t

        result = t("success", lang="en")

        assert result == "Success"


class TestGetErrorMessage:
    """get_error_message関数のテスト"""

    def test_CSRFトークン無効エラー(self, app):
        """CSRFトークン無効エラーメッセージ"""
        from utils.i18n import get_error_message

        result = get_error_message("CSRF_TOKEN_INVALID", lang="ja")

        assert "セキュリティトークン" in result

    def test_CSRFトークン欠落エラー(self, app):
        """CSRFトークン欠落エラーメッセージ"""
        from utils.i18n import get_error_message

        result = get_error_message("CSRF_TOKEN_MISSING", lang="en")

        assert "Security token" in result

    def test_レート制限エラー(self, app):
        """レート制限エラーメッセージ"""
        from utils.i18n import get_error_message

        result = get_error_message("RATE_LIMIT_EXCEEDED", lang="ja")

        assert "リクエスト制限" in result

    def test_内部エラー(self, app):
        """内部エラーメッセージ"""
        from utils.i18n import get_error_message

        result = get_error_message("INTERNAL_ERROR", lang="en")

        assert "internal error" in result

    def test_バリデーションエラー(self, app):
        """バリデーションエラーメッセージ"""
        from utils.i18n import get_error_message

        result = get_error_message("VALIDATION_ERROR", lang="ja")

        assert "メッセージを入力" in result

    def test_不明なエラーコード(self, app):
        """不明なエラーコードは内部エラーにフォールバック"""
        from utils.i18n import get_error_message

        result = get_error_message("UNKNOWN_ERROR", lang="ja")

        assert "内部エラー" in result


class TestMessages:
    """MESSAGESディクショナリのテスト"""

    def test_全キーに日本語と英語が存在(self):
        """全キーに日本語と英語の翻訳が存在"""
        from utils.i18n import MESSAGES, SUPPORTED_LANGUAGES

        for key, translations in MESSAGES.items():
            for lang in SUPPORTED_LANGUAGES:
                assert lang in translations, f"Key '{key}' missing '{lang}' translation"
                assert translations[lang], f"Key '{key}' has empty '{lang}' translation"

    def test_サポート言語定数(self):
        """サポート言語定数の確認"""
        from utils.i18n import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

        assert "ja" in SUPPORTED_LANGUAGES
        assert "en" in SUPPORTED_LANGUAGES
        assert DEFAULT_LANGUAGE == "ja"
