#!/usr/bin/env python3
"""async APIエンドポイントのテスト"""
import requests
import json

# エンドポイントをテスト
url = "http://localhost:5001/api/async/scenario/stream"
data = {
    "message": "",
    "scenario_id": "scenario1",
    "is_initial": True
}

headers = {
    "Content-Type": "application/json"
}

print("Testing /api/async/scenario/stream endpoint...")
print(f"URL: {url}")
print(f"Data: {json.dumps(data, indent=2)}")

try:
    response = requests.post(url, json=data, headers=headers)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code != 200:
        print(f"\nError Response:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
        except:
            print(response.text)
    else:
        print(f"\nSuccess Response:")
        print(response.text[:500])  # 最初の500文字を表示
        
except Exception as e:
    print(f"\nRequest failed: {str(e)}")