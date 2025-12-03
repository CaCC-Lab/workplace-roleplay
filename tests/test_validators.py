"""
Validators utility tests for improved coverage.
"""

import pytest
from utils.validators import (
    validate_message_content,
    validate_scenario_id,
    validate_model_name,
    validate_voice_name,
    validate_json_data,
    sanitize_input,
)


class TestValidateMessageContent:
    """validate_message_content関数のテスト"""

    def test_正常なメッセージ(self):
        """正常なメッセージの検証"""
        valid, error = validate_message_content("こんにちは")
        assert valid is True
        assert error is None

    def test_Noneメッセージ(self):
        """Noneメッセージの検証"""
        valid, error = validate_message_content(None)
        assert valid is False
        assert "必要です" in error

    def test_非文字列メッセージ(self):
        """非文字列メッセージの検証"""
        valid, error = validate_message_content(123)
        assert valid is False
        assert "文字列" in error

    def test_空メッセージ(self):
        """空メッセージの検証"""
        valid, error = validate_message_content("   ")
        assert valid is False
        assert "空です" in error

    def test_長すぎるメッセージ(self):
        """長すぎるメッセージの検証"""
        long_message = "a" * 5000
        valid, error = validate_message_content(long_message)
        assert valid is False
        assert "長すぎます" in error

    def test_HTMLタグを含むメッセージ(self):
        """HTMLタグを含むメッセージの検証"""
        valid, error = validate_message_content("<script>alert('xss')</script>")
        assert valid is False
        assert "HTMLタグ" in error

    def test_カスタム最大長(self):
        """カスタム最大長の検証"""
        valid, error = validate_message_content("hello", max_length=3)
        assert valid is False
        assert "長すぎます" in error


class TestValidateScenarioId:
    """validate_scenario_id関数のテスト"""

    def test_正常なシナリオID(self):
        """正常なシナリオIDの検証"""
        valid, error = validate_scenario_id("scenario1")
        assert valid is True
        assert error is None

    def test_ハイフン付きシナリオID(self):
        """ハイフン付きシナリオIDの検証"""
        valid, error = validate_scenario_id("gray_zone_01")
        assert valid is True
        assert error is None

    def test_NoneシナリオID(self):
        """NoneシナリオIDの検証"""
        valid, error = validate_scenario_id(None)
        assert valid is False
        assert "必要です" in error

    def test_非文字列シナリオID(self):
        """非文字列シナリオIDの検証"""
        valid, error = validate_scenario_id(123)
        assert valid is False
        assert "文字列" in error

    def test_無効な文字を含むシナリオID(self):
        """無効な文字を含むシナリオIDの検証"""
        valid, error = validate_scenario_id("scenario!@#")
        assert valid is False
        assert "無効" in error

    def test_スペースを含むシナリオID(self):
        """スペースを含むシナリオIDの検証"""
        valid, error = validate_scenario_id("scenario 1")
        assert valid is False
        assert "無効" in error


class TestValidateModelName:
    """validate_model_name関数のテスト"""

    def test_正常なモデル名(self):
        """正常なモデル名の検証"""
        valid, error = validate_model_name("gemini-1.5-flash")
        assert valid is True
        assert error is None

    def test_Noneモデル名(self):
        """Noneモデル名の検証"""
        valid, error = validate_model_name(None)
        assert valid is False
        assert "必要です" in error

    def test_非文字列モデル名(self):
        """非文字列モデル名の検証"""
        valid, error = validate_model_name(123)
        assert valid is False
        assert "文字列" in error

    def test_許可されていないモデル名(self):
        """許可されていないモデル名の検証"""
        valid, error = validate_model_name("gpt-4")
        assert valid is False
        assert "無効なモデル名" in error

    def test_カスタム許可リスト(self):
        """カスタム許可リストでの検証"""
        valid, error = validate_model_name("custom-model", allowed_models=["custom-model"])
        assert valid is True
        assert error is None

    def test_許可されたモデル一覧(self):
        """全ての許可されたモデルの検証"""
        allowed_models = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ]
        for model in allowed_models:
            valid, error = validate_model_name(model)
            assert valid is True, f"{model} should be valid"


class TestValidateVoiceName:
    """validate_voice_name関数のテスト"""

    def test_正常な音声名(self):
        """正常な音声名の検証"""
        valid, error = validate_voice_name("kore")
        assert valid is True
        assert error is None

    def test_None音声名(self):
        """None音声名の検証（オプション）"""
        valid, error = validate_voice_name(None)
        assert valid is True
        assert error is None

    def test_非文字列音声名(self):
        """非文字列音声名の検証"""
        valid, error = validate_voice_name(123)
        assert valid is False
        assert "文字列" in error

    def test_許可されていない音声名(self):
        """許可されていない音声名の検証"""
        valid, error = validate_voice_name("invalid_voice")
        assert valid is False
        assert "無効な音声名" in error

    def test_大文字小文字の区別(self):
        """大文字小文字の区別なし"""
        valid, error = validate_voice_name("KORE")
        assert valid is True
        assert error is None

    def test_カスタム許可リスト(self):
        """カスタム許可リストでの検証"""
        valid, error = validate_voice_name("custom", allowed_voices=["custom"])
        assert valid is True
        assert error is None


class TestValidateJsonData:
    """validate_json_data関数のテスト"""

    def test_正常なJSONデータ(self):
        """正常なJSONデータの検証"""
        valid, error = validate_json_data({"key": "value"})
        assert valid is True
        assert error is None

    def test_NoneJSONデータ(self):
        """NoneJSONデータの検証"""
        valid, error = validate_json_data(None)
        assert valid is False
        assert "必要です" in error

    def test_非辞書JSONデータ(self):
        """非辞書JSONデータの検証"""
        valid, error = validate_json_data("not a dict")
        assert valid is False
        assert "辞書形式" in error

    def test_必須フィールド不足(self):
        """必須フィールド不足の検証"""
        valid, error = validate_json_data({"key": "value"}, required_fields=["key", "missing"])
        assert valid is False
        assert "missing" in error

    def test_必須フィールド全て存在(self):
        """必須フィールドが全て存在する場合"""
        valid, error = validate_json_data({"key1": "value1", "key2": "value2"}, required_fields=["key1", "key2"])
        assert valid is True
        assert error is None


class TestSanitizeInput:
    """sanitize_input関数のテスト"""

    def test_正常なテキスト(self):
        """正常なテキストのサニタイズ"""
        result = sanitize_input("Hello World")
        assert result == "Hello World"

    def test_前後の空白削除(self):
        """前後の空白を削除"""
        result = sanitize_input("  hello  ")
        assert result == "hello"

    def test_連続する空白を単一に(self):
        """連続する空白を単一の空白に"""
        result = sanitize_input("hello    world")
        assert result == "hello world"

    def test_制御文字の削除(self):
        """制御文字を削除"""
        result = sanitize_input("hello\x00world")
        assert result == "helloworld"

    def test_非文字列の変換(self):
        """非文字列を文字列に変換"""
        result = sanitize_input(123)
        assert result == "123"

    def test_改行とタブの処理(self):
        """改行とタブの処理（制御文字は削除される）"""
        result = sanitize_input("hello\n\tworld")
        # 改行とタブは制御文字として削除される
        assert result == "helloworld"
