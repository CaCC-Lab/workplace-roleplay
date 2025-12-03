#!/usr/bin/env python3
"""音声事前生成機能のテストスクリプト"""

import asyncio
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def test_preload_tts():
    """音声事前生成機能をテスト"""

    # Chromeオプションの設定
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # ヘッドレスモード
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # WebDriverの初期化
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        print("1. トップページにアクセス")
        driver.get("http://localhost:5001")
        time.sleep(2)

        # モデル選択（Gemini Pro）
        print("2. モデルを選択")
        model_select = driver.find_element(By.ID, "model-select")
        driver.execute_script("arguments[0].value = 'gemini-pro'", model_select)
        driver.execute_script("localStorage.setItem('selectedModel', 'gemini-pro')")

        print("3. シナリオ一覧ページへ移動")
        scenario_link = driver.find_element(By.LINK_TEXT, "シナリオ練習")
        scenario_link.click()
        time.sleep(2)

        print("4. シナリオ1を選択")
        scenario1_link = driver.find_element(By.XPATH, "//h3[contains(text(), '新しいタスクの依頼を断る')]")
        scenario1_link.click()
        time.sleep(3)

        print("5. 初期メッセージの音声が事前生成されているか確認")
        # コンソールログを確認
        logs = driver.get_log("browser")
        for log in logs:
            if "音声" in log["message"]:
                print(f"  Console: {log['message']}")

        # TTSボタンが存在し、tts-readyクラスが付いているか確認
        wait = WebDriverWait(driver, 10)
        tts_button = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "tts-button")))

        # JavaScriptでクラスを確認
        has_ready_class = driver.execute_script(
            "return document.querySelector('.tts-button').classList.contains('tts-ready')"
        )
        print(f"6. TTSボタンにtts-readyクラスがある: {has_ready_class}")

        # キャッシュの状態を確認
        cache_size = driver.execute_script("return audioCache.size")
        print(f"7. 音声キャッシュのサイズ: {cache_size}")

        # メッセージを送信
        print("8. メッセージを送信")
        message_input = driver.find_element(By.ID, "message-input")
        message_input.send_keys("申し訳ありませんが、現在のプロジェクトが忙しく...")

        send_button = driver.find_element(By.ID, "send-button")
        send_button.click()
        time.sleep(5)  # 応答を待つ

        # 新しいメッセージの音声が事前生成されているか確認
        print("9. 新しいメッセージの音声事前生成を確認")
        logs = driver.get_log("browser")
        for log in logs:
            if "音声" in log["message"]:
                print(f"  Console: {log['message']}")

        # 全てのTTSボタンを確認
        tts_buttons = driver.find_elements(By.CLASS_NAME, "tts-button")
        print(f"10. TTSボタンの総数: {len(tts_buttons)}")

        for i, button in enumerate(tts_buttons):
            has_ready = driver.execute_script("return arguments[0].classList.contains('tts-ready')", button)
            print(f"   ボタン{i+1}: tts-ready={has_ready}")

        # キャッシュの最終状態
        final_cache_size = driver.execute_script("return audioCache.size")
        print(f"11. 最終的な音声キャッシュサイズ: {final_cache_size}")

        print("\nテスト完了！")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()

    finally:
        driver.quit()


if __name__ == "__main__":
    print("音声事前生成機能のテストを開始します...\n")
    test_preload_tts()
