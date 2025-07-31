#!/usr/bin/env python3
"""
シナリオモードのパフォーマンスをベンチマーク
"""
import time
import subprocess
import sys
import os
import signal
import requests
from datetime import datetime

def start_app(app_file):
    """アプリケーションを起動"""
    print(f"起動中: {app_file}")
    process = subprocess.Popen(
        [sys.executable, app_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    
    # 起動を待つ
    time.sleep(5)
    
    # 起動確認
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        if response.status_code == 200:
            print("✅ アプリケーションが起動しました")
            return process
        else:
            print(f"❌ 起動失敗: ステータスコード {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 起動失敗: {e}")
        return None

def stop_app(process):
    """アプリケーションを停止"""
    if process:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait()
        print("アプリケーションを停止しました")

def measure_response_time(url, description):
    """レスポンス時間を測定"""
    try:
        start = time.time()
        response = requests.get(url, timeout=30)
        elapsed = time.time() - start
        
        print(f"{description}:")
        print(f"  ステータス: {response.status_code}")
        print(f"  レスポンス時間: {elapsed:.3f}秒")
        print(f"  コンテンツサイズ: {len(response.text)} bytes")
        
        return elapsed, response.status_code == 200
    except Exception as e:
        print(f"{description}: エラー - {e}")
        return -1, False

def main():
    print("=== シナリオモード パフォーマンスベンチマーク ===")
    print(f"実行時刻: {datetime.now()}")
    print()
    
    # 1. 通常のapp.pyのテスト
    print("1. 通常版 (app.py) のテスト")
    process_normal = start_app("app.py")
    if process_normal:
        # ホームページ
        measure_response_time("http://localhost:5000/", "ホームページ")
        
        # シナリオ一覧
        time1, success1 = measure_response_time("http://localhost:5000/scenarios", "シナリオ一覧ページ")
        
        # API呼び出し
        time2, success2 = measure_response_time("http://localhost:5000/api/models", "モデル一覧API")
        
        stop_app(process_normal)
        print()
    
    # 2. 最適化版のテスト
    print("2. 最適化版 (app_optimized.py) のテスト")
    process_optimized = start_app("app_optimized.py")
    if process_optimized:
        # ホームページ
        measure_response_time("http://localhost:5000/", "ホームページ")
        
        # シナリオ一覧
        time3, success3 = measure_response_time("http://localhost:5000/scenarios", "シナリオ一覧ページ")
        
        # API呼び出し
        time4, success4 = measure_response_time("http://localhost:5000/api/models", "モデル一覧API")
        
        stop_app(process_optimized)
        print()
    
    # 3. 結果サマリー
    print("=== 結果サマリー ===")
    if process_normal and process_optimized:
        print("シナリオ一覧ページの応答時間:")
        print(f"  通常版: {time1:.3f}秒")
        print(f"  最適化版: {time3:.3f}秒")
        if time1 > 0 and time3 > 0:
            improvement = ((time1 - time3) / time1) * 100
            print(f"  改善率: {improvement:.1f}%")
            print(f"  高速化: {time1/time3:.1f}倍")

if __name__ == "__main__":
    main()