#!/usr/bin/env python3
"""
修正版app.pyのテスト
"""
import time
import subprocess
import sys
import os
import requests
import signal

print("=== 修正版app.pyのテスト ===\n")

# app.pyを起動
print("1. app.pyを起動中...")
env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'

proc = subprocess.Popen(
    [sys.executable, 'app.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    env=env,
    text=True,
    preexec_fn=os.setsid
)

# 起動を待つ
print("   サーバーの起動を待機中...")
time.sleep(5)

# シナリオページへのアクセステスト
print("\n2. シナリオ一覧ページへアクセス:")
start_time = time.time()

try:
    # タイムアウト30秒で実行
    response = requests.get("http://localhost:5001/scenarios", timeout=30)
    elapsed = time.time() - start_time
    
    print(f"   ✅ 成功!")
    print(f"   応答時間: {elapsed:.3f}秒")
    print(f"   ステータス: {response.status_code}")
    
    if elapsed < 1:
        print(f"\n   🎉 素晴らしい！1秒以内に応答しました!")
    elif elapsed < 5:
        print(f"\n   ✅ 良好: 5秒以内に応答しました")
    else:
        print(f"\n   ⚠️ まだ遅い: {elapsed:.0f}秒かかりました")
        
except requests.Timeout:
    elapsed = time.time() - start_time
    print(f"   ❌ タイムアウト（30秒）")
    print(f"   まだ問題が残っている可能性があります")
except Exception as e:
    print(f"   ❌ エラー: {e}")

# APIテスト
print("\n3. モデル一覧APIテスト:")
try:
    api_start = time.time()
    response = requests.get("http://localhost:5001/api/models", timeout=10)
    api_elapsed = time.time() - api_start
    
    print(f"   応答時間: {api_elapsed:.3f}秒")
    print(f"   ステータス: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   モデル数: {len(data.get('models', []))}")
except Exception as e:
    print(f"   エラー: {e}")

# クリーンアップ
print("\n4. クリーンアップ中...")
os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
proc.wait()
print("   完了")

print("\n=== 結果サマリー ===")
if 'elapsed' in locals() and elapsed < 5:
    print("✅ 修正は成功しました！シナリオページが高速に表示されるようになりました。")
else:
    print("⚠️ まだパフォーマンスの問題が残っている可能性があります。")