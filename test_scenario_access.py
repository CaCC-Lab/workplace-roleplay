#!/usr/bin/env python3
"""
シナリオページアクセス時の遅延を再現
"""
import time
import subprocess
import sys
import os
import requests
import threading
import signal

def start_app_and_test():
    """アプリを起動してシナリオページにアクセス"""
    print("=== シナリオページアクセステスト ===\n")
    
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
    
    # 起動確認
    try:
        response = requests.get("http://localhost:5001/", timeout=5)
        print(f"   ✓ サーバー起動確認 (ステータス: {response.status_code})")
    except Exception as e:
        print(f"   ✗ サーバー起動失敗: {e}")
        proc.terminate()
        return
    
    # シナリオページへのアクセステスト
    print("\n2. シナリオ一覧ページへアクセス:")
    print("   http://localhost:5001/scenarios")
    
    access_start = time.time()
    last_update = access_start
    completed = False
    response = None
    
    def monitor_request():
        """リクエストの進行状況を監視"""
        nonlocal last_update, completed
        elapsed = 0
        while not completed:
            time.sleep(5)
            elapsed = time.time() - access_start
            if elapsed > 10 and not completed:
                print(f"   ... {elapsed:.0f}秒経過（まだ応答待ち）...")
                
                # 30秒ごとに詳細情報
                if elapsed % 30 < 5:
                    try:
                        # プロセスの状態確認
                        if proc.poll() is None:
                            print("      サーバープロセスは生きています")
                        else:
                            print("      ⚠️ サーバープロセスが終了しています！")
                    except:
                        pass
    
    monitor_thread = threading.Thread(target=monitor_request)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    try:
        # 実際のリクエスト（タイムアウト5分）
        print("   リクエスト送信中...")
        response = requests.get("http://localhost:5001/scenarios", timeout=300)
        completed = True
        elapsed = time.time() - access_start
        
        print(f"\n   ✓ 応答受信!")
        print(f"   ステータスコード: {response.status_code}")
        print(f"   応答時間: {elapsed:.2f}秒")
        print(f"   コンテンツサイズ: {len(response.text)} bytes")
        
        if elapsed > 30:
            print(f"\n   ⚠️ 異常に長い応答時間です！（{elapsed:.0f}秒）")
            
    except requests.Timeout:
        completed = True
        print("\n   ✗ タイムアウト！（5分経過）")
    except Exception as e:
        completed = True
        print(f"\n   ✗ エラー: {e}")
    
    # サーバーログを確認
    print("\n3. サーバーログ（最後の20行）:")
    print("-" * 60)
    
    # ログを取得
    logs = []
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        logs.append(line.rstrip())
        if len(logs) > 100:  # 最大100行保持
            logs.pop(0)
    
    # 最後の20行を表示
    for line in logs[-20:]:
        print(f"   {line}")
    
    # クリーンアップ
    print("\n4. クリーンアップ中...")
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    proc.wait()
    print("   完了")

if __name__ == "__main__":
    try:
        start_app_and_test()
    except KeyboardInterrupt:
        print("\n\n中断されました。")
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()