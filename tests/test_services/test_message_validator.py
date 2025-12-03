"""
MessageValidatorのユニットテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.message_validator import (
    MessageValidator,
    get_message_validator,
    validate_message,
    sanitize_message,
)


class TestMessageValidator:
    """MessageValidatorのテストクラス"""

    @pytest.fixture
    def validator(self):
        return MessageValidator()


class TestValidate:
    """validateメソッドのテスト"""

    @pytest.fixture
    def validator(self):
        return MessageValidator()

    def test_valid_message(self, validator):
        """有効なメッセージのテスト"""
        is_valid, error = validator.validate("こんにちは")
        assert is_valid is True
        assert error is None

    def test_empty_message(self, validator):
        """空のメッセージのテスト"""
        is_valid, error = validator.validate("")
        assert is_valid is False
        assert "入力してください" in error

    def test_whitespace_only(self, validator):
        """空白のみのメッセージのテスト"""
        is_valid, error = validator.validate("   ")
        assert is_valid is False
        assert "入力してください" in error

    def test_too_long_message(self):
        """長すぎるメッセージのテスト"""
        validator = MessageValidator(max_length=10)
        is_valid, error = validator.validate("あ" * 11)
        assert is_valid is False
        assert "10文字以内" in error

    def test_inappropriate_word(self, validator):
        """不適切な単語を含むメッセージのテスト"""
        is_valid, error = validator.validate("テストばかテスト")
        assert is_valid is False
        assert "不適切な表現" in error

    def test_custom_inappropriate_words(self):
        """カスタム不適切単語リストのテスト"""
        validator = MessageValidator(inappropriate_words=["NG"])

        is_valid, error = validator.validate("これはNGです")
        assert is_valid is False

        is_valid, error = validator.validate("これはOKです")
        assert is_valid is True


class TestSanitize:
    """sanitizeメソッドのテスト"""

    @pytest.fixture
    def validator(self):
        return MessageValidator()

    def test_trim_whitespace(self, validator):
        """前後の空白が削除されることをテスト"""
        result = validator.sanitize("  こんにちは  ")
        assert result == "こんにちは"

    def test_normalize_whitespace(self, validator):
        """連続する空白が正規化されることをテスト"""
        result = validator.sanitize("こんにちは    世界")
        assert result == "こんにちは 世界"

    def test_remove_control_chars(self, validator):
        """制御文字が削除されることをテスト"""
        result = validator.sanitize("こんにちは\x00世界")
        assert result == "こんにちは世界"

    def test_combined_sanitization(self, validator):
        """複合的なサニタイズのテスト"""
        result = validator.sanitize("  テスト\x00   メッセージ  ")
        assert result == "テスト メッセージ"


class TestValidateAndSanitize:
    """validate_and_sanitizeメソッドのテスト"""

    @pytest.fixture
    def validator(self):
        return MessageValidator()

    def test_valid_message(self, validator):
        """有効なメッセージでの動作テスト"""
        is_valid, sanitized, error = validator.validate_and_sanitize("  こんにちは  ")

        assert is_valid is True
        assert sanitized == "こんにちは"
        assert error is None

    def test_invalid_message(self, validator):
        """無効なメッセージでの動作テスト"""
        is_valid, sanitized, error = validator.validate_and_sanitize("   ")

        assert is_valid is False
        assert error is not None


class TestShortcutFunctions:
    """ショートカット関数のテスト"""

    def test_validate_message(self):
        """validate_message関数のテスト"""
        is_valid, error = validate_message("テスト")
        assert is_valid is True
        assert error is None

    def test_sanitize_message(self):
        """sanitize_message関数のテスト"""
        result = sanitize_message("  テスト  ")
        assert result == "テスト"


class TestGetMessageValidator:
    """get_message_validator関数のテスト"""

    def test_returns_instance(self):
        """インスタンスが返されることをテスト"""
        import services.message_validator as module

        module._default_validator = None

        validator = get_message_validator()
        assert isinstance(validator, MessageValidator)

    def test_singleton(self):
        """シングルトンパターンのテスト"""
        import services.message_validator as module

        module._default_validator = None

        validator1 = get_message_validator()
        validator2 = get_message_validator()
        assert validator1 is validator2
