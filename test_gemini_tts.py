#!/usr/bin/env python
"""
Gemini TTS APIのテストスクリプト
"""

import requests
import json
import base64
import wave
import io

# APIエンドポイント
BASE_URL = "http://localhost:5001"

def test_get_voices():
    """利用可能な音声の一覧を取得"""
    print("=== 利用可能な音声の取得 ===")
    response = requests.get(f"{BASE_URL}/api/tts/voices")
    
    if response.status_code == 200:
        voices = response.json()["voices"]
        print(f"利用可能な音声数: {len(voices)}")
        for voice in voices:
            print(f"- {voice['id']}: {voice['name']} ({voice['gender']}) - {voice['provider']}")
    else:
        print(f"エラー: {response.status_code}")
        print(response.json())
    
    return response.status_code == 200

def test_tts(text="こんにちは、音声合成のテストです。", voice="kore"):
    """TTSエンドポイントのテスト"""
    print(f"\n=== TTS テスト ===")
    print(f"テキスト: {text}")
    print(f"音声: {voice}")
    
    # TTSリクエスト
    response = requests.post(
        f"{BASE_URL}/api/tts",
        headers={"Content-Type": "application/json"},
        json={
            "text": text,
            "voice": voice
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"成功: {data['format']}形式, 音声: {data['voice']}, プロバイダー: {data.get('provider', 'unknown')}")
        
        # 音声データのサイズを確認
        audio_base64 = data['audio']
        audio_bytes = base64.b64decode(audio_base64)
        print(f"音声データサイズ: {len(audio_bytes)} bytes")
        
        # WAVファイルとして保存（テスト用）
        output_file = f"test_output_{voice}.{data['format']}"
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        print(f"音声ファイルを保存しました: {output_file}")
        
        # WAVファイルの情報を表示
        if data['format'] == 'wav':
            try:
                with wave.open(output_file, 'rb') as wf:
                    print(f"  チャンネル数: {wf.getnchannels()}")
                    print(f"  サンプル幅: {wf.getsampwidth()} bytes")
                    print(f"  フレームレート: {wf.getframerate()} Hz")
                    print(f"  フレーム数: {wf.getnframes()}")
                    duration = wf.getnframes() / wf.getframerate()
                    print(f"  再生時間: {duration:.2f} 秒")
            except Exception as e:
                print(f"WAVファイル情報の読み取りエラー: {e}")
        
        return True
    else:
        print(f"エラー: {response.status_code}")
        print(response.json())
        return False

def test_different_voices():
    """異なる音声でのテスト"""
    print("\n=== 異なる音声でのテスト ===")
    test_voices = ["kore", "aoede", "puck", "charon"]
    test_text = "おはようございます。今日はいい天気ですね。"
    
    for voice in test_voices:
        print(f"\n音声 '{voice}' でテスト中...")
        success = test_tts(test_text, voice)
        if not success:
            print(f"音声 '{voice}' のテストに失敗しました")

def test_long_text():
    """長いテキストでのテスト"""
    print("\n=== 長いテキストでのテスト ===")
    long_text = """
    本日は職場でのコミュニケーション練習アプリの音声読み上げ機能をテストしています。
    このアプリケーションは、AIを活用したロールプレイシナリオを通じて、
    職場でのコミュニケーションスキルを向上させることを目的としています。
    音声読み上げ機能により、より自然な会話練習が可能になります。
    """.strip().replace("\n", "")
    
    test_tts(long_text, "kore")

def main():
    """メインテスト関数"""
    print("Gemini TTS API テスト開始\n")
    
    # 各テストを実行
    if test_get_voices():
        test_different_voices()
        test_long_text()
    else:
        print("音声リストの取得に失敗しました")
    
    print("\nテスト完了")

if __name__ == "__main__":
    main()