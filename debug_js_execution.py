#!/usr/bin/env python3
"""JavaScriptの実行を詳細にデバッグ"""
import requests
from bs4 import BeautifulSoup
import re

print("JavaScriptデバッグ")
print("=" * 50)

# ページを取得
response = requests.get("http://localhost:5001/scenarios")
soup = BeautifulSoup(response.text, 'html.parser')

# シナリオカードを確認
cards = soup.find_all(class_='scenario-card')
print(f"\n1. HTMLのシナリオカード数: {len(cards)}")

# 初期状態のスタイルを確認
hidden_count = 0
for i, card in enumerate(cards[:5]):  # 最初の5つ
    style = card.get('style', '')
    print(f"   カード{i+1}: style='{style}'")
    if 'display: none' in style:
        hidden_count += 1

print(f"\n   初期状態で非表示のカード: {hidden_count}/{len(cards)}")

# scenarios_list.jsの内容を確認
print("\n2. scenarios_list.jsの問題箇所を確認")
js_response = requests.get("http://localhost:5001/static/js/scenarios_list.js")
js_content = js_response.text

# 問題のある可能性のある行を特定
lines = js_content.split('\n')
for i, line in enumerate(lines):
    # scenarioCardsの定義を探す
    if 'const scenarioCards' in line and 'querySelectorAll' in line:
        print(f"\n   行{i+1}: {line.strip()}")
        # 前後の行も表示
        if i > 0:
            print(f"   行{i}: {lines[i-1].strip()}")
        if i < len(lines) - 1:
            print(f"   行{i+2}: {lines[i+1].strip()}")

# filterScenariosの呼び出しを探す
print("\n3. filterScenarios関数の呼び出し箇所")
for i, line in enumerate(lines):
    if 'filterScenarios()' in line and 'function' not in line:
        print(f"   行{i+1}: {line.strip()}")

# 初期化の順序を確認
print("\n4. 初期化の順序")
init_calls = []
for i, line in enumerate(lines):
    if 'initialize' in line and '(' in line and ')' in line:
        init_calls.append((i+1, line.strip()))

for line_num, line in init_calls[:10]:  # 最初の10個
    print(f"   行{line_num}: {line}")

print("\n分析完了！")