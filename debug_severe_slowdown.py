#!/usr/bin/env python3
"""
分単位の深刻な遅延問題を調査
"""
import time
import threading
import psutil
import os
import traceback
import sys

print("=== 深刻な遅延問題の調査 ===\n")

# 1. シナリオデータの読み込みを詳細にチェック
print("1. シナリオ読み込みの詳細調査:")
print("-" * 50)

start_total = time.time()
try:
    from scenarios import load_scenarios
    print("scenarios モジュールのインポート完了")
    
    # load_scenarios の実行を監視
    start = time.time()
    print("load_scenarios() を実行中...")
    
    # タイムアウト付きで実行
    result = None
    exception = None
    
    def load_with_timeout():
        global result, exception
        try:
            result = load_scenarios()
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=load_with_timeout)
    thread.daemon = True
    thread.start()
    
    # 10秒ごとに進捗を表示
    elapsed = 0
    while thread.is_alive() and elapsed < 300:  # 最大5分
        time.sleep(10)
        elapsed += 10
        print(f"  {elapsed}秒経過... まだ実行中")
        
        # メモリ使用量をチェック
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / 1024 / 1024
        print(f"  メモリ使用量: {mem:.2f} MB")
    
    if thread.is_alive():
        print("  ⚠️ 5分経過してもまだ実行中！")
    else:
        elapsed = time.time() - start
        print(f"  完了時間: {elapsed:.2f}秒")
        if result:
            print(f"  シナリオ数: {len(result)}")
        if exception:
            print(f"  エラー: {exception}")
            traceback.print_exception(type(exception), exception, exception.__traceback__)
            
except Exception as e:
    print(f"エラー: {e}")
    traceback.print_exc()

# 2. ファイルシステムの確認
print("\n2. シナリオファイルの確認:")
print("-" * 50)

scenarios_dir = "scenarios/data"
if os.path.exists(scenarios_dir):
    files = os.listdir(scenarios_dir)
    yaml_files = [f for f in files if f.endswith('.yaml')]
    print(f"YAMLファイル数: {len(yaml_files)}")
    
    # 各ファイルのサイズをチェック
    total_size = 0
    for f in yaml_files:
        path = os.path.join(scenarios_dir, f)
        size = os.path.getsize(path)
        total_size += size
        if size > 100000:  # 100KB以上
            print(f"  大きなファイル: {f} ({size/1024:.2f} KB)")
    
    print(f"総ファイルサイズ: {total_size/1024:.2f} KB")
else:
    print("scenarios/data ディレクトリが見つかりません")

# 3. ネットワーク接続の確認
print("\n3. ネットワーク関連の確認:")
print("-" * 50)

# 環境変数をチェック
api_keys = {
    "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY"),
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
    "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY")
}

for key, value in api_keys.items():
    if value:
        print(f"{key}: 設定済み（長さ: {len(value)}）")
    else:
        print(f"{key}: 未設定")

# 4. config.py の確認
print("\n4. 設定ファイルの確認:")
print("-" * 50)

try:
    from config import get_cached_config
    config = get_cached_config()
    
    # 特に遅延に関係しそうな設定をチェック
    print(f"DEBUG: {getattr(config, 'DEBUG', 'Unknown')}")
    print(f"DATABASE_URL: {'設定あり' if getattr(config, 'DATABASE_URL', None) else '未設定'}")
    print(f"SESSION_TYPE: {getattr(config, 'SESSION_TYPE', 'Unknown')}")
    
    # API関連の設定
    if hasattr(config, 'API_TIMEOUT'):
        print(f"API_TIMEOUT: {config.API_TIMEOUT}")
    
except Exception as e:
    print(f"config読み込みエラー: {e}")

print("\n=== 推測される原因 ===")
print("1. ネットワーク接続のタイムアウト（API初期化など）")
print("2. 大量のファイルI/O処理")
print("3. 無限ループや再帰的な処理")
print("4. 外部APIへの同期的な接続試行")
print("5. データベース接続の長時間タイムアウト")