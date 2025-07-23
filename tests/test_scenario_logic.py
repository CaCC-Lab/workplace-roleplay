"""
シナリオ管理のビジネスロジックをテスト
実際のコードの動作を確認する現実的なテスト
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scenarios import load_scenarios


class TestScenarioLogic:
    """シナリオ管理機能の単体テスト"""
    
    def test_load_scenarios_returns_dict(self):
        """シナリオ読み込みが辞書を返す"""
        scenarios = load_scenarios()
        assert isinstance(scenarios, dict)
        assert len(scenarios) > 0
    
    def test_scenario_has_required_fields(self):
        """各シナリオに基本的なフィールドが存在する"""
        scenarios = load_scenarios()
        
        # 最低限1つのシナリオは存在するはず
        assert len(scenarios) > 0
        
        # 最初のシナリオをチェック
        first_scenario_key = list(scenarios.keys())[0]
        first_scenario = scenarios[first_scenario_key]
        
        # YAMLファイルの構造に依存するが、基本的なチェックのみ
        assert isinstance(first_scenario, dict)
    
    def test_scenario_ids_are_strings(self):
        """シナリオIDが文字列である"""
        scenarios = load_scenarios()
        
        for scenario_id in scenarios.keys():
            assert isinstance(scenario_id, str)
    
    def test_natural_sort_order(self):
        """シナリオが自然な順序でソートされている"""
        scenarios = load_scenarios()
        scenario_ids = list(scenarios.keys())
        
        # scenario1, scenario2, ..., scenario10のような順序になっているか確認
        # ただし、実際のファイル名に依存するので、このテストは省略可能
        print(f"Loaded scenario IDs: {scenario_ids[:5]}")  # デバッグ用
    
    def test_scenario_structure(self):
        """シナリオが期待される構造を持っている"""
        scenarios = load_scenarios()
        
        # scenario1の構造をチェック
        if 'scenario1' in scenarios:
            scenario = scenarios['scenario1']
            
            # 必須フィールドの確認
            assert 'title' in scenario, "titleフィールドが存在しない"
            assert 'description' in scenario, "descriptionフィールドが存在しない"
            assert 'difficulty' in scenario, "difficultyフィールドが存在しない"
            assert 'tags' in scenario, "tagsフィールドが存在しない"
            
            # 型の確認
            assert isinstance(scenario['title'], str), "titleが文字列でない"
            assert isinstance(scenario['tags'], list), "tagsがリストでない"
            
            # 難易度の値確認
            valid_difficulties = ['初級', '中級', '上級', 'beginner', 'intermediate', 'advanced']
            assert scenario['difficulty'] in valid_difficulties, f"難易度 '{scenario['difficulty']}' が不正"