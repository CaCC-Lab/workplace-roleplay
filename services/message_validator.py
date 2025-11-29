"""
メッセージ検証サービス
入力メッセージの検証とサニタイズを担当
"""
import re
from typing import List, Optional, Tuple

from utils.constants import MAX_MESSAGE_LENGTH


class MessageValidator:
    """メッセージ検証を管理するクラス"""

    # 不適切な単語リスト（基本的なもの）
    DEFAULT_INAPPROPRIATE_WORDS = [
        "死ね", "殺す", "ばか", "あほ",
    ]

    # メッセージの最小長
    MIN_MESSAGE_LENGTH = 1

    def __init__(
        self,
        max_length: int = MAX_MESSAGE_LENGTH,
        inappropriate_words: Optional[List[str]] = None
    ):
        """
        MessageValidatorの初期化

        Args:
            max_length: メッセージの最大長
            inappropriate_words: 不適切な単語リスト
        """
        self.max_length = max_length
        self.inappropriate_words = (
            inappropriate_words
            if inappropriate_words is not None
            else self.DEFAULT_INAPPROPRIATE_WORDS.copy()
        )

    def validate(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        メッセージの検証

        Args:
            message: 検証するメッセージ

        Returns:
            Tuple[bool, Optional[str]]: (有効かどうか, エラーメッセージ)
        """
        # 空チェック
        if not message:
            return False, "メッセージを入力してください。"

        # 空白のみチェック
        if not message.strip():
            return False, "メッセージを入力してください。"

        # 最大長チェック
        if len(message) > self.max_length:
            return False, f"メッセージは{self.max_length}文字以内で入力してください。"

        # 不適切な内容のチェック
        for word in self.inappropriate_words:
            if word in message:
                return False, "不適切な表現が含まれています。"

        return True, None

    def sanitize(self, message: str) -> str:
        """
        メッセージのサニタイズ

        Args:
            message: サニタイズするメッセージ

        Returns:
            str: サニタイズされたメッセージ
        """
        # 前後の空白を削除
        sanitized = message.strip()

        # 連続する空白を単一の空白に
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # 制御文字を削除
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)

        return sanitized

    def validate_and_sanitize(self, message: str) -> Tuple[bool, str, Optional[str]]:
        """
        メッセージの検証とサニタイズを同時に行う

        Args:
            message: 検証・サニタイズするメッセージ

        Returns:
            Tuple[bool, str, Optional[str]]: (有効かどうか, サニタイズされたメッセージ, エラーメッセージ)
        """
        sanitized = self.sanitize(message)
        is_valid, error = self.validate(sanitized)
        return is_valid, sanitized, error


# デフォルトのバリデータインスタンス
_default_validator: Optional[MessageValidator] = None


def get_message_validator() -> MessageValidator:
    """デフォルトのMessageValidatorインスタンスを取得"""
    global _default_validator
    if _default_validator is None:
        _default_validator = MessageValidator()
    return _default_validator


def validate_message(message: str) -> Tuple[bool, Optional[str]]:
    """
    メッセージを検証するショートカット関数

    Args:
        message: 検証するメッセージ

    Returns:
        Tuple[bool, Optional[str]]: (有効かどうか, エラーメッセージ)
    """
    return get_message_validator().validate(message)


def sanitize_message(message: str) -> str:
    """
    メッセージをサニタイズするショートカット関数

    Args:
        message: サニタイズするメッセージ

    Returns:
        str: サニタイズされたメッセージ
    """
    return get_message_validator().sanitize(message)
