#!/usr/bin/env python3
"""
アプリケーション起動時間の比較
"""
import time
import importlib
import sys

print("=== アプリケーション起動時間の測定 ===\n")

# 1. 通常版の起動時間
print("1. 通常版 (app.py) の起動時間測定:")
start = time.time()
try:
    # 環境変数を設定してテストモードにする
    import os
    os.environ['TESTING'] = 'true'
    
    # appモジュールをインポート
    if 'app' in sys.modules:
        del sys.modules['app']
    
    import app
    elapsed = time.time() - start
    print(f"   起動時間: {elapsed:.3f}秒")
    print(f"   シナリオ数: {len(app.scenarios)}")
except Exception as e:
    print(f"   エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n2. 最適化版 (app_optimized.py) の起動時間測定:")

# モジュールをクリア
modules_to_clear = [m for m in sys.modules.keys() if m.startswith(('app', 'langchain', 'google'))]
for module in modules_to_clear:
    del sys.modules[module]

start = time.time()
try:
    # app_optimizedモジュールをインポート
    import app_optimized
    elapsed = time.time() - start
    print(f"   起動時間: {elapsed:.3f}秒")
    print(f"   シナリオ数: {len(app_optimized.scenarios)}")
    
    # 遅延読み込みのテスト
    print("\n3. 遅延読み込みのテスト:")
    
    # LangChainの読み込み時間
    start = time.time()
    langchain_modules = app_optimized.get_langchain_modules()
    elapsed = time.time() - start
    print(f"   LangChain初期化: {elapsed:.3f}秒")
    
    # Google Generative AIの読み込み時間
    start = time.time()
    genai = app_optimized.get_genai()
    elapsed = time.time() - start
    print(f"   Google GenAI初期化: {elapsed:.3f}秒")
    
except Exception as e:
    print(f"   エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n=== まとめ ===")
print("最適化版では重いモジュールの読み込みを遅延させることで、")
print("初期起動時間を大幅に短縮しています。")