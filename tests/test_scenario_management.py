"""
シナリオ管理ビジネスロジックの詳細な単体テスト
実際の職場コミュニケーション練習アプリの要件に基づく現実的なテスト
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scenarios import load_scenarios


class TestScenarioManagement:
    """シナリオ管理機能の詳細なテスト"""
    
    @pytest.fixture
    def scenarios(self):
        """テスト用にシナリオを一度だけ読み込む"""
        return load_scenarios()
    
    def test_scenario_difficulty_levels(self, scenarios):
        """難易度レベルが適切に設定されている"""
        valid_difficulties = ['初級', '中級', '上級', 'beginner', 'intermediate', 'advanced']
        difficulty_count = {'初級': 0, '中級': 0, '上級': 0}
        
        for scenario_id, scenario in scenarios.items():
            assert 'difficulty' in scenario, f"{scenario_id}に難易度が設定されていない"
            assert scenario['difficulty'] in valid_difficulties, \
                f"{scenario_id}の難易度'{scenario['difficulty']}'が不正"
            
            # 日本語の難易度をカウント
            if scenario['difficulty'] in difficulty_count:
                difficulty_count[scenario['difficulty']] += 1
        
        # 各難易度のシナリオが存在することを確認
        print(f"難易度分布: {difficulty_count}")
        assert difficulty_count['初級'] > 0, "初級シナリオが存在しない"
    
    def test_scenario_tags_consistency(self, scenarios):
        """タグが一貫性を持って使用されている"""
        all_tags = set()
        tag_usage = {}
        
        for scenario_id, scenario in scenarios.items():
            assert 'tags' in scenario, f"{scenario_id}にタグが設定されていない"
            assert isinstance(scenario['tags'], list), f"{scenario_id}のタグがリストでない"
            
            for tag in scenario['tags']:
                all_tags.add(tag)
                tag_usage[tag] = tag_usage.get(tag, 0) + 1
        
        # タグの使用状況を確認
        print(f"使用されているタグ: {sorted(all_tags)}")
        print(f"タグ使用頻度: {tag_usage}")
        
        # 最低限のタグカテゴリが存在することを確認
        expected_tag_categories = ['コミュニケーション', '報告', '指示']
        for category in expected_tag_categories:
            assert any(category in tag for tag in all_tags), \
                f"'{category}'関連のタグが存在しない"
    
    def test_scenario_learning_points(self, scenarios):
        """学習ポイントが適切に設定されている"""
        for scenario_id, scenario in scenarios.items():
            if 'learning_points' in scenario:
                assert isinstance(scenario['learning_points'], list), \
                    f"{scenario_id}の学習ポイントがリストでない"
                assert len(scenario['learning_points']) > 0, \
                    f"{scenario_id}の学習ポイントが空"
                
                # 各学習ポイントが文字列であることを確認
                for point in scenario['learning_points']:
                    assert isinstance(point, str), \
                        f"{scenario_id}の学習ポイントに非文字列が含まれている"
                    assert len(point) > 5, \
                        f"{scenario_id}の学習ポイント'{point}'が短すぎる"
    
    def test_scenario_character_settings(self, scenarios):
        """キャラクター設定が職場環境として適切"""
        for scenario_id, scenario in scenarios.items():
            if 'character_setting' in scenario:
                char_setting = scenario['character_setting']
                
                # 必須フィールドの確認
                expected_fields = ['personality', 'speaking_style', 'situation']
                for field in expected_fields:
                    assert field in char_setting, \
                        f"{scenario_id}のキャラクター設定に{field}がない"
                
                # 職場のペルソナとして適切か
                personality = char_setting.get('personality', '')
                assert len(personality) > 20, \
                    f"{scenario_id}のpersonalityが詳細でない"
                
                # 話し方が設定されているか
                speaking_style = char_setting.get('speaking_style', '')
                assert len(speaking_style) > 10, \
                    f"{scenario_id}の話し方設定が不十分"
    
    def test_scenario_practical_relevance(self, scenarios):
        """シナリオが実際の職場で起こりうる状況か"""
        workplace_keywords = [
            '上司', '部下', '同僚', '会議', '報告', '相談', '依頼',
            'プロジェクト', '納期', 'ミーティング', '業務', '仕事'
        ]
        
        relevant_scenarios = 0
        
        for scenario_id, scenario in scenarios.items():
            # タイトルと説明文に職場関連キーワードが含まれるか
            title = scenario.get('title', '')
            description = scenario.get('description', '')
            combined_text = title + description
            
            if any(keyword in combined_text for keyword in workplace_keywords):
                relevant_scenarios += 1
        
        # 80%以上のシナリオが職場関連であることを確認
        relevance_ratio = relevant_scenarios / len(scenarios)
        print(f"職場関連シナリオの割合: {relevance_ratio:.1%}")
        assert relevance_ratio >= 0.8, "職場関連シナリオが少なすぎる"
    
    def test_scenario_feedback_points_validity(self, scenarios):
        """フィードバックポイントが学習に役立つ内容か"""
        for scenario_id, scenario in scenarios.items():
            if 'feedback_points' in scenario:
                feedback_points = scenario['feedback_points']
                assert isinstance(feedback_points, list), \
                    f"{scenario_id}のfeedback_pointsがリストでない"
                
                # フィードバックポイントが具体的で測定可能か
                for point in feedback_points:
                    assert isinstance(point, str), \
                        f"{scenario_id}のフィードバックポイントに非文字列が含まれる"
                    
                    # 評価可能な要素が含まれているか確認
                    evaluatable_keywords = [
                        '確認', '質問', '説明', '伝達', '表現',
                        'タイミング', '明確', '適切', '丁寧'
                    ]
                    assert any(keyword in point for keyword in evaluatable_keywords), \
                        f"{scenario_id}のフィードバックポイント'{point}'が評価困難"
    
    def test_scenario_progression_difficulty(self, scenarios):
        """シナリオが難易度順に適切に配置されているか"""
        # scenario1から順番に難易度を確認
        scenario_numbers = []
        for scenario_id in scenarios.keys():
            if scenario_id.startswith('scenario') and scenario_id[8:].isdigit():
                scenario_numbers.append(int(scenario_id[8:]))
        
        scenario_numbers.sort()
        
        # 最初の10個のシナリオで難易度の進行を確認
        if len(scenario_numbers) >= 10:
            first_10 = [f'scenario{n}' for n in scenario_numbers[:10]]
            
            beginner_count = 0
            for scenario_id in first_10[:5]:  # 最初の5つ
                if scenarios[scenario_id].get('difficulty') == '初級':
                    beginner_count += 1
            
            # 最初の5つのうち少なくとも3つは初級であるべき
            assert beginner_count >= 3, \
                "序盤のシナリオに初級が少なすぎる（学習曲線が急すぎる）"