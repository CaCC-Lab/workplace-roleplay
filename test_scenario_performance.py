#!/usr/bin/env python3
"""
シナリオモードのパフォーマンステスト
"""
import time
import requests
import psutil
import os

# プロセスのメモリ使用量を監視
process = psutil.Process(os.getpid())

print("=== シナリオモードパフォーマンステスト ===\n")

# 1. シナリオ一覧ページのロード時間を測定
print("1. シナリオ一覧ページのロード時間:")
start_time = time.time()
try:
    response = requests.get("http://localhost:5001/scenarios", timeout=30)
    elapsed = time.time() - start_time
    print(f"   ステータスコード: {response.status_code}")
    print(f"   レスポンスサイズ: {len(response.content) / 1024:.2f} KB")
    print(f"   ロード時間: {elapsed:.2f} 秒")
    
    # レスポンスに含まれるシナリオ数をカウント
    scenario_count = response.text.count('scenario-card')
    print(f"   シナリオ数: {scenario_count}")
    
except requests.exceptions.Timeout:
    print("   エラー: タイムアウト（30秒以上）")
except Exception as e:
    print(f"   エラー: {e}")

# 2. 個別シナリオページのロード時間
print("\n2. 個別シナリオページのロード時間:")
scenario_ids = ["scenario1", "scenario2", "scenario3"]

for scenario_id in scenario_ids:
    start_time = time.time()
    try:
        response = requests.get(f"http://localhost:5001/scenario/{scenario_id}", timeout=10)
        elapsed = time.time() - start_time
        print(f"   {scenario_id}: {elapsed:.2f} 秒 (ステータス: {response.status_code})")
    except Exception as e:
        print(f"   {scenario_id}: エラー - {e}")

# 3. 静的ファイルのロード時間
print("\n3. 静的ファイルのロード時間:")
static_files = [
    "/static/css/style.css",
    "/static/js/model-selection.js",
    "/static/js/scenario.js"
]

for file_path in static_files:
    start_time = time.time()
    try:
        response = requests.get(f"http://localhost:5001{file_path}", timeout=5)
        elapsed = time.time() - start_time
        print(f"   {file_path}: {elapsed:.2f} 秒")
    except Exception as e:
        print(f"   {file_path}: エラー - {e}")

# 4. メモリ使用量
print(f"\nメモリ使用量: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# 5. サーバーのプロセス情報を確認
print("\n5. Flaskプロセスの確認:")
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
    try:
        if 'python' in proc.info['name'] and 'app.py' in ' '.join(proc.cmdline()):
            print(f"   PID: {proc.info['pid']}")
            print(f"   CPU使用率: {proc.cpu_percent(interval=1)}%")
            print(f"   メモリ使用率: {proc.info['memory_percent']:.2f}%")
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass