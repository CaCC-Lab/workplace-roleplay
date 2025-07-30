#!/usr/bin/env python3
"""テンプレートレンダリングのテスト"""
from src.app import create_app
from scenarios import load_scenarios

app = create_app()

with app.app_context():
    # シナリオデータを読み込む
    scenarios_data = load_scenarios()
    print(f"シナリオ数: {len(scenarios_data)}")
    print(f"シナリオキー（最初の5個）: {list(scenarios_data.keys())[:5]}")
    
    # テンプレートをレンダリング
    from flask import render_template
    
    # モデル情報も取得
    from src.services.llm_service import LLMService
    llm_service = LLMService()
    models = llm_service.get_available_models()
    print(f"\nモデル数: {len(models)}")
    
    # テンプレートに渡されるデータを確認
    print("\nテンプレートに渡すデータ:")
    print(f"  scenarios: {type(scenarios_data)} (要素数: {len(scenarios_data)})")
    print(f"  models: {type(models)} (要素数: {len(models)})")
    
    # テンプレートをレンダリング
    html = render_template("scenarios_list.html", scenarios=scenarios_data, models=models)
    
    # レンダリング結果を確認
    print(f"\nレンダリング結果のサイズ: {len(html)}文字")
    
    # scenarios-listの内容を確認
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # メインのscenarios-listを探す（推薦用ではない方）
    all_scenario_lists = soup.find_all(class_='scenarios-list')
    print(f"\nscenarios-listコンテナ数: {len(all_scenario_lists)}")
    
    for i, sl in enumerate(all_scenario_lists):
        parent_section = sl.find_parent(class_='content-section')
        if parent_section and parent_section.get('id') != 'recommended-scenarios-section':
            # これがメインのシナリオリスト
            cards = sl.find_all(class_='scenario-card')
            print(f"\nメインのscenarios-list:")
            print(f"  子要素数: {len(sl.find_all(recursive=False))}")
            print(f"  scenario-card数: {len(cards)}")
            break
    
    # 全体のscenario-card数
    all_cards = soup.find_all(class_='scenario-card')
    print(f"\n全scenario-card数: {len(all_cards)}")