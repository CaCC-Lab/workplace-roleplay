"""
国際化（i18n）設定モジュール
Flask-Babelを使用した多言語対応の基盤を提供
"""
from typing import Optional

from flask import Flask, g, request
from flask_babel import Babel, gettext as _, lazy_gettext as _l, ngettext

# グローバルBabelインスタンス
babel = Babel()

# サポートされる言語
SUPPORTED_LANGUAGES = ["ja", "en"]
DEFAULT_LANGUAGE = "ja"


def get_locale() -> str:
    """
    現在のリクエストのロケールを取得

    優先順位:
    1. URLパラメータ (?lang=en)
    2. セッションに保存された言語
    3. Accept-Languageヘッダー
    4. デフォルト言語

    Returns:
        str: ロケール文字列 (例: 'ja', 'en')
    """
    # URLパラメータをチェック
    lang = request.args.get("lang")
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang

    # セッションをチェック
    if hasattr(g, "language"):
        return g.language

    # Accept-Languageヘッダーから最適な言語を選択
    return request.accept_languages.best_match(SUPPORTED_LANGUAGES, default=DEFAULT_LANGUAGE)


def get_timezone() -> str:
    """
    現在のユーザーのタイムゾーンを取得

    Returns:
        str: タイムゾーン文字列 (例: 'Asia/Tokyo')
    """
    # 将来的にユーザー設定から取得可能
    return "Asia/Tokyo"


def init_i18n(app: Flask) -> Babel:
    """
    国際化機能を初期化

    Args:
        app: Flaskアプリケーション

    Returns:
        Babel: 初期化されたBabelインスタンス
    """
    # Babel設定
    app.config.setdefault("BABEL_DEFAULT_LOCALE", DEFAULT_LANGUAGE)
    app.config.setdefault("BABEL_DEFAULT_TIMEZONE", "Asia/Tokyo")
    app.config.setdefault("BABEL_TRANSLATION_DIRECTORIES", "translations")

    # Babelを初期化
    babel.init_app(app, locale_selector=get_locale)

    # コンテキストプロセッサでテンプレートにヘルパー関数を追加
    @app.context_processor
    def inject_i18n():
        return {
            "_": _,
            "_l": _l,
            "ngettext": ngettext,
            "current_language": get_locale(),
            "supported_languages": SUPPORTED_LANGUAGES,
        }

    return babel


# 翻訳済みメッセージの定義
# 将来的にはPOファイルで管理するが、現時点では辞書で管理
MESSAGES = {
    # 一般的なメッセージ
    "welcome": {
        "ja": "ようこそ！",
        "en": "Welcome!",
    },
    "loading": {
        "ja": "読み込み中...",
        "en": "Loading...",
    },
    "error_occurred": {
        "ja": "エラーが発生しました",
        "en": "An error occurred",
    },
    "success": {
        "ja": "成功しました",
        "en": "Success",
    },
    # 入力検証メッセージ
    "message_required": {
        "ja": "メッセージを入力してください。",
        "en": "Please enter a message.",
    },
    "message_too_long": {
        "ja": "メッセージは{max_length}文字以内で入力してください。",
        "en": "Message must be {max_length} characters or less.",
    },
    "inappropriate_content": {
        "ja": "不適切な表現が含まれています。",
        "en": "Inappropriate content detected.",
    },
    # チャット関連
    "chat_started": {
        "ja": "チャットを開始しました",
        "en": "Chat started",
    },
    "history_cleared": {
        "ja": "履歴をクリアしました",
        "en": "History cleared",
    },
    "no_conversation_yet": {
        "ja": "まだ会話がありません。",
        "en": "No conversation yet.",
    },
    # シナリオ関連
    "scenario_not_found": {
        "ja": "シナリオが見つかりません。",
        "en": "Scenario not found.",
    },
    "start_scenario": {
        "ja": "シナリオを始めてみましょう！",
        "en": "Let's start the scenario!",
    },
    # フィードバック関連
    "feedback_generated": {
        "ja": "フィードバックを生成しました",
        "en": "Feedback generated",
    },
    "rate_limit_exceeded": {
        "ja": "リクエスト制限を超えました。しばらくお待ちください。",
        "en": "Rate limit exceeded. Please wait a moment.",
    },
    # エラーメッセージ
    "csrf_token_invalid": {
        "ja": "セキュリティトークンが無効です。ページを再読み込みしてください。",
        "en": "Security token is invalid. Please reload the page.",
    },
    "internal_error": {
        "ja": "内部エラーが発生しました。",
        "en": "An internal error occurred.",
    },
}


def translate(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """
    メッセージを翻訳

    Args:
        key: メッセージキー
        lang: 言語コード（省略時は現在のロケール）
        **kwargs: フォーマット用のパラメータ

    Returns:
        str: 翻訳されたメッセージ
    """
    if lang is None:
        try:
            lang = get_locale()
        except RuntimeError:
            # リクエストコンテキスト外の場合
            lang = DEFAULT_LANGUAGE

    message = MESSAGES.get(key, {}).get(lang)

    if message is None:
        # フォールバック: 日本語 -> キー
        message = MESSAGES.get(key, {}).get(DEFAULT_LANGUAGE, key)

    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError:
            pass

    return message


# 短縮関数
t = translate


def get_error_message(error_code: str, lang: Optional[str] = None) -> str:
    """
    エラーコードから翻訳されたエラーメッセージを取得

    Args:
        error_code: エラーコード
        lang: 言語コード

    Returns:
        str: 翻訳されたエラーメッセージ
    """
    error_key_map = {
        "CSRF_TOKEN_INVALID": "csrf_token_invalid",
        "CSRF_TOKEN_MISSING": "csrf_token_invalid",
        "RATE_LIMIT_EXCEEDED": "rate_limit_exceeded",
        "INTERNAL_ERROR": "internal_error",
        "VALIDATION_ERROR": "message_required",
    }

    message_key = error_key_map.get(error_code, "internal_error")
    return translate(message_key, lang)
