#!/usr/bin/env python3
"""
genai.list_models()のブロッキング問題を修正
"""

# 修正内容を表示
print("=== genai.list_models()ブロッキング問題の修正 ===\n")

print("問題の原因:")
print("- get_available_gemini_models()関数内でgenai.list_models()を呼び出し")
print("- このAPIコールがネットワーク遅延やタイムアウトで分単位の遅延を引き起こす")
print("- シナリオ一覧ページ（/scenarios）の表示時に毎回実行される")

print("\n修正方法:")
print("1. genai.list_models()の呼び出しを削除")
print("2. 固定のモデルリストを使用")
print("3. または、キャッシュとタイムアウトを実装")

print("\n修正コード:")
print("-" * 60)

fixed_code = '''
def get_available_gemini_models():
    """
    利用可能なGeminiモデルのリストを返す（固定リスト版）
    """
    # API呼び出しを避けて固定リストを返す
    # これにより分単位の遅延を回避
    return [
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-pro-latest",
        "gemini/gemini-1.5-flash-latest",
        "gemini/gemini-1.0-pro"
    ]
'''

print(fixed_code)
print("-" * 60)

print("\nまたは、キャッシュとタイムアウト版:")
print("-" * 60)

cached_code = '''
import threading
import time

# キャッシュ
_model_cache = None
_cache_time = 0
_cache_duration = 3600  # 1時間

def get_available_gemini_models():
    """
    利用可能なGeminiモデルのリストを返す（キャッシュ版）
    """
    global _model_cache, _cache_time
    
    # キャッシュが有効な場合は返す
    if _model_cache and (time.time() - _cache_time) < _cache_duration:
        return _model_cache
    
    # デフォルトモデル
    default_models = [
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash"
    ]
    
    try:
        # タイムアウト付きでモデルリストを取得
        models = []
        error = None
        
        def fetch_models():
            nonlocal models, error
            try:
                models = list(genai.list_models())
            except Exception as e:
                error = e
        
        # タイムアウト1秒で実行
        thread = threading.Thread(target=fetch_models)
        thread.daemon = True
        thread.start()
        thread.join(timeout=1.0)
        
        if thread.is_alive():
            # タイムアウト
            return default_models
            
        if error:
            return default_models
            
        # 成功した場合はキャッシュ
        gemini_models = []
        for model in models:
            if "gemini" in model.name.lower():
                gemini_models.append(f"gemini/{model.name.split('/')[-1]}")
        
        _model_cache = gemini_models or default_models
        _cache_time = time.time()
        return _model_cache
        
    except:
        return default_models
'''

print(cached_code)
print("-" * 60)

print("\n推奨事項:")
print("1. すぐに修正したい場合は固定リスト版を使用")
print("2. 動的にモデルリストを取得したい場合はキャッシュ版を使用")
print("3. いずれにせよ、ページ表示時の同期的なAPI呼び出しは避ける")