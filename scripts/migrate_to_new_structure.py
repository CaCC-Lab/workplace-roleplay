#!/usr/bin/env python3
"""既存のアプリケーションを新しい構造に移行するスクリプト"""
import os
import shutil
import sys


def main():
    """メイン処理"""
    print("=== 新構造への移行スクリプト ===\n")
    
    # 確認
    response = input("このスクリプトは既存のファイルを新しい構造に移行します。続行しますか？ (y/N): ")
    if response.lower() != "y":
        print("キャンセルしました。")
        return
    
    print("\n移行を開始します...\n")
    
    # 1. テンプレートとスタティックファイルの確認
    if os.path.exists("templates") and not os.path.exists("src/templates"):
        print("✓ templates ディレクトリは既に正しい場所にあります")
    
    if os.path.exists("static") and not os.path.exists("src/static"):
        print("✓ static ディレクトリは既に正しい場所にあります")
    
    # 2. 既存のサービスファイルの移行
    migrate_services()
    
    # 3. 既存のAPIファイルの移行
    migrate_api_files()
    
    # 4. ユーティリティファイルの移行
    migrate_utils()
    
    # 5. モデルファイルの移行
    migrate_models()
    
    print("\n移行が完了しました！")
    print("\n次のステップ:")
    print("1. 新しい依存関係をインストール:")
    print("   pip install -r requirements/development.txt")
    print("\n2. 新しいアプリケーションを起動:")
    print("   python run.py")
    print("\n3. 動作確認後、古いファイルを削除:")
    print("   - app.py (バックアップは保持)")
    print("   - 他の不要なファイル")


def migrate_services():
    """サービスファイルの移行"""
    print("サービスファイルの移行...")
    
    # 既存のservicesディレクトリがある場合
    if os.path.exists("services") and os.path.isdir("services"):
        # ファイルをコピー
        service_files = [
            "llm_service.py",
            "scenario_service.py",
            "conversation_service.py",
            "session_service.py",
            "analytics_service.py",
            "journal_service.py",
            "watch_service.py"
        ]
        
        for filename in service_files:
            src_path = f"services/{filename}"
            if os.path.exists(src_path):
                dst_path = f"src/services/{filename}"
                if not os.path.exists(dst_path):
                    print(f"  - {filename} を移行")
                    shutil.copy2(src_path, dst_path)


def migrate_api_files():
    """APIファイルの移行"""
    print("\nAPIファイルの移行...")
    
    # 既存のapiディレクトリがある場合
    if os.path.exists("api") and os.path.isdir("api"):
        api_files = [
            "chat.py",
            "scenarios.py",
            "watch.py",
            "analytics.py"
        ]
        
        for filename in api_files:
            src_path = f"api/{filename}"
            if os.path.exists(src_path):
                # ファイル名を変更する場合もある
                dst_filename = filename
                if filename == "watch.py":
                    dst_filename = "watch_api.py"
                
                dst_path = f"src/api/{dst_filename}"
                if not os.path.exists(dst_path):
                    print(f"  - {filename} を移行")
                    shutil.copy2(src_path, dst_path)


def migrate_utils():
    """ユーティリティファイルの移行"""
    print("\nユーティリティファイルの移行...")
    
    # utilsディレクトリ
    if os.path.exists("utils") and os.path.isdir("utils"):
        utils_files = [
            "security.py",
            "redis_manager.py",
            "helpers.py"
        ]
        
        for filename in utils_files:
            src_path = f"utils/{filename}"
            if os.path.exists(src_path):
                dst_path = f"src/utils/{filename}"
                if not os.path.exists(dst_path):
                    print(f"  - {filename} を移行")
                    shutil.copy2(src_path, dst_path)


def migrate_models():
    """モデルファイルの移行"""
    print("\nモデルファイルの移行...")
    
    # models.pyファイル
    if os.path.exists("models.py"):
        # モデルを個別ファイルに分割
        print("  - models.py を分割して移行")
        
        # src/models/__init__.py を作成
        init_content = '''"""モデルモジュール"""
from .user import User
from .conversation import Conversation, Message
from .scenario_result import ScenarioResult

__all__ = ["User", "Conversation", "Message", "ScenarioResult"]
'''
        
        with open("src/models/__init__.py", "w", encoding="utf-8") as f:
            f.write(init_content)
        
        print("    モデルファイルの分割が必要です（手動で実施してください）")


if __name__ == "__main__":
    main()