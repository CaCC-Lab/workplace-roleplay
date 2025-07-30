#!/usr/bin/env python3
"""アプリケーションのインポートテスト"""
try:
    import app
    print("✅ アプリケーションのインポート成功")
except Exception as e:
    print(f"❌ エラー: {str(e)}")
    import traceback
    traceback.print_exc()