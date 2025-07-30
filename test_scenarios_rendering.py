#!/usr/bin/env python3
"""シナリオレンダリングの問題を調査"""
from src.app import create_app
from bs4 import BeautifulSoup

app = create_app()

with app.test_client() as client:
    # /scenariosページを取得
    response = client.get('/scenarios')
    html = response.data.decode('utf-8')
    
    # BeautifulSoupでパース
    soup = BeautifulSoup(html, 'html.parser')
    
    # デバッグ情報を出力
    print("シナリオレンダリングの調査")
    print("=" * 50)
    
    # scenarios-listを全て探す
    all_lists = soup.find_all(class_='scenarios-list')
    print(f"\n1. scenarios-listの数: {len(all_lists)}")
    
    for i, sl in enumerate(all_lists):
        parent = sl.find_parent()
        parent_id = parent.get('id', 'no-id') if parent else 'no-parent'
        print(f"\n   リスト{i+1}:")
        print(f"     親要素のID: {parent_id}")
        print(f"     クラス: {' '.join(sl.get('class', []))}")
        print(f"     子要素数: {len(sl.find_all(recursive=False))}")
        
        # 最初の数個の子要素を表示
        children = sl.find_all(recursive=False)
        if children:
            for j, child in enumerate(children[:3]):
                print(f"     子要素{j+1}: <{child.name} class='{' '.join(child.get('class', []))}'>")
    
    # シナリオカードの位置を確認
    print("\n2. シナリオカードの位置:")
    cards = soup.find_all(class_='scenario-card')
    print(f"   総数: {len(cards)}")
    
    if cards:
        # 最初のカードの親要素を辿る
        first_card = cards[0]
        print(f"\n   最初のカードの親要素チェーン:")
        parent = first_card.parent
        level = 1
        while parent and parent.name != 'body':
            classes = ' '.join(parent.get('class', []))
            print(f"     レベル{level}: <{parent.name} class='{classes}'>")
            if 'scenarios-list' in parent.get('class', []):
                print(f"     ★ scenarios-listコンテナ発見！")
            parent = parent.parent
            level += 1
    
    # Jinja2のループが動作しているか確認
    print("\n3. テンプレートのループ確認:")
    # HTMLソースで{% for scenario_id を探す
    if '{% for scenario_id' in html:
        print("   ❌ Jinja2テンプレートタグが残っている（レンダリングされていない）")
    else:
        print("   ✅ Jinja2テンプレートタグは正しくレンダリングされている")
    
    # scenariosデータが空でないか確認
    print("\n4. コンテキストデータの確認:")
    # エラーメッセージやデバッグ情報を探す
    if 'シナリオが見つかりません' in html:
        print("   ❌ シナリオが見つからないメッセージが表示されている")
    elif len(cards) > 0:
        print(f"   ✅ {len(cards)}個のシナリオカードがレンダリングされている")