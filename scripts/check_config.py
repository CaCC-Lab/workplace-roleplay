#!/usr/bin/env python
"""
設定の動作確認スクリプト
環境変数と設定ファイルから正しく値が読み込まれているか確認します
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config, DevelopmentConfig, ProductionConfig, ConfigForTesting


def check_environment():
    """現在の環境を確認"""
    print("=== 環境確認 ===")
    print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', '(未設定)')}")
    print(f"GOOGLE_API_KEY: {'設定済み' if os.environ.get('GOOGLE_API_KEY') else '(未設定)'}")
    print(f"FLASK_SECRET_KEY: {'設定済み' if os.environ.get('FLASK_SECRET_KEY') else '(未設定)'}")
    print()


def check_config():
    """設定の読み込みと表示"""
    print("=== 設定読み込み ===")
    try:
        config = get_config()
        print(f"設定クラス: {config.__class__.__name__}")
        print(f"環境: {config.FLASK_ENV}")
        print()

        print("=== 主要な設定値 ===")
        # 機密情報をマスクして表示
        config_dict = config.to_dict(mask_secrets=True)

        # 重要な設定項目を表示
        important_fields = [
            "FLASK_ENV",
            "DEBUG",
            "TESTING",
            "SECRET_KEY",
            "GOOGLE_API_KEY",
            "DEFAULT_TEMPERATURE",
            "DEFAULT_MODEL",
            "SESSION_TYPE",
            "PORT",
            "HOST",
            "LOG_LEVEL",
        ]

        for field in important_fields:
            if field in config_dict:
                print(f"{field}: {config_dict[field]}")

        print()

        # 環境別の特別な設定
        if isinstance(config, ProductionConfig):
            print("=== 本番環境固有の設定 ===")
            print(f"SECURE_COOKIES: {config.SECURE_COOKIES}")
            print(f"HOT_RELOAD: {config.HOT_RELOAD}")
        elif isinstance(config, DevelopmentConfig):
            print("=== 開発環境固有の設定 ===")
            print(f"HOT_RELOAD: {config.HOT_RELOAD}")
        elif isinstance(config, ConfigForTesting):
            print("=== テスト環境固有の設定 ===")
            print(f"WTF_CSRF_ENABLED: {config.WTF_CSRF_ENABLED}")

        print()

        # 検証結果
        print("=== 検証結果 ===")
        validation_passed = True

        # 本番環境での必須チェック
        if config.FLASK_ENV == "production":
            if not config.GOOGLE_API_KEY:
                print("❌ エラー: 本番環境ではGOOGLE_API_KEYが必須です")
                validation_passed = False
            if config.SECRET_KEY == "default-secret-key-change-in-production":
                print("❌ エラー: 本番環境では適切なSECRET_KEYが必須です")
                validation_passed = False

        if validation_passed:
            print("✅ 設定の検証に成功しました")
        else:
            print("❌ 設定の検証に失敗しました")

        return validation_passed

    except Exception as e:
        print(f"❌ エラー: 設定の読み込みに失敗しました: {e}")
        return False


def test_environment_override():
    """環境変数のオーバーライドテスト"""
    print("\n=== 環境変数オーバーライドテスト ===")

    # 元の値を保存
    original_temp = os.environ.get("DEFAULT_TEMPERATURE")

    try:
        # 環境変数を設定
        os.environ["DEFAULT_TEMPERATURE"] = "0.9"

        # 新しい設定を読み込み
        from config import Config

        test_config = Config()

        if test_config.DEFAULT_TEMPERATURE == 0.9:
            print("✅ 環境変数のオーバーライドが正常に動作しています")
        else:
            print("❌ 環境変数のオーバーライドが機能していません")

    finally:
        # 元に戻す
        if original_temp is None:
            os.environ.pop("DEFAULT_TEMPERATURE", None)
        else:
            os.environ["DEFAULT_TEMPERATURE"] = original_temp


def main():
    """メイン処理"""
    print("workplace-roleplay 設定チェッカー")
    print("=" * 50)
    print()

    check_environment()
    success = check_config()
    test_environment_override()

    print()
    print("=" * 50)

    if success:
        print("設定は正常です。アプリケーションを起動できます。")
        sys.exit(0)
    else:
        print("設定にエラーがあります。環境変数を確認してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()
