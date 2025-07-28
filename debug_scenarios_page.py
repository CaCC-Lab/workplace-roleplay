#!/usr/bin/env python3
"""シナリオ一覧ページのデバッグツール"""
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import subprocess
import os
import signal

def test_with_selenium():
    """Seleniumを使用してブラウザの挙動を確認"""
    print("=== Seleniumでブラウザテスト ===\n")
    
    # アプリケーションの起動
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    proc = subprocess.Popen(
        ['python', 'run.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        preexec_fn=os.setsid
    )
    
    print("アプリケーション起動中...")
    time.sleep(5)
    
    try:
        # Chrome WebDriverの設定
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # ヘッドレスモード
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        
        print("\n1. シナリオ一覧ページへアクセス")
        start_time = time.time()
        driver.get("http://localhost:5001/scenarios")
        
        # ページロード待機
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            load_time = time.time() - start_time
            print(f"   ページロード時間: {load_time:.3f}秒")
            
            # JavaScriptエラーの確認
            logs = driver.get_log('browser')
            if logs:
                print("\n2. ブラウザコンソールログ:")
                for log in logs:
                    print(f"   [{log['level']}] {log['message']}")
            else:
                print("\n2. ブラウザコンソールエラーなし")
            
            # ページタイトルの確認
            print(f"\n3. ページタイトル: {driver.title}")
            
            # 要素の存在確認
            try:
                scenarios_container = driver.find_element(By.ID, "chat-container")
                print("4. メインコンテナ: 存在")
            except:
                print("4. メインコンテナ: 見つかりません")
            
            # JavaScriptの実行時間を測定
            js_start = time.time()
            driver.execute_script("return document.readyState")
            js_time = time.time() - js_start
            print(f"5. JavaScript実行時間: {js_time:.3f}秒")
            
        except Exception as e:
            print(f"\n❌ ページロードエラー: {e}")
            
    finally:
        driver.quit()
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()


def test_api_endpoints():
    """API エンドポイントの応答時間を確認"""
    print("\n=== APIエンドポイントテスト ===\n")
    
    endpoints = [
        "/api/models",
        "/api/scenarios",  # もし存在すれば
    ]
    
    for endpoint in endpoints:
        try:
            start = time.time()
            response = requests.get(f"http://localhost:5001{endpoint}", timeout=10)
            elapsed = time.time() - start
            print(f"{endpoint}: {response.status_code} ({elapsed:.3f}秒)")
        except requests.exceptions.RequestException as e:
            print(f"{endpoint}: エラー - {e}")


def analyze_template_performance():
    """テンプレートレンダリングのパフォーマンスを分析"""
    print("\n=== テンプレートパフォーマンス分析 ===\n")
    
    # 実際のアプリケーションでテンプレートをレンダリング
    from src.app import create_app
    from flask import render_template_string
    
    app = create_app()
    
    with app.app_context():
        # シンプルなテンプレートのレンダリング時間
        simple_template = "<h1>Test</h1>"
        start = time.time()
        render_template_string(simple_template)
        simple_time = time.time() - start
        print(f"シンプルテンプレート: {simple_time:.3f}秒")
        
        # 実際のテンプレートのレンダリング時間
        try:
            start = time.time()
            from flask import render_template
            result = render_template("scenarios_list.html", scenarios={}, models=[])
            template_time = time.time() - start
            print(f"scenarios_list.html: {template_time:.3f}秒")
        except Exception as e:
            print(f"scenarios_list.html: エラー - {e}")


if __name__ == "__main__":
    print("シナリオ一覧ページのパフォーマンス調査\n")
    
    # APIテスト
    test_api_endpoints()
    
    # テンプレート分析
    analyze_template_performance()
    
    # Seleniumテスト（必要に応じて）
    # test_with_selenium()