#!/usr/bin/env python3
"""
app.pyのインポート順序と時間を詳細に調査
"""
import sys
import time
import builtins
from datetime import datetime

# インポートフック
original_import = builtins.__import__
import_times = []
start_time = time.time()

def timed_import(name, *args, **kwargs):
    """インポートをトレース"""
    import_start = time.time()
    
    # 実際のインポート
    module = original_import(name, *args, **kwargs)
    
    # 時間を記録
    import_time = time.time() - import_start
    elapsed_total = time.time() - start_time
    
    # 0.1秒以上かかったものだけ記録
    if import_time > 0.1:
        import_times.append({
            'module': name,
            'time': import_time,
            'elapsed': elapsed_total
        })
        print(f"[{elapsed_total:6.2f}s] Import {name}: {import_time:.3f}s")
        
        # 10秒以上かかったら警告
        if import_time > 10:
            print(f"⚠️  WARNING: {name} took {import_time:.0f} seconds to import!")
    
    return module

# インポートフックを設定
builtins.__import__ = timed_import

print("=== app.py インポート分析 ===")
print(f"開始時刻: {datetime.now()}")
print("-" * 60)

try:
    # app.pyをインポート
    print("\napp.pyをインポート中...")
    import app
    
    total_time = time.time() - start_time
    print("-" * 60)
    print(f"\n総インポート時間: {total_time:.2f}秒")
    
    # 遅いインポートのサマリー
    print("\n遅いインポート TOP 10:")
    sorted_imports = sorted(import_times, key=lambda x: x['time'], reverse=True)
    for i, item in enumerate(sorted_imports[:10]):
        print(f"{i+1}. {item['module']}: {item['time']:.3f}秒 (累計: {item['elapsed']:.2f}秒)")
        
except Exception as e:
    print(f"\nエラー: {e}")
    import traceback
    traceback.print_exc()
finally:
    # インポートフックを元に戻す
    builtins.__import__ = original_import

print("\n=== 分析結果 ===")
if any(item['time'] > 30 for item in import_times):
    print("⚠️  30秒以上かかっているインポートがあります！")
    print("これが分単位の遅延の原因です。")
elif any(item['time'] > 10 for item in import_times):
    print("⚠️  10秒以上かかっているインポートがあります。")
    print("ネットワーク接続やAPI初期化に問題がある可能性があります。")