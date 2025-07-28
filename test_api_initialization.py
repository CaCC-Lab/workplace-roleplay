#!/usr/bin/env python3
"""
API初期化の遅延をテスト
"""
import time
import os
import sys

print("=== API初期化テスト ===\n")

# 環境変数の確認
print("1. API Key設定:")
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    print(f"   GOOGLE_API_KEY: 設定済み（長さ: {len(api_key)}）")
else:
    print("   GOOGLE_API_KEY: 未設定")
    print("   ⚠️ API Keyが設定されていません！")

# Google Generative AI の初期化テスト
print("\n2. Google Generative AI初期化テスト:")
start = time.time()
try:
    import google.generativeai as genai
    print(f"   インポート完了: {time.time() - start:.3f}秒")
    
    # APIキーの設定
    if api_key:
        print("   API Key設定中...")
        config_start = time.time()
        genai.configure(api_key=api_key)
        print(f"   設定完了: {time.time() - config_start:.3f}秒")
        
        # モデル一覧の取得（これがブロックする可能性）
        print("\n3. モデル一覧取得テスト:")
        list_start = time.time()
        try:
            # タイムアウトを設定
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("モデル一覧取得がタイムアウトしました")
            
            # 30秒のタイムアウトを設定
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            
            models = genai.list_models()
            signal.alarm(0)  # タイムアウトをクリア
            
            elapsed = time.time() - list_start
            print(f"   成功: {elapsed:.3f}秒")
            print(f"   利用可能なモデル数: {sum(1 for _ in models)}")
            
        except TimeoutError as e:
            print(f"   ✗ タイムアウト: 30秒経過")
            print("   ⚠️ ネットワーク接続に問題がある可能性があります")
        except Exception as e:
            elapsed = time.time() - list_start
            print(f"   ✗ エラー: {elapsed:.3f}秒後")
            print(f"   {type(e).__name__}: {e}")
            
except ImportError as e:
    print(f"   ✗ インポートエラー: {e}")
except Exception as e:
    print(f"   ✗ エラー: {e}")

# LangChain初期化テスト
print("\n4. LangChain Gemini初期化テスト:")
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    if api_key:
        print("   ChatGoogleGenerativeAIインスタンス作成中...")
        init_start = time.time()
        
        # これがブロックする可能性
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7,
            timeout=10  # 10秒のタイムアウト
        )
        
        elapsed = time.time() - init_start
        print(f"   成功: {elapsed:.3f}秒")
        
        # 実際に呼び出してみる
        print("\n5. 実際のAPI呼び出しテスト:")
        call_start = time.time()
        try:
            response = llm.invoke("Hello, this is a test.")
            elapsed = time.time() - call_start
            print(f"   成功: {elapsed:.3f}秒")
            print(f"   レスポンス長: {len(response.content)}")
        except Exception as e:
            elapsed = time.time() - call_start
            print(f"   ✗ エラー: {elapsed:.3f}秒後")
            print(f"   {type(e).__name__}: {e}")
            
except Exception as e:
    print(f"   ✗ エラー: {e}")

print("\n=== 診断結果 ===")
if not api_key:
    print("⚠️ GOOGLE_API_KEYが設定されていないため、API初期化ができません。")
    print("これが分単位の遅延の原因の可能性があります。")
else:
    print("API Key は設定されていますが、ネットワーク接続に問題がある可能性があります。")