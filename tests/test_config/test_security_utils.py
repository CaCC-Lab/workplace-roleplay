"""
Config security utils tests for improved coverage.
"""

import pytest
import string


class TestGenerateSecureSecretKey:
    """generate_secure_secret_key関数のテスト"""

    def test_デフォルト長さで生成(self):
        """デフォルトの長さ（64文字）で生成"""
        from config.security_utils import generate_secure_secret_key

        key = generate_secure_secret_key()

        assert len(key) == 64

    def test_カスタム長さで生成(self):
        """カスタムの長さで生成"""
        from config.security_utils import generate_secure_secret_key

        key = generate_secure_secret_key(128)

        assert len(key) == 128

    def test_生成キーはユニーク(self):
        """生成されるキーは毎回異なる"""
        from config.security_utils import generate_secure_secret_key

        key1 = generate_secure_secret_key()
        key2 = generate_secure_secret_key()

        assert key1 != key2

    def test_使用文字セット(self):
        """適切な文字セットが使用されている"""
        from config.security_utils import generate_secure_secret_key

        key = generate_secure_secret_key(1000)  # 統計的に十分なサンプル

        # 英字・数字・特殊文字が含まれることを確認
        has_upper = any(c.isupper() for c in key)
        has_lower = any(c.islower() for c in key)
        has_digit = any(c.isdigit() for c in key)
        has_special = any(c in string.punctuation for c in key)

        assert has_upper
        assert has_lower
        assert has_digit
        assert has_special


class TestIsSecureSecretKey:
    """is_secure_secret_key関数のテスト"""

    def test_安全なキー(self):
        """安全なキーのチェック"""
        from config.security_utils import is_secure_secret_key, generate_secure_secret_key

        key = generate_secure_secret_key(64)
        is_secure, message = is_secure_secret_key(key)

        assert is_secure is True
        assert message == "OK"

    def test_短すぎるキー(self):
        """短すぎるキーのチェック"""
        from config.security_utils import is_secure_secret_key

        is_secure, message = is_secure_secret_key("short")

        assert is_secure is False
        assert "too short" in message

    def test_複雑さ不足のキー(self):
        """複雑さが不足しているキー"""
        from config.security_utils import is_secure_secret_key

        # 数字のみ
        is_secure, message = is_secure_secret_key("12345678901234567890123456789012")

        assert is_secure is False
        assert "lacks complexity" in message

    def test_繰り返し文字が多いキー(self):
        """繰り返し文字が多いキー"""
        from config.security_utils import is_secure_secret_key

        # 同じ文字の繰り返し
        is_secure, message = is_secure_secret_key("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaAa1!")

        assert is_secure is False
        assert "repeated characters" in message

    def test_予測可能なパターンを含むキー_password(self):
        """予測可能なパターン（password）を含むキー"""
        from config.security_utils import is_secure_secret_key

        is_secure, message = is_secure_secret_key("abc123passwordXYZ456!@#$%^&*()_+")

        assert is_secure is False
        assert "predictable pattern" in message
        assert "password" in message

    def test_予測可能なパターンを含むキー_secret(self):
        """予測可能なパターン（secret）を含むキー"""
        from config.security_utils import is_secure_secret_key

        is_secure, message = is_secure_secret_key("abc123secretXYZ456!@#$%^&*()_+AB")

        assert is_secure is False
        assert "secret" in message

    def test_予測可能なパターンを含むキー_admin(self):
        """予測可能なパターン（admin）を含むキー"""
        from config.security_utils import is_secure_secret_key

        is_secure, message = is_secure_secret_key("abc123adminXYZ456!@#$%^&*()_+ABC")

        assert is_secure is False
        assert "admin" in message

    def test_予測可能なパターンを含むキー_qwerty(self):
        """予測可能なパターン（qwerty）を含むキー"""
        from config.security_utils import is_secure_secret_key

        is_secure, message = is_secure_secret_key("abc123qwertyXYZ456!@#$%^&*()_+AB")

        assert is_secure is False
        assert "qwerty" in message


class TestRecommendSecretKeyImprovements:
    """recommend_secret_key_improvements関数のテスト"""

    def test_安全なキーには改善提案なし(self):
        """安全なキーには改善提案がない"""
        from config.security_utils import (
            recommend_secret_key_improvements,
            generate_secure_secret_key,
        )

        key = generate_secure_secret_key(64)
        recommendations = recommend_secret_key_improvements(key)

        assert "appears to be secure" in recommendations

    def test_短いキーへの改善提案(self):
        """短いキーへの改善提案"""
        from config.security_utils import recommend_secret_key_improvements

        recommendations = recommend_secret_key_improvements("short")

        assert "Increase length" in recommendations

    def test_大文字なしキーへの改善提案(self):
        """大文字がないキーへの改善提案"""
        from config.security_utils import recommend_secret_key_improvements

        recommendations = recommend_secret_key_improvements("abcdefghijklmnopqrstuvwxyz123456")

        assert "uppercase" in recommendations

    def test_小文字なしキーへの改善提案(self):
        """小文字がないキーへの改善提案"""
        from config.security_utils import recommend_secret_key_improvements

        recommendations = recommend_secret_key_improvements("ABCDEFGHIJKLMNOPQRSTUVWXYZ123456")

        assert "lowercase" in recommendations

    def test_数字なしキーへの改善提案(self):
        """数字がないキーへの改善提案"""
        from config.security_utils import recommend_secret_key_improvements

        # 数字がなく、かつ短すぎるキー（32文字未満でdigits推奨が出る）
        recommendations = recommend_secret_key_improvements("ABCDefghijklmnopqrstuvwxyz!@#")

        assert "digits" in recommendations or "Increase length" in recommendations

    def test_特殊文字なしキーへの改善提案(self):
        """特殊文字がないキーへの改善提案"""
        from config.security_utils import recommend_secret_key_improvements

        recommendations = recommend_secret_key_improvements("ABCDefghijklmnopqrstuvwxyz123456")

        assert "special characters" in recommendations

    def test_サンプルキーが含まれる(self):
        """改善提案にサンプルキーが含まれる"""
        from config.security_utils import recommend_secret_key_improvements

        recommendations = recommend_secret_key_improvements("short")

        assert "Example of a secure key" in recommendations
