#!/usr/bin/env python3
"""シンプルなエンドポイントテスト"""
import sys
sys.path.insert(0, '.')

from app import app, scenarios

# テスト用にアプリケーションコンテキストを使用
with app.test_client() as client:
    # エンドポイントが存在するか確認
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        if "async" in rule.rule:
            print(f"  {rule.rule} -> {rule.methods}")
    
    # シナリオが読み込まれているか確認
    print(f"\nScenarios loaded: {len(scenarios)}")
    print(f"First scenario: {list(scenarios.keys())[0] if scenarios else 'None'}")
    
    # エンドポイントを直接呼び出し
    response = client.post('/api/async/scenario/stream', 
                          json={
                              "message": "",
                              "scenario_id": "scenario1",
                              "is_initial": True
                          })
    
    print(f"\nResponse status: {response.status_code}")
    if response.status_code != 200:
        print(f"Response data: {response.get_json()}")