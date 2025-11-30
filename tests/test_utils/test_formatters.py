"""
Formatters tests for improved coverage.
"""

import pytest


class TestEscapeForJson:
    """escape_for_json関数のテスト"""

    def test_通常の文字列(self):
        """通常の文字列のエスケープ"""
        from utils.formatters import escape_for_json

        result = escape_for_json("hello")

        assert result == "hello"

    def test_特殊文字のエスケープ(self):
        """特殊文字のエスケープ"""
        from utils.formatters import escape_for_json

        result = escape_for_json('test "quote" and \\backslash')

        assert '"' not in result or '\\"' in result

    def test_非文字列の入力(self):
        """非文字列の入力"""
        from utils.formatters import escape_for_json

        result = escape_for_json(123)

        assert result == "123"

    def test_改行文字のエスケープ(self):
        """改行文字のエスケープ"""
        from utils.formatters import escape_for_json

        result = escape_for_json("line1\nline2")

        assert "\\n" in result


class TestFormatDatetime:
    """format_datetime関数のテスト"""

    def test_空の値(self):
        """空の値"""
        from utils.formatters import format_datetime

        result = format_datetime(None)

        assert result == "なし"

    def test_空文字列(self):
        """空文字列"""
        from utils.formatters import format_datetime

        result = format_datetime("")

        assert result == "なし"

    def test_有効なISO形式(self):
        """有効なISO形式"""
        from utils.formatters import format_datetime

        result = format_datetime("2024-01-15T10:30:00")

        assert "2024年01月15日" in result
        assert "10:30" in result

    def test_無効な形式(self):
        """無効な形式"""
        from utils.formatters import format_datetime

        result = format_datetime("invalid-date")

        assert result == "invalid-date"


class TestFormatDuration:
    """format_duration関数のテスト"""

    def test_None値(self):
        """None値"""
        from utils.formatters import format_duration

        result = format_duration(None)

        assert result == "不明"

    def test_秒単位(self):
        """秒単位"""
        from utils.formatters import format_duration

        result = format_duration(45)

        assert result == "45秒"

    def test_分単位(self):
        """分単位（秒あり）"""
        from utils.formatters import format_duration

        result = format_duration(125)  # 2分5秒

        assert "2分" in result
        assert "5秒" in result

    def test_分単位_秒なし(self):
        """分単位（秒なし）"""
        from utils.formatters import format_duration

        result = format_duration(120)  # 2分ちょうど

        assert result == "2分"

    def test_時間単位(self):
        """時間単位（分あり）"""
        from utils.formatters import format_duration

        result = format_duration(3900)  # 1時間5分

        assert "1時間" in result
        assert "5分" in result

    def test_時間単位_分なし(self):
        """時間単位（分なし）"""
        from utils.formatters import format_duration

        result = format_duration(3600)  # 1時間ちょうど

        assert result == "1時間"


class TestFormatFileSize:
    """format_file_size関数のテスト"""

    def test_バイト(self):
        """バイト単位"""
        from utils.formatters import format_file_size

        result = format_file_size(500)

        assert "B" in result
        assert "500" in result

    def test_キロバイト(self):
        """キロバイト単位"""
        from utils.formatters import format_file_size

        result = format_file_size(2048)

        assert "KB" in result

    def test_メガバイト(self):
        """メガバイト単位"""
        from utils.formatters import format_file_size

        result = format_file_size(2 * 1024 * 1024)

        assert "MB" in result

    def test_ギガバイト(self):
        """ギガバイト単位"""
        from utils.formatters import format_file_size

        result = format_file_size(2 * 1024 * 1024 * 1024)

        assert "GB" in result

    def test_テラバイト(self):
        """テラバイト単位"""
        from utils.formatters import format_file_size

        result = format_file_size(2 * 1024 * 1024 * 1024 * 1024)

        assert "TB" in result


class TestTruncateText:
    """truncate_text関数のテスト"""

    def test_短いテキスト(self):
        """短いテキスト（切り詰めなし）"""
        from utils.formatters import truncate_text

        result = truncate_text("short", max_length=100)

        assert result == "short"

    def test_長いテキスト(self):
        """長いテキスト（切り詰めあり）"""
        from utils.formatters import truncate_text

        long_text = "a" * 200
        result = truncate_text(long_text, max_length=100)

        assert len(result) == 100
        assert result.endswith("...")

    def test_カスタムサフィックス(self):
        """カスタムサフィックス"""
        from utils.formatters import truncate_text

        long_text = "a" * 200
        result = truncate_text(long_text, max_length=100, suffix="…")

        assert result.endswith("…")

    def test_ちょうど最大長(self):
        """ちょうど最大長のテキスト"""
        from utils.formatters import truncate_text

        text = "a" * 100
        result = truncate_text(text, max_length=100)

        assert result == text
        assert not result.endswith("...")
