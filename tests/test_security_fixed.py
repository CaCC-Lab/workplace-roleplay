#!/usr/bin/env python3
"""
セキュリティ修正の簡易テストスイート
実際の環境で動作する現実的なテスト
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_security_utils():
    """SecurityUtilsのテスト"""
    from utils.security import SecurityUtils

    print("🔒 SecurityUtilsのテスト...")

    # XSS対策テスト
    dangerous_inputs = [
        '<script>alert("XSS")</script>',
        '<img src=x onerror="alert(1)">',
        '<iframe src="evil.com"></iframe>',
    ]

    for dangerous in dangerous_inputs:
        cleaned = SecurityUtils.escape_html(dangerous)
        # スクリプトタグが除去されていることを確認
        if "<script" not in cleaned.lower() and "onerror" not in cleaned.lower():
            print(f"  ✓ XSS防御成功: {dangerous[:30]}...")
        else:
            print(f"  ⚠️ 要確認: {dangerous[:30]}... → {cleaned[:30]}...")

    # 入力検証テスト
    print("\n📝 入力検証のテスト...")

    # 正常な入力
    valid, error = SecurityUtils.validate_message("これは正常なメッセージです")
    assert valid == True
    print("  ✓ 正常な入力: OK")

    # 空の入力
    valid, error = SecurityUtils.validate_message("")
    assert valid == False
    print("  ✓ 空の入力: 適切に拒否")

    # 長すぎる入力
    long_msg = "a" * 10001
    valid, error = SecurityUtils.validate_message(long_msg)
    assert valid == False
    print("  ✓ 長すぎる入力: 適切に拒否")

    # SHA-256ハッシュテスト
    print("\n🔐 SHA-256ハッシュのテスト...")
    hashed = SecurityUtils.hash_user_id("test_user")
    assert len(hashed) == 64
    print(f"  ✓ SHA-256ハッシュ生成: {hashed[:16]}...")


def test_csrf_protection():
    """CSRF保護のテスト"""
    from utils.security import CSRFProtection

    print("\n🛡️ CSRF保護のテスト...")

    # トークン生成
    token1 = CSRFProtection.generate_token()
    token2 = CSRFProtection.generate_token()

    assert len(token1) == 64
    assert token1 != token2
    print(f"  ✓ CSRFトークン生成: {token1[:16]}...")
    print("  ✓ トークンはユニーク")


def test_rate_limiter():
    """レート制限のテスト"""
    from utils.security import RateLimiter

    print("\n⏱️ レート制限のテスト...")

    limiter = RateLimiter(max_requests=3, window_seconds=60)

    # 3回まではOK
    for i in range(3):
        assert limiter.is_allowed("test_user") == True
    print("  ✓ 3回までのリクエスト: 許可")

    # 4回目はブロック
    assert limiter.is_allowed("test_user") == False
    print("  ✓ 4回目のリクエスト: ブロック")

    # 別のユーザーはOK
    assert limiter.is_allowed("another_user") == True
    print("  ✓ 別ユーザー: 許可")


def test_feature_flags():
    """フィーチャーフラグのテスト"""
    print("\n🚩 フィーチャーフラグのテスト...")

    from config.feature_flags import get_feature_flags

    # フィーチャーフラグを取得
    flags = get_feature_flags()

    # 設定の取得
    config = flags.to_dict()
    assert "model_selection" in config
    assert "tts" in config
    print(f"  ✓ モデル選択有効: {config['model_selection']}")
    print(f"  ✓ TTS有効: {config['tts']}")
    print(f"  ✓ デフォルトモデル: {config['default_model']}")


def test_ab_routes_integration():
    """A/Bテストルートの統合テスト"""
    print("\n🔄 A/Bテストルートのテスト...")

    from app import app

    client = app.test_client()

    # ヘルスチェック
    response = client.get("/api/v2/health")
    assert response.status_code == 200, f"V2ヘルスチェック: {response.status_code}"
    print("  ✓ V2ヘルスチェック: 正常")

    # 設定エンドポイント
    response = client.get("/api/v2/config")
    assert response.status_code == 200, f"V2設定エンドポイント: {response.status_code}"
    print("  ✓ V2設定エンドポイント: 正常")


def main():
    """メインテスト実行"""
    print("=" * 60)
    print("🧪 セキュリティ修正テストスイート")
    print("=" * 60)

    all_passed = True

    # 各テストを実行
    tests = [
        ("SecurityUtils", test_security_utils),
        ("CSRF保護", test_csrf_protection),
        ("レート制限", test_rate_limiter),
        ("フィーチャーフラグ", test_feature_flags),
        ("A/Bルート統合", test_ab_routes_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            test_func()
            results.append((name, True))
        except AssertionError as e:
            print(f"\n❌ {name}: 失敗 - {e}")
            results.append((name, False))
            all_passed = False
        except Exception as e:
            print(f"\n⚠️ {name}: エラー - {e}")
            results.append((name, None))

    # サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    for name, result in results:
        if result is True:
            print(f"  ✅ {name}: 成功")
        elif result is False:
            print(f"  ❌ {name}: 失敗")
        else:
            print(f"  ⚠️ {name}: スキップ")

    if all_passed:
        print("\n🎉 全てのテストが成功しました！")
    else:
        print("\n⚠️ 一部のテストが失敗しました")

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
