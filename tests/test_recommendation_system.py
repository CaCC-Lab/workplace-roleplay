"""
推薦システムのテスト

パーソナライズ学習パス機能の単体テスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.recommendation import (
    PersonalizedRecommendationEngine,
    RecommendationItem,
    get_recommendations_for_user,
    get_recommendation_explanation
)


class TestPersonalizedRecommendationEngine:
    """PersonalizedRecommendationEngineのテスト"""
    
    @pytest.fixture
    def engine(self):
        """推薦エンジンのインスタンス"""
        return PersonalizedRecommendationEngine()
    
    @pytest.fixture
    def mock_user_analysis(self):
        """モックユーザー分析結果"""
        return {
            'skill_scores': {
                'empathy': 2.5,
                'clarity': 4.0,
                'active_listening': 3.0,
                'adaptability': 2.0,
                'positivity': 3.5,
                'professionalism': 4.5
            },
            'overall_score': 3.3
        }
    
    @pytest.fixture
    def mock_scenarios(self):
        """モックシナリオデータ"""
        return {
            'scenario1': {
                'title': 'テストシナリオ1',
                'description': '説明1',
                'metadata': {
                    'target_strengths': ['empathy', 'clarity'],
                    'difficulty': 2
                }
            },
            'scenario2': {
                'title': 'テストシナリオ2',
                'description': '説明2',
                'metadata': {
                    'target_strengths': ['adaptability'],
                    'difficulty': 3
                }
            },
            'scenario3': {
                'title': 'テストシナリオ3',
                'description': '説明3',
                'metadata': {
                    'target_strengths': ['professionalism'],
                    'difficulty': 4
                }
            }
        }
    
    def test_identify_weak_skills(self, engine, mock_user_analysis):
        """弱点スキルの特定テスト"""
        weak_skills = engine._identify_weak_skills(mock_user_analysis)
        
        # 3.5未満のスキルが弱点として特定される
        assert len(weak_skills) == 3
        assert ('adaptability', 2.0) in weak_skills
        assert ('empathy', 2.5) in weak_skills
        assert ('active_listening', 3.0) in weak_skills
        
        # スコア順でソートされている
        assert weak_skills[0][0] == 'adaptability'
        assert weak_skills[1][0] == 'empathy'
        assert weak_skills[2][0] == 'active_listening'
    
    def test_calculate_recommendation_score(self, engine, mock_scenarios, mock_user_analysis):
        """推薦スコア計算のテスト"""
        weak_skills = [('adaptability', 2.0), ('empathy', 2.5)]
        
        # adaptabilityを対象とするシナリオが最高スコア
        score1 = engine._calculate_recommendation_score(
            mock_scenarios['scenario1'], weak_skills, mock_user_analysis
        )
        score2 = engine._calculate_recommendation_score(
            mock_scenarios['scenario2'], weak_skills, mock_user_analysis
        )
        score3 = engine._calculate_recommendation_score(
            mock_scenarios['scenario3'], weak_skills, mock_user_analysis
        )
        
        assert score2 > score1  # adaptabilityシナリオが高スコア
        assert score1 > score3  # empathyシナリオが次
        assert score3 == 0.0    # professionalism（弱点でない）は0
    
    @patch('services.recommendation.get_latest_analysis_result')
    @patch('services.recommendation.load_scenarios')
    def test_get_user_recommendations_with_analysis(self, mock_load_scenarios, 
                                                  mock_get_analysis, engine, 
                                                  mock_user_analysis, mock_scenarios):
        """分析結果がある場合の推薦取得テスト"""
        mock_get_analysis.return_value = {'strengths_analysis': mock_user_analysis}
        mock_load_scenarios.return_value = mock_scenarios
        engine.scenarios = mock_scenarios
        
        recommendations = engine.get_user_recommendations(1, limit=2)
        
        assert len(recommendations) == 2
        assert isinstance(recommendations[0], RecommendationItem)
        assert recommendations[0].scenario_id in ['scenario1', 'scenario2']
        assert recommendations[0].recommendation_score > 0
    
    @patch('services.recommendation.get_latest_analysis_result')
    @patch('services.recommendation.load_scenarios')
    def test_get_user_recommendations_no_analysis(self, mock_load_scenarios, 
                                                 mock_get_analysis, engine, mock_scenarios):
        """分析結果がない場合の推薦取得テスト（初心者向け）"""
        mock_get_analysis.return_value = None
        mock_load_scenarios.return_value = mock_scenarios
        engine.scenarios = mock_scenarios
        
        recommendations = engine.get_user_recommendations(1, limit=3)
        
        assert len(recommendations) > 0
        # 初心者向け（難易度2以下）が推薦される
        for rec in recommendations:
            assert rec.difficulty <= 2
            assert '初心者' in rec.reason
    
    def test_translate_skill_names(self, engine):
        """スキル名の日本語翻訳テスト"""
        skills = ['empathy', 'clarity', 'unknown']
        translated = engine._translate_skill_names(skills)
        
        assert translated[0] == '共感力'
        assert translated[1] == '明確性'
        assert translated[2] == 'unknown'  # 未知のスキルはそのまま
    
    @patch('services.recommendation.get_latest_analysis_result')
    def test_get_explanation_with_analysis(self, mock_get_analysis, engine, mock_user_analysis):
        """推薦根拠の説明取得テスト（分析あり）"""
        mock_get_analysis.return_value = {'strengths_analysis': mock_user_analysis}
        
        explanation = engine.get_explanation(1)
        
        assert explanation['status'] == 'success'
        assert 'weak_skills' in explanation
        assert 'skill_scores' in explanation
        assert 'average_skill' in explanation
        assert explanation['average_skill'] == pytest.approx(3.25, 0.01)
    
    @patch('services.recommendation.get_latest_analysis_result')
    def test_get_explanation_no_analysis(self, mock_get_analysis, engine):
        """推薦根拠の説明取得テスト（分析なし）"""
        mock_get_analysis.return_value = None
        
        explanation = engine.get_explanation(1)
        
        assert explanation['status'] == 'no_analysis'
        assert 'message' in explanation


class TestRecommendationHelperFunctions:
    """ヘルパー関数のテスト"""
    
    @patch('services.recommendation.recommendation_engine.get_user_recommendations')
    def test_get_recommendations_for_user(self, mock_get_recommendations):
        """外部API用推薦取得関数のテスト"""
        mock_item = RecommendationItem(
            scenario_id='test1',
            title='テスト',
            description='説明',
            target_strengths=['empathy'],
            difficulty=3,
            recommendation_score=2.5,
            reason='テスト理由'
        )
        mock_get_recommendations.return_value = [mock_item]
        
        result = get_recommendations_for_user(1, limit=1)
        
        assert len(result) == 1
        assert result[0]['scenario_id'] == 'test1'
        assert result[0]['recommendation_score'] == 2.5
        assert 'reason' in result[0]
    
    @patch('services.recommendation.recommendation_engine.get_explanation')
    def test_get_recommendation_explanation(self, mock_get_explanation):
        """外部API用説明取得関数のテスト"""
        mock_explanation = {
            'status': 'success',
            'weak_skills': [('empathy', 2.5)],
            'average_skill': 3.0
        }
        mock_get_explanation.return_value = mock_explanation
        
        result = get_recommendation_explanation(1)
        
        assert result == mock_explanation
        mock_get_explanation.assert_called_once_with(1)