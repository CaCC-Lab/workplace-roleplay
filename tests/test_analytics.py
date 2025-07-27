"""
分析機能のテスト
"""
import pytest
from datetime import datetime, timedelta
import json
from unittest.mock import Mock, patch

from analytics import LearningDashboard, SkillProgressAnalyzer, TrendAnalyzer
from database import db, StrengthAnalysisResult, ConversationHistory


class TestLearningDashboard:
    """学習ダッシュボードのテスト"""
    
    @pytest.fixture
    def dashboard(self, mock_redis):
        """ダッシュボードインスタンス"""
        with patch('analytics.dashboard.redis.Redis', return_value=mock_redis):
            return LearningDashboard()
    
    @pytest.fixture
    def mock_redis(self):
        """Redisモック"""
        mock = Mock()
        mock.get.return_value = None
        mock.setex.return_value = True
        return mock
    
    def test_get_user_overview_キャッシュなし(self, dashboard, mock_redis, sample_user):
        """キャッシュがない場合のユーザー概要取得"""
        # テストデータ作成
        result = StrengthAnalysisResult(
            user_id=sample_user.id,
            session_id='test-session',
            session_type='scenario',
            analysis_result={
                'scores': {
                    'empathy': 80,
                    'clarity': 75,
                    'active_listening': 85,
                    'adaptability': 70,
                    'positivity': 90,
                    'professionalism': 78
                }
            }
        )
        db.session.add(result)
        db.session.commit()
        
        # テスト実行
        with patch.object(dashboard, '_get_total_sessions', return_value=10):
            with patch.object(dashboard, '_get_total_practice_time', return_value=300):
                overview = dashboard.get_user_overview(sample_user.id)
        
        # 検証
        assert overview['total_sessions'] == 10
        assert overview['total_practice_time'] == 300
        assert 'skill_summary' in overview
        assert 'recommendation' in overview
        
        # キャッシュが設定されたことを確認
        mock_redis.setex.assert_called_once()
    
    def test_get_user_overview_キャッシュあり(self, dashboard, mock_redis, sample_user):
        """キャッシュがある場合のユーザー概要取得"""
        # キャッシュデータ設定
        cached_data = {
            'total_sessions': 20,
            'total_practice_time': 600,
            'skill_summary': {'test': 'data'}
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        # テスト実行
        overview = dashboard.get_user_overview(sample_user.id)
        
        # 検証
        assert overview == cached_data
        # キャッシュから取得したため、setexは呼ばれない
        mock_redis.setex.assert_not_called()
    
    def test_get_skill_progression(self, dashboard, sample_user):
        """スキル進捗データの取得"""
        # テストデータ作成
        base_date = datetime.utcnow()
        for i in range(5):
            result = StrengthAnalysisResult(
                user_id=sample_user.id,
                session_id=f'session-{i}',
                session_type='scenario',
                analysis_result={
                    'scores': {
                        'empathy': 70 + i * 2,
                        'clarity': 65 + i * 3,
                        'active_listening': 75 + i * 1.5,
                        'adaptability': 60 + i * 2.5,
                        'positivity': 80 + i * 1,
                        'professionalism': 70 + i * 2
                    }
                },
                created_at=base_date - timedelta(days=10-i*2)
            )
            db.session.add(result)
        db.session.commit()
        
        # テスト実行
        progression = dashboard.get_skill_progression(sample_user.id, days=30)
        
        # 検証
        assert progression['total_analyses'] == 5
        assert 'skill_trends' in progression
        assert 'growth_rates' in progression
        
        # 成長率の検証
        growth_rates = progression['growth_rates']
        assert growth_rates['empathy'] > 0  # 正の成長
        assert growth_rates['clarity'] > 0


class TestSkillProgressAnalyzer:
    """スキル進捗分析のテスト"""
    
    @pytest.fixture
    def analyzer(self):
        return SkillProgressAnalyzer()
    
    def test_analyze_skill_progress(self, analyzer, sample_user):
        """特定スキルの進捗分析"""
        # テストデータ作成
        skill_name = 'empathy'
        scores = [70, 72, 75, 73, 78, 80, 82]
        
        for i, score in enumerate(scores):
            result = StrengthAnalysisResult(
                user_id=sample_user.id,
                session_id=f'session-{i}',
                session_type='scenario',
                analysis_result={'scores': {skill_name: score}},
                created_at=datetime.utcnow() - timedelta(days=len(scores)-i)
            )
            db.session.add(result)
        db.session.commit()
        
        # テスト実行
        analysis = analyzer.analyze_skill_progress(sample_user.id, skill_name, days=30)
        
        # 検証
        assert analysis['skill'] == skill_name
        assert 'statistics' in analysis
        assert 'trend' in analysis
        assert 'consistency' in analysis
        assert 'improvement_suggestions' in analysis
        
        # 統計情報の検証
        stats = analysis['statistics']
        assert stats['mean'] > 70
        assert stats['min'] == 70
        assert stats['max'] == 82
    
    def test_compare_skills(self, analyzer, sample_user):
        """全スキルの比較分析"""
        # テストデータ作成
        result = StrengthAnalysisResult(
            user_id=sample_user.id,
            session_id='test-session',
            session_type='scenario',
            analysis_result={
                'scores': {
                    'empathy': 85,
                    'clarity': 70,
                    'active_listening': 90,
                    'adaptability': 65,
                    'positivity': 80,
                    'professionalism': 75
                }
            }
        )
        db.session.add(result)
        db.session.commit()
        
        # テスト実行
        comparison = analyzer.compare_skills(sample_user.id, days=30)
        
        # 検証
        assert 'current_scores' in comparison
        assert 'skill_growth' in comparison
        assert 'balance_analysis' in comparison
        assert 'strongest_skills' in comparison
        assert 'weakest_skills' in comparison
        
        # 最強・最弱スキルの検証
        strongest = comparison['strongest_skills'][0]
        weakest = comparison['weakest_skills'][0]
        assert strongest[0] == 'active_listening'
        assert weakest[0] == 'adaptability'


class TestTrendAnalyzer:
    """トレンド分析のテスト"""
    
    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer()
    
    def test_analyze_overall_trends(self, analyzer, sample_user):
        """全体的なトレンド分析"""
        # テストデータ作成
        for i in range(10):
            # 分析結果
            result = StrengthAnalysisResult(
                user_id=sample_user.id,
                session_id=f'session-{i}',
                session_type='scenario',
                analysis_result={
                    'scores': {
                        'empathy': 70 + i,
                        'clarity': 65 + i * 1.5,
                        'active_listening': 75 + i * 0.5
                    }
                },
                created_at=datetime.utcnow() - timedelta(days=20-i*2)
            )
            db.session.add(result)
            
            # 会話履歴
            conv = ConversationHistory(
                user_id=sample_user.id,
                session_id=f'session-{i}',
                session_type='scenario',
                messages=[],
                created_at=datetime.utcnow() - timedelta(days=20-i*2)
            )
            db.session.add(conv)
        
        db.session.commit()
        
        # テスト実行
        trends = analyzer.analyze_overall_trends(sample_user.id, days=30)
        
        # 検証
        assert 'period' in trends
        assert 'activity_trend' in trends
        assert 'performance_trend' in trends
        assert 'skill_trends' in trends
        assert 'predictions' in trends
        assert 'insights' in trends
        
        # アクティビティトレンドの検証
        activity = trends['activity_trend']
        assert activity['direction'] in ['increasing', 'decreasing', 'stable']
    
    def test_identify_learning_plateaus(self, analyzer, sample_user):
        """学習停滞期の特定"""
        # 停滞したスコアのデータ作成
        plateau_scores = [75, 76, 75, 74, 76]  # 変化が小さい
        
        for i, score in enumerate(plateau_scores):
            result = StrengthAnalysisResult(
                user_id=sample_user.id,
                session_id=f'plateau-{i}',
                session_type='scenario',
                analysis_result={
                    'scores': {
                        'empathy': score,
                        'clarity': 80 + i * 3  # こちらは成長
                    }
                },
                created_at=datetime.utcnow() - timedelta(days=10-i)
            )
            db.session.add(result)
        
        db.session.commit()
        
        # テスト実行
        plateaus = analyzer.identify_learning_plateaus(sample_user.id)
        
        # 検証
        assert 'plateaus_detected' in plateaus
        assert 'affected_skills' in plateaus
        assert 'breakthrough_strategies' in plateaus
        
        # empathyが停滞していることを確認
        if plateaus['plateaus_detected']:
            assert 'empathy' in plateaus['affected_skills']
    
    def test_analyze_momentum(self, analyzer, sample_user):
        """学習モメンタムの分析"""
        # 直近30日のデータ（活発）
        for i in range(15):
            result = StrengthAnalysisResult(
                user_id=sample_user.id,
                session_id=f'recent-{i}',
                session_type='scenario',
                analysis_result={
                    'scores': {
                        'empathy': 80 + i,
                        'clarity': 75 + i
                    }
                },
                created_at=datetime.utcnow() - timedelta(days=15-i)
            )
            db.session.add(result)
            
            conv = ConversationHistory(
                user_id=sample_user.id,
                session_id=f'recent-{i}',
                session_type='scenario',
                messages=[],
                created_at=datetime.utcnow() - timedelta(days=15-i)
            )
            db.session.add(conv)
        
        # 前30日のデータ（低活動）
        for i in range(5):
            result = StrengthAnalysisResult(
                user_id=sample_user.id,
                session_id=f'previous-{i}',
                session_type='scenario',
                analysis_result={
                    'scores': {
                        'empathy': 70,
                        'clarity': 65
                    }
                },
                created_at=datetime.utcnow() - timedelta(days=45-i*3)
            )
            db.session.add(result)
            
            conv = ConversationHistory(
                user_id=sample_user.id,
                session_id=f'previous-{i}',
                session_type='scenario',
                messages=[],
                created_at=datetime.utcnow() - timedelta(days=45-i*3)
            )
            db.session.add(conv)
        
        db.session.commit()
        
        # テスト実行
        momentum = analyzer.analyze_momentum(sample_user.id)
        
        # 検証
        assert 'overall_momentum' in momentum
        assert 'interpretation' in momentum
        assert 'activity_momentum' in momentum
        assert 'performance_momentum' in momentum
        assert 'recommendations' in momentum
        
        # モメンタムが正の値であることを確認
        assert momentum['overall_momentum'] > 0
        assert momentum['activity_momentum']['score'] > 0
        assert momentum['performance_momentum']['score'] > 0