#!/usr/bin/env python3
"""
app.py起動時の詳細なトレース（分単位の遅延を特定）
"""
import time
import sys
import os
import subprocess
import threading
import signal

print("=== app.py 起動トレース ===\n")

# 環境変数を設定
env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'  # 出力をバッファリングしない

# app.pyをサブプロセスで起動
print("app.pyを起動中...")
start_time = time.time()

proc = subprocess.Popen(
    [sys.executable, 'app.py'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    env=env,
    text=True,
    bufsize=1
)

# 出力を監視
last_output_time = time.time()
timeout_seconds = 10
lines_buffer = []

def check_timeout():
    """タイムアウトチェック"""
    while proc.poll() is None:
        time.sleep(1)
        current_time = time.time()
        elapsed = current_time - start_time
        no_output_time = current_time - last_output_time
        
        if no_output_time > timeout_seconds:
            print(f"\n⚠️ {no_output_time:.0f}秒間出力なし！（合計経過時間: {elapsed:.0f}秒）")
            print("最後の出力:")
            for line in lines_buffer[-5:]:
                print(f"  > {line}")
            print("\nプロセスがハングしている可能性があります。")
            
            # さらに30秒待つ
            time.sleep(30)
            if proc.poll() is None:
                print("\n❌ 30秒追加で待機しましたが、まだ応答がありません。")
                print("プロセスを強制終了します。")
                proc.terminate()
                time.sleep(2)
                if proc.poll() is None:
                    proc.kill()
                break

timeout_thread = threading.Thread(target=check_timeout)
timeout_thread.daemon = True
timeout_thread.start()

# 出力を読み取り
print("\n出力:")
print("-" * 60)

try:
    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        
        if line:
            line = line.rstrip()
            current_time = time.time()
            elapsed = current_time - start_time
            last_output_time = current_time
            
            # タイムスタンプ付きで出力
            print(f"[{elapsed:6.2f}s] {line}")
            lines_buffer.append(line)
            
            # 重要なイベントを検出
            if "Loaded" in line and "scenarios" in line:
                print(f"         ^ シナリオ読み込み完了 ({elapsed:.2f}秒)")
            elif "Running on" in line:
                print(f"         ^ サーバー起動完了 ({elapsed:.2f}秒)")
            elif "WARNING" in line or "Error" in line:
                print(f"         ^ ⚠️ 警告/エラー検出")
                
        # 60秒以上かかっている場合
        if elapsed > 60:
            print(f"\n⚠️ 起動に{elapsed:.0f}秒以上かかっています！")
            break
            
except KeyboardInterrupt:
    print("\n\n中断されました。")
    proc.terminate()

# 終了を待つ
proc.wait()
total_time = time.time() - start_time

print("-" * 60)
print(f"\n総起動時間: {total_time:.2f}秒")

if total_time > 30:
    print("\n⚠️ 異常に長い起動時間です！")
    print("\n考えられる原因:")
    print("1. データベース接続のタイムアウト")
    print("2. 外部APIへの接続試行")
    print("3. DNSルックアップの遅延")
    print("4. ファイルシステムの問題")
    print("5. 依存パッケージの初期化問題")