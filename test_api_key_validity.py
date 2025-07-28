#!/usr/bin/env python3
"""
API Keyの有効性をテスト
"""
import os
import time
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

print("=== API Key有効性テスト ===\n")

# API Keyの取得
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    print(f"API Key: 設定済み（長さ: {len(api_key)}）")
    print(f"最初の5文字: {api_key[:5]}...")
else:
    print("API Key: 未設定")
    exit(1)

# Google Generative AIで直接テスト
print("\n1. Google Generative AI 直接テスト:")
try:
    import google.generativeai as genai
    
    # API Keyを設定
    print("   API Key設定中...")
    start = time.time()
    genai.configure(api_key=api_key)
    print(f"   設定完了: {time.time() - start:.3f}秒")
    
    # モデルを作成してテスト
    print("\n2. モデル作成テスト:")
    model_start = time.time()
    model = genai.GenerativeModel('gemini-1.5-flash')
    print(f"   モデル作成完了: {time.time() - model_start:.3f}秒")
    
    # 簡単なテストメッセージを送信
    print("\n3. API呼び出しテスト:")
    call_start = time.time()
    try:
        response = model.generate_content("Say 'Hello World' in Japanese", 
                                        generation_config=genai.types.GenerationConfig(
                                            max_output_tokens=50,
                                            temperature=0.1,
                                        ),
                                        request_options={"timeout": 10})
        elapsed = time.time() - call_start
        print(f"   ✅ 成功: {elapsed:.3f}秒")
        print(f"   レスポンス: {response.text[:100]}...")
        
    except Exception as e:
        elapsed = time.time() - call_start
        print(f"   ❌ 失敗: {elapsed:.3f}秒")
        print(f"   エラー: {type(e).__name__}: {str(e)[:200]}")
        
        # エラーの詳細を分析
        error_msg = str(e).lower()
        if "invalid" in error_msg or "api key" in error_msg:
            print("\n   診断: API Keyが無効です")
        elif "quota" in error_msg:
            print("\n   診断: API使用量の上限に達しています")
        elif "timeout" in error_msg or "timed out" in error_msg:
            print("\n   診断: ネットワーク接続の問題です")
        elif "permission" in error_msg:
            print("\n   診断: API Keyの権限が不足しています")
            
except ImportError as e:
    print(f"   ❌ インポートエラー: {e}")
except Exception as e:
    print(f"   ❌ エラー: {type(e).__name__}: {e}")

print("\n=== 結論 ===")
if 'response' in locals() and response:
    print("✅ API Keyは有効で、正常に動作しています")
else:
    print("❌ API Keyまたはネットワーク接続に問題があります")
    print("\n対処方法:")
    print("1. API Keyが正しいか確認してください")
    print("2. Google AI Studioで新しいAPI Keyを生成してみてください")
    print("3. ネットワーク接続を確認してください")
    print("4. プロキシ設定がある場合は確認してください")