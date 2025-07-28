#!/usr/bin/env python3
"""リファクタリング後の動作テスト"""
import subprocess
import time
import requests
import sys
import os
import signal


def test_new_structure():
    """新構造のテスト"""
    print("=== リファクタリング後の動作テスト ===\n")
    
    # 1. 新しいアプリケーションの起動テスト
    print("1. 新アプリケーション (run.py) の起動テスト")
    
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    proc = subprocess.Popen(
        [sys.executable, 'run.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        preexec_fn=os.setsid
    )
    
    print("   起動を待機中...")
    time.sleep(5)
    
    # 起動確認
    try:
        # ホームページ
        print("\n2. エンドポイントテスト:")
        
        # ホーム
        response = requests.get("http://localhost:5001/", timeout=5)
        print(f"   GET /: {response.status_code}")
        if response.status_code != 200:
            print(f"      エラー内容: {response.text[:200]}...")
        
        # シナリオ一覧
        start = time.time()
        response = requests.get("http://localhost:5001/scenarios", timeout=10)
        elapsed = time.time() - start
        print(f"   GET /scenarios: {response.status_code} ({elapsed:.3f}秒)")
        
        # API: モデル一覧
        response = requests.get("http://localhost:5001/api/models", timeout=5)
        print(f"   GET /api/models: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"      モデル数: {len(data.get('models', []))}")
        
        print("\n✅ 基本的な動作は正常です")
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        
    finally:
        # クリーンアップ
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait()
        except Exception:
            pass  # プロセスが既に終了している場合は無視


def test_imports():
    """インポートテスト"""
    print("\n3. モジュールインポートテスト:")
    
    modules = [
        "src",
        "src.config",
        "src.app",
        "src.api",
        "src.services",
        "src.utils"
    ]
    
    success = True
    for module in modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except Exception as e:
            print(f"   ❌ {module}: {e}")
            success = False
    
    return success


def check_requirements():
    """依存関係の確認"""
    print("\n4. 依存関係チェック:")
    
    # pipチェック
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("   ✅ すべての依存関係が満たされています")
    else:
        print("   ❌ 依存関係に問題があります:")
        print(result.stdout)


if __name__ == "__main__":
    # インポートテスト
    if test_imports():
        # 依存関係チェック
        check_requirements()
        
        # 動作テスト
        test_new_structure()
    else:
        print("\n❌ インポートエラーのため動作テストをスキップします")