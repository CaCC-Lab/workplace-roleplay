#!/usr/bin/env python3
"""
緊急修正版：API Key未設定時でもアプリケーションが起動するように修正
"""
import os
import sys

# 環境変数チェック
if not os.environ.get("GOOGLE_API_KEY"):
    print("=" * 60)
    print("⚠️  警告: GOOGLE_API_KEY が設定されていません")
    print("=" * 60)
    print()
    print("API Key なしでも起動できるよう、ダミーモードで実行します。")
    print("実際のAI機能は利用できません。")
    print()
    print("API Keyを設定するには：")
    print("1. .env ファイルを作成（.env.example をコピー）")
    print("2. GOOGLE_API_KEY を設定")
    print("3. アプリケーションを再起動")
    print()
    print("=" * 60)
    
    # ダミーのAPI Keyを設定（実際には使用されない）
    os.environ["GOOGLE_API_KEY"] = "dummy-key-for-testing"
    os.environ["DUMMY_MODE"] = "true"

# 通常のapp.pyを実行
if __name__ == "__main__":
    # app.pyをインポートして実行
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import app