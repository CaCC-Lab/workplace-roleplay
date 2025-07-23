#!/usr/bin/env python3
"""
app.pyのカバレッジ向上を確認するための簡単なテストスクリプト
"""

import app
import coverage

def main():
    # カバレッジ測定開始
    cov = coverage.Coverage(source=['app'])
    cov.start()
    
    try:
        # app.pyの様々な関数を実行
        print("=== app.py関数の実行テスト ===")
        
        # 1. format_datetime関数
        result1 = app.format_datetime('2024-01-15T10:30:45')
        print(f"format_datetime: {result1}")
        
        result2 = app.format_datetime(None)
        print(f"format_datetime(None): {result2}")
        
        # 2. get_available_gemini_models関数
        models = app.get_available_gemini_models()
        print(f"Available models: {len(models)} models")
        
        # 3. extract_content関数
        content = app.extract_content("テストコンテンツ")
        print(f"extract_content: {content}")
        
        # 4. initialize_session_history関数（Flaskコンテキスト無しでは実行不可）
        print("initialize_session_history: Flask context required")
        
        # 5. create_gemini_llm関数（環境によっては制限される）
        try:
            llm = app.create_gemini_llm("gemini-1.5-flash")
            print(f"create_gemini_llm: {type(llm)}")
        except Exception as e:
            print(f"create_gemini_llm error (expected): {e}")
        
        print("\n=== 基本関数テスト完了 ===")
        
    finally:
        # カバレッジ測定停止
        cov.stop()
        cov.save()
        
        # レポート生成
        print("\n=== カバレッジレポート ===")
        cov.report(show_missing=True)

if __name__ == "__main__":
    main()