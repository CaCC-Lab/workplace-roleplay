#!/usr/bin/env python
"""
音声スタイル制御のテストスクリプト
"""

import requests
import json
import base64
import time

# APIエンドポイント
BASE_URL = "http://localhost:5001"

def test_emotion_styles():
    """感情ごとの音声スタイルをテスト"""
    print("=== 感情スタイルのテスト ===\n")
    
    # テストする感情とサンプルテキスト
    emotion_tests = [
        {
            "emotion": "happy",
            "text": "わあ、素晴らしいニュースですね！今日は本当に最高の一日です！",
            "description": "楽しい・嬉しい"
        },
        {
            "emotion": "sad",
            "text": "残念ですが、今回はうまくいきませんでした。少し悲しいです。",
            "description": "悲しい・寂しい"
        },
        {
            "emotion": "excited",
            "text": "すごい！ついに成功しました！みんなに早く伝えたいです！",
            "description": "興奮・ワクワク"
        },
        {
            "emotion": "worried",
            "text": "本当に大丈夫でしょうか...少し心配になってきました。",
            "description": "心配・不安"
        },
        {
            "emotion": "tired",
            "text": "ふぅ...今日は本当に疲れました。もう少し休憩が必要です。",
            "description": "疲れ・眠い"
        },
        {
            "emotion": "professional",
            "text": "お忙しいところ恐れ入ります。本日の会議についてご連絡いたします。",
            "description": "ビジネス・丁寧"
        },
        {
            "emotion": "whisper",
            "text": "しーっ...静かに...誰かが近くにいるみたいです...",
            "description": "ささやき"
        }
    ]
    
    for test in emotion_tests:
        print(f"感情: {test['emotion']} ({test['description']})")
        print(f"テキスト: {test['text']}")
        
        # TTSリクエスト
        response = requests.post(
            f"{BASE_URL}/api/tts",
            headers={"Content-Type": "application/json"},
            json={
                "text": test['text'],
                "emotion": test['emotion']
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 成功: 音声={data.get('voice', 'unknown')}, プロバイダー={data.get('provider', 'unknown')}")
            
            # 音声ファイルを保存
            audio_base64 = data['audio']
            audio_bytes = base64.b64decode(audio_base64)
            filename = f"test_emotion_{test['emotion']}.{data['format']}"
            with open(filename, "wb") as f:
                f.write(audio_bytes)
            print(f"  → 保存: {filename}")
        else:
            print(f"✗ エラー: {response.status_code}")
            print(f"  {response.json()}")
        
        print()
        time.sleep(1)  # API負荷軽減のため

def test_custom_styles():
    """カスタムスタイルのテスト"""
    print("\n=== カスタムスタイルのテスト ===\n")
    
    custom_tests = [
        {
            "text": "昔々、あるところに、優しい心を持った若者が住んでいました。",
            "style": "in a storytelling manner",
            "description": "物語風"
        },
        {
            "text": "本日午後3時、重要な発表がありました。詳細は以下の通りです。",
            "style": "like a news anchor",
            "description": "ニュースキャスター風"
        },
        {
            "text": "次のスライドをご覧ください。ここがポイントになります。",
            "style": "as if giving a presentation",
            "description": "プレゼンテーション風"
        }
    ]
    
    for test in custom_tests:
        print(f"スタイル: {test['style']} ({test['description']})")
        print(f"テキスト: {test['text']}")
        
        # TTSリクエスト
        response = requests.post(
            f"{BASE_URL}/api/tts",
            headers={"Content-Type": "application/json"},
            json={
                "text": test['text'],
                "style": test['style']
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 成功: 音声={data.get('voice', 'unknown')}")
            
            # 音声ファイルを保存
            audio_base64 = data['audio']
            audio_bytes = base64.b64decode(audio_base64)
            filename = f"test_style_{test['description']}.{data['format']}"
            with open(filename, "wb") as f:
                f.write(audio_bytes)
            print(f"  → 保存: {filename}")
        else:
            print(f"✗ エラー: {response.status_code}")
            print(f"  {response.json()}")
        
        print()
        time.sleep(1)

def test_get_styles():
    """利用可能なスタイル一覧を取得"""
    print("=== 利用可能なスタイル一覧 ===\n")
    
    response = requests.get(f"{BASE_URL}/api/tts/styles")
    
    if response.status_code == 200:
        styles = response.json()
        
        print("感情スタイル:")
        for emotion in styles['emotions']:
            print(f"  - {emotion['id']}: {emotion['name']} - {emotion['description']}")
        
        print("\nカスタムスタイル例:")
        for style in styles['custom_styles']:
            print(f"  - {style['example']}: {style['description']}")
    else:
        print(f"エラー: {response.status_code}")
        print(response.json())

def main():
    """メインテスト関数"""
    print("音声スタイル制御テスト開始\n")
    
    # スタイル一覧を取得
    test_get_styles()
    print("\n" + "="*50 + "\n")
    
    # 感情スタイルをテスト
    test_emotion_styles()
    
    # カスタムスタイルをテスト
    test_custom_styles()
    
    print("\nテスト完了")

if __name__ == "__main__":
    main()