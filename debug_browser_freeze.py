#!/usr/bin/env python3
"""ブラウザでのフリーズ問題をデバッグ"""
import time
import requests
from threading import Thread

print("ブラウザフリーズ問題のデバッグ")
print("=" * 50)

# JavaScriptの実行を含むテスト
print("\n1. JavaScriptを含むページの完全なレンダリングテスト")

# HTMLコンテンツの解析
response = requests.get("http://localhost:5001/scenarios")
if response.status_code == 200:
    html = response.text
    
    # JavaScript関連の要素を確認
    js_files = []
    import re
    
    # scriptタグを抽出
    script_tags = re.findall(r'<script[^>]*src="([^"]+)"', html)
    print(f"\n読み込まれているJavaScriptファイル:")
    for script in script_tags:
        print(f"   - {script}")
        js_files.append(script)
    
    # インラインJavaScriptの確認
    inline_scripts = re.findall(r'<script[^>]*>([^<]+)</script>', html, re.DOTALL)
    if inline_scripts:
        print(f"\nインラインJavaScript: {len(inline_scripts)}個")
        for i, script in enumerate(inline_scripts[:3]):  # 最初の3つだけ表示
            print(f"   Script {i+1}: {script[:100]}...")
    
    # シナリオカードの数を確認
    scenario_cards = html.count('scenario-card')
    print(f"\nシナリオカード数: {scenario_cards}")
    
    # DOMContentLoadedイベント関連のコードを確認
    if "DOMContentLoaded" in html:
        print("\n⚠️ DOMContentLoadedイベントリスナーが存在します")
        
        # scenarios_list.jsの内容を確認
        js_response = requests.get("http://localhost:5001/static/js/scenarios_list.js")
        if js_response.status_code == 200:
            js_content = js_response.text
            
            # 問題のある可能性のあるパターンを検索
            problematic_patterns = [
                ("setTimeout", js_content.count("setTimeout")),
                ("setInterval", js_content.count("setInterval")),
                ("while", js_content.count("while")),
                ("fetch", js_content.count("fetch")),
                ("XMLHttpRequest", js_content.count("XMLHttpRequest")),
                ("addEventListener", js_content.count("addEventListener")),
                ("forEach", js_content.count("forEach")),
                ("sort", js_content.count("sort")),
            ]
            
            print("\nJavaScriptコードの潜在的な問題箇所:")
            for pattern, count in problematic_patterns:
                if count > 0:
                    print(f"   - {pattern}: {count}回使用")
            
            # ソート処理の詳細を確認
            if "sortScenarios" in js_content:
                print("\n⚠️ ソート処理が含まれています")
                # ソート関連のコードを抽出
                sort_matches = re.findall(r'sortScenarios[^}]+}', js_content, re.DOTALL)
                if sort_matches:
                    print("   ソート処理の一部:")
                    print(f"   {sort_matches[0][:200]}...")

# パフォーマンスプロファイリング
print("\n\n2. リクエストのタイミング分析")

# 複数回のリクエストでタイミングを測定
timings = []
for i in range(3):
    start = time.time()
    response = requests.get("http://localhost:5001/scenarios")
    elapsed = time.time() - start
    timings.append(elapsed)
    print(f"   リクエスト {i+1}: {elapsed:.3f}秒 (ステータス: {response.status_code})")
    time.sleep(0.5)

avg_time = sum(timings) / len(timings)
print(f"\n平均応答時間: {avg_time:.3f}秒")

# 並行リクエストのテスト
print("\n3. 並行リクエストテスト")

def make_request(i):
    start = time.time()
    try:
        response = requests.get("http://localhost:5001/scenarios", timeout=10)
        elapsed = time.time() - start
        print(f"   スレッド {i}: {elapsed:.3f}秒 (ステータス: {response.status_code})")
    except Exception as e:
        print(f"   スレッド {i}: エラー - {e}")

threads = []
for i in range(3):
    t = Thread(target=make_request, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("\n分析完了！")