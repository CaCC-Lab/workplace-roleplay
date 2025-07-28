#!/usr/bin/env python3
"""シナリオ読み込みテスト"""
import sys
import time

print("シナリオ読み込みテスト")
print("=" * 50)

# シナリオ読み込みの計測
print("\n1. シナリオデータの読み込み")
start = time.time()
from scenarios import load_scenarios
scenarios_data = load_scenarios()
elapsed = time.time() - start

print(f"   読み込み時間: {elapsed:.3f}秒")
print(f"   シナリオ数: {len(scenarios_data)}")
print(f"   シナリオID: {list(scenarios_data.keys())[:5]}...")  # 最初の5個だけ表示

# アプリケーションコンテキストでのテスト
print("\n2. Flaskアプリケーションコンテキストでのテスト")
from src.app import create_app
app = create_app()

with app.app_context():
    # LLMサービスのテスト
    print("\n3. LLMサービスのテスト")
    from src.services.llm_service import LLMService
    
    start = time.time()
    llm_service = LLMService()
    models = llm_service.get_available_models()
    elapsed = time.time() - start
    
    print(f"   モデル取得時間: {elapsed:.3f}秒")
    print(f"   モデル数: {len(models)}")
    print(f"   モデル: {[m['name'] for m in models]}")
    
    # ルートハンドラのテスト
    print("\n4. list_scenariosルートのテスト")
    with app.test_client() as client:
        start = time.time()
        response = client.get('/scenarios')
        elapsed = time.time() - start
        
        print(f"   応答時間: {elapsed:.3f}秒")
        print(f"   ステータスコード: {response.status_code}")
        
        # レスポンスにシナリオが含まれているか確認
        if response.status_code == 200:
            html = response.data.decode('utf-8')
            if 'scenario-card' in html:
                print("   ✅ シナリオカードが含まれています")
            else:
                print("   ❌ シナリオカードが見つかりません")
                # デバッグ用: HTMLの一部を表示
                if 'scenarios' in html:
                    print("   HTMLに'scenarios'という文字列は含まれています")
                    
print("\n完了！")