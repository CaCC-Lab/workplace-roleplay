#!/usr/bin/env python3
"""
アプリケーション起動時の詳細トレース
"""
import time
import sys
import os
import importlib.util

# トレース開始
print("=== アプリケーション起動トレース ===\n")
start_time = time.time()

def trace_import(module_name, indent=0):
    """モジュールのインポートをトレース"""
    prefix = "  " * indent
    print(f"{prefix}[{time.time() - start_time:.3f}s] Importing {module_name}...")
    
    try:
        # 既にインポート済みの場合はスキップ
        if module_name in sys.modules:
            print(f"{prefix}  (already imported)")
            return sys.modules[module_name]
        
        # インポート開始
        import_start = time.time()
        module = importlib.import_module(module_name)
        import_time = time.time() - import_start
        
        print(f"{prefix}  ✓ {module_name} imported in {import_time:.3f}s")
        
        # 10秒以上かかったら警告
        if import_time > 10:
            print(f"{prefix}  ⚠️ WARNING: {module_name} took {import_time:.3f}s to import!")
        
        return module
    except Exception as e:
        print(f"{prefix}  ✗ Failed to import {module_name}: {e}")
        return None

# 主要なインポートをトレース
print("1. 基本モジュールのインポート:")
trace_import("os")
trace_import("sys")
trace_import("time")

print("\n2. Flaskと関連モジュール:")
trace_import("flask")
trace_import("flask_session")
trace_import("flask_login")

print("\n3. 設定関連:")
trace_import("dotenv")
trace_import("config")

print("\n4. シナリオモジュール:")
scenarios_module = trace_import("scenarios")

# load_scenarios の実行をトレース
if scenarios_module:
    print("\n5. load_scenarios()の実行:")
    print(f"[{time.time() - start_time:.3f}s] Calling load_scenarios()...")
    
    # 実行開始
    load_start = time.time()
    
    # 1秒ごとに進捗を表示するためのスレッド
    import threading
    stop_monitoring = False
    
    def monitor_progress():
        elapsed = 0
        while not stop_monitoring:
            time.sleep(1)
            elapsed += 1
            if not stop_monitoring:
                print(f"  ... {elapsed}秒経過 ...")
    
    monitor_thread = threading.Thread(target=monitor_progress)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    try:
        scenarios = scenarios_module.load_scenarios()
        load_time = time.time() - load_start
        stop_monitoring = True
        monitor_thread.join(timeout=0.5)
        
        print(f"  ✓ load_scenarios() completed in {load_time:.3f}s")
        print(f"  シナリオ数: {len(scenarios)}")
        
        if load_time > 5:
            print(f"  ⚠️ WARNING: load_scenarios() took {load_time:.3f}s!")
            
    except Exception as e:
        stop_monitoring = True
        print(f"  ✗ load_scenarios() failed: {e}")
        import traceback
        traceback.print_exc()

print("\n6. その他の重いモジュール:")
trace_import("langchain")
trace_import("google.generativeai")

print(f"\n=== 総起動時間: {time.time() - start_time:.3f}秒 ===")

# 追加の診断情報
print("\n追加診断:")
print("-" * 50)

# プロセスのファイルディスクリプタ数をチェック
try:
    import psutil
    process = psutil.Process(os.getpid())
    print(f"開いているファイル数: {len(process.open_files())}")
    print(f"ネットワーク接続数: {len(process.connections())}")
except:
    pass

# 環境変数で何か特殊な設定がないかチェック
suspicious_env_vars = [
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
    "SSL_CERT_FILE", "SSL_CERT_DIR"
]

print("\nプロキシ/SSL関連の環境変数:")
for var in suspicious_env_vars:
    value = os.environ.get(var)
    if value:
        print(f"  {var}: {value}")