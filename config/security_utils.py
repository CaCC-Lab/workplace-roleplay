"""
セキュリティ関連のユーティリティ関数
シークレットキーの生成と検証
"""
import secrets
import string
from typing import Tuple


def generate_secure_secret_key(length: int = 64) -> str:
    """
    安全なシークレットキーを生成

    Args:
        length: キーの長さ（デフォルト: 64文字）

    Returns:
        str: 生成されたシークレットキー
    """
    # 使用する文字セット（英数字と一部の特殊文字）
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # cryptographically strongな乱数生成器を使用
    return "".join(secrets.choice(alphabet) for _ in range(length))


def is_secure_secret_key(key: str) -> Tuple[bool, str]:
    """
    シークレットキーが安全かチェック

    Args:
        key: チェックするシークレットキー

    Returns:
        Tuple[bool, str]: (安全かどうか, エラーメッセージまたは"OK")
    """
    # 長さチェック
    if len(key) < 32:
        return False, f"Key is too short ({len(key)} chars). Minimum 32 characters required."

    # 文字種の多様性チェック
    has_upper = any(c.isupper() for c in key)
    has_lower = any(c.islower() for c in key)
    has_digit = any(c.isdigit() for c in key)
    has_special = any(c in string.punctuation for c in key)

    complexity_score = sum([has_upper, has_lower, has_digit, has_special])

    if complexity_score < 3:
        return False, "Key lacks complexity. Use uppercase, lowercase, digits, and special characters."

    # エントロピーチェック（同じ文字の繰り返し）
    unique_chars = len(set(key))
    if unique_chars < len(key) * 0.5:  # 50%以上がユニークな文字であるべき
        return False, "Key has too many repeated characters."

    # 単純なパターンのチェック
    simple_patterns = ["password", "secret", "12345", "admin", "default", "qwerty", "asdfgh", "zxcvbn"]

    key_lower = key.lower()
    for pattern in simple_patterns:
        if pattern in key_lower:
            return False, f"Key contains predictable pattern: '{pattern}'"

    return True, "OK"


def recommend_secret_key_improvements(key: str) -> str:
    """
    シークレットキーの改善提案を返す

    Args:
        key: チェックするシークレットキー

    Returns:
        str: 改善提案のメッセージ
    """
    is_secure, message = is_secure_secret_key(key)

    if is_secure:
        return "Your secret key appears to be secure!"

    recommendations = [f"Issue: {message}"]

    if len(key) < 32:
        recommendations.append(f"Recommendation: Increase length to at least 32 characters (current: {len(key)})")

    if not any(c.isupper() for c in key):
        recommendations.append("Recommendation: Add uppercase letters")

    if not any(c.islower() for c in key):
        recommendations.append("Recommendation: Add lowercase letters")

    if not any(c.isdigit() for c in key):
        recommendations.append("Recommendation: Add digits")

    if not any(c in string.punctuation for c in key):
        recommendations.append("Recommendation: Add special characters (!@#$%^&* etc.)")

    recommendations.append("\nExample of a secure key:")
    recommendations.append(generate_secure_secret_key(48))

    return "\n".join(recommendations)


if __name__ == "__main__":
    # 使用例
    print("Generating secure secret keys...")
    print(f"64 chars: {generate_secure_secret_key(64)}")
    print(f"48 chars: {generate_secure_secret_key(48)}")
    print(f"32 chars: {generate_secure_secret_key(32)}")

    print("\nChecking key security...")
    test_keys = [
        "short",
        "password123password123password123",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        generate_secure_secret_key(48),
    ]

    for key in test_keys:
        is_secure, message = is_secure_secret_key(key)
        print(f"\nKey: {key[:20]}...")
        print(f"Secure: {is_secure}")
        print(f"Message: {message}")
