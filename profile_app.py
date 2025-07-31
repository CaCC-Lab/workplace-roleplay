#!/usr/bin/env python3
"""
アプリケーションのボトルネックを特定するプロファイリングツール
"""
import time
import traceback
import psutil
import os

print("=== アプリケーションプロファイリング ===\n")

# 1. インポート時間の測定
print("1. モジュールインポート時間の測定:")
module_times = {}

modules_to_test = [
    "flask",
    "google.generativeai",
    "langchain",
    "scenarios",
    "strength_analyzer",
    "api_key_manager",
    "database",
    "models",
    "service_layer"
]

for module_name in modules_to_test:
    start = time.time()
    try:
        if module_name == "google.generativeai":
            import google.generativeai
        elif module_name == "langchain":
            from langchain.memory import ConversationBufferMemory
        elif module_name == "scenarios":
            from scenarios import load_scenarios
        elif module_name == "strength_analyzer":
            from strength_analyzer import analyze_user_strengths
        elif module_name == "api_key_manager":
            from api_key_manager import get_google_api_key
        elif module_name == "database":
            from database import init_database
        elif module_name == "models":
            from models import User, db
        elif module_name == "service_layer":
            from service_layer import ScenarioService
        else:
            __import__(module_name)
        elapsed = time.time() - start
        module_times[module_name] = elapsed
        print(f"   {module_name}: {elapsed:.3f}秒")
    except Exception as e:
        print(f"   {module_name}: エラー - {str(e)}")
        module_times[module_name] = -1

# 2. シナリオデータの読み込み時間
print("\n2. シナリオデータの読み込み:")
start = time.time()
try:
    from scenarios import load_scenarios
    scenarios = load_scenarios()
    elapsed = time.time() - start
    print(f"   シナリオ数: {len(scenarios)}")
    print(f"   読み込み時間: {elapsed:.3f}秒")
    
    # 各シナリオのサイズをチェック
    total_size = 0
    for scenario_id, scenario_data in scenarios.items():
        scenario_size = len(str(scenario_data))
        total_size += scenario_size
    print(f"   総データサイズ: {total_size / 1024:.2f} KB")
except Exception as e:
    print(f"   エラー: {e}")
    traceback.print_exc()

# 3. Flask設定の確認
print("\n3. Flask設定の確認:")
try:
    from config import get_cached_config
    config = get_cached_config()
    print(f"   DEBUG: {getattr(config, 'DEBUG', 'Unknown')}")
    print(f"   SECRET_KEY長: {len(getattr(config, 'SECRET_KEY', ''))}")
    print(f"   SESSION_TYPE: {getattr(config, 'SESSION_TYPE', 'Unknown')}")
except Exception as e:
    print(f"   エラー: {e}")

# 4. データベース接続の確認
print("\n4. データベース接続テスト:")
start = time.time()
try:
    use_db = os.environ.get("USE_DATABASE", "false").lower() == "true"
    if use_db:
        from database import init_database
        from flask import Flask
        test_app = Flask(__name__)
        test_app.config['TESTING'] = True
        db_available = init_database(test_app)
        elapsed = time.time() - start
        print(f"   データベース利用可能: {db_available}")
        print(f"   接続時間: {elapsed:.3f}秒")
    else:
        print("   データベースは無効化されています（USE_DATABASE=false）")
except Exception as e:
    print(f"   エラー: {e}")

# 5. メモリ使用量
print(f"\n5. メモリ使用量:")
process = psutil.Process(os.getpid())
print(f"   現在: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# 6. ボトルネックの特定
print("\n=== ボトルネック分析 ===")
slow_modules = [(name, time) for name, time in module_times.items() if time > 0.5]
if slow_modules:
    print("遅いモジュール（0.5秒以上）:")
    for name, time in sorted(slow_modules, key=lambda x: x[1], reverse=True):
        print(f"   - {name}: {time:.3f}秒")
else:
    print("特に遅いモジュールは見つかりませんでした。")

# 7. 推奨事項
print("\n=== 推奨事項 ===")
if any(time > 1.0 for time in module_times.values()):
    print("- 重いモジュールの遅延インポートを検討してください")
if 'langchain' in module_times and module_times['langchain'] > 0.5:
    print("- LangChainの初期化を遅延させることを検討してください")
if not os.environ.get("USE_DATABASE") == "false":
    print("- データベースを無効化してパフォーマンスを向上させることを検討してください")