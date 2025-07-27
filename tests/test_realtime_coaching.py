"""
リアルタイムコーチング機能のテスト

WebSocketとコーチングエンジンの単体テスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import asyncio

from services.realtime_coach import RealTimeCoach
from services.websocket_service import WebSocketCoachingService
from services.ab_testing import ExperimentationFramework, ExperimentConfig


async def generate_typing_hints(message: str, analysis: dict, level: str) -> list:
    """タイピングヒント生成のヘルパー関数"""
    hints = []
    suggestions = analysis.get('suggestions', [])
    
    max_hints = 1 if level == 'basic' else 3
    for i, suggestion in enumerate(suggestions[:max_hints]):
        hints.append({
            'hint': suggestion.get('suggestion', ''),
            'skill': suggestion.get('skill', ''),
            'confidence': suggestion.get('confidence', 0.8)
        })
    
    return hints


class TestRealtimeCoachingEngine:
    """RealTimeCoachのテスト"""
    
    @pytest.fixture
    def coaching_engine(self):
        """コーチングエンジンのインスタンス"""
        return RealTimeCoach()
    
    @pytest.mark.asyncio
    async def test_analyze_message_realtime_basic(self, coaching_engine):
        """基本的なメッセージ分析のテスト"""
        message = "すみません、遅れて申し訳ございません"
        context = {
            'page_type': 'scenario',
            'scenario_id': 'business_meeting'
        }
        
        result = await coaching_engine.analyze_message_realtime(message, context)
        
        assert 'message' in result
        assert 'timestamp' in result
        assert 'suggestions' in result
        assert 'scores' in result
        assert 'overall_rating' in result
        assert result['overall_rating'] in ['needs_improvement', 'good', 'excellent']
    
    @pytest.mark.asyncio
    async def test_analyze_message_with_patterns(self, coaching_engine):
        """パターンマッチングのテスト"""
        # 弱いパターン（曖昧な表現）
        message = "えーと、なんか、そんな感じです"
        context = {'page_type': 'chat'}
        
        result = await coaching_engine.analyze_message_realtime(message, context)
        
        # 明確性の問題が検出される
        assert result['scores']['clarity'] < 70
        assert len(result['suggestions']) > 0
    
    def test_get_scenario_specific_hints(self, coaching_engine):
        """シナリオ固有ヒント生成のテスト"""
        hints = coaching_engine.get_scenario_specific_hints('business_apology', {})
        
        assert isinstance(hints, list)
        # ヒントがあれば検証
        if hints:
            assert all('message' in h and 'suggestion' in h for h in hints)
    
    def test_pattern_matching(self, coaching_engine):
        """パターンマッチング機能のテスト"""
        # 過度な謝罪（共感スキルの弱いパターン）
        message1 = "わかりました。"
        score1, suggestions1 = coaching_engine._analyze_skill(
            message1, 'empathy', coaching_engine.coaching_rules['empathy'], {}
        )
        
        # 弱いパターンなのでスコアが低い
        assert score1 < 70
        assert len(suggestions1) > 0
        
        # 良いパターン
        message2 = "大変お疲れさまでした。お気持ちお察しします。"
        score2, suggestions2 = coaching_engine._analyze_skill(
            message2, 'empathy', coaching_engine.coaching_rules['empathy'], {}
        )
        
        # 良いパターンなのでスコアが高い
        assert score2 > 70


class TestWebSocketCoachingService:
    """WebSocketCoachingServiceのテスト"""
    
    @pytest.fixture
    def mock_socketio(self):
        """モックSocket.IOサーバー"""
        mock = MagicMock()
        mock.emit = MagicMock()
        mock.on = MagicMock()
        return mock
    
    @pytest.fixture
    def websocket_service(self, mock_socketio):
        """WebSocketサービスのインスタンス"""
        with patch('services.websocket_service.current_user', MagicMock(is_authenticated=True, id=1)):
            service = WebSocketCoachingService(mock_socketio)
            service.coaching_engine = Mock(spec=RealTimeCoach)
            service.experiment_framework = Mock(spec=ExperimentationFramework)
            return service
    
    def test_session_stats(self, websocket_service):
        """セッション統計情報のテスト"""
        # セッションデータを追加
        session_id = 'test-session-123'
        websocket_service.active_sessions[session_id] = {
            'user_id': 1,
            'variant': {'coaching_enabled': True, 'hint_level': 'basic'},
            'start_time': datetime.utcnow(),
            'message_count': 5,
            'hints_shown': 3,
            'hints_accepted': 2
        }
        
        # 統計情報を取得
        stats = websocket_service.get_session_stats(session_id)
        
        assert stats is not None
        assert stats['user_id'] == 1
        assert stats['message_count'] == 5
        assert stats['hints_shown'] == 3
        assert stats['hints_accepted'] == 2
        assert stats['acceptance_rate'] == 2/3
    
    def test_calculate_hint_confidence(self, websocket_service):
        """ヒント信頼度計算のテスト"""
        # 短いメッセージ
        confidence1 = websocket_service._calculate_hint_confidence("こんにちは")
        assert 0 <= confidence1 <= 1.0
        
        # 完成したメッセージ
        confidence2 = websocket_service._calculate_hint_confidence("会議の件でご相談があります。")
        assert confidence2 > confidence1  # より長く完成したメッセージは信頼度が高い
        
        # 長いメッセージ
        long_message = "本日の会議についてですが、予定通り14時から開始でよろしいでしょうか。"
        confidence3 = websocket_service._calculate_hint_confidence(long_message)
        assert confidence3 >= 0.7  # 十分長いメッセージは高い信頼度
    
    def test_get_all_session_stats(self, websocket_service):
        """全セッション統計のテスト"""
        # 複数のセッションを追加
        for i in range(3):
            websocket_service.active_sessions[f'session_{i}'] = {
                'user_id': i,
                'variant': {'name': 'treatment' if i % 2 == 0 else 'control', 'coaching_enabled': True},
                'start_time': datetime.utcnow(),
                'message_count': i * 2,
                'hints_shown': i,
                'hints_accepted': i // 2
            }
        
        stats = websocket_service.get_all_session_stats()
        
        assert stats['active_sessions'] == 3
        assert stats['total_messages'] == 6  # 0 + 2 + 4
        assert stats['total_hints_shown'] == 3  # 0 + 1 + 2
        assert stats['variant_distribution']['treatment'] == 2
        assert stats['variant_distribution']['control'] == 1


class TestGenerateTypingHints:
    """generate_typing_hints関数のテスト"""
    
    @pytest.mark.asyncio
    async def test_generate_basic_hints(self):
        """基本レベルのヒント生成テスト"""
        message = "すみません"
        analysis = {
            'suggestions': [
                {'suggestion': 'より具体的に', 'skill': 'clarity'}
            ]
        }
        
        hints = await generate_typing_hints(message, analysis, 'basic')
        
        assert len(hints) <= 1  # basicは最大1つ
        if hints:
            assert 'hint' in hints[0]
            assert 'confidence' in hints[0]
    
    @pytest.mark.asyncio
    async def test_generate_advanced_hints(self):
        """上級レベルのヒント生成テスト"""
        message = "たぶん、できるかもしれません"
        analysis = {
            'suggestions': [
                {'suggestion': '断定的に', 'skill': 'confidence'},
                {'suggestion': '具体的に', 'skill': 'clarity'}
            ]
        }
        
        hints = await generate_typing_hints(message, analysis, 'advanced')
        
        assert len(hints) <= 3  # advancedは最大3つ
        for hint in hints:
            assert 'hint' in hint
            assert 'skill' in hint
            assert 'confidence' in hint


class TestABTestingFramework:
    """A/Bテストフレームワークのテスト"""
    
    @pytest.fixture
    def ab_framework(self):
        """A/Bテストフレームワークのインスタンス"""
        return ExperimentationFramework()
    
    def test_assign_user_to_experiment(self, ab_framework):
        """ユーザーの実験グループ割り当てテスト"""
        # 実験設定を追加
        config = ExperimentConfig(
            name='realtime_coaching',
            control_percentage=50,
            enabled=True,
            start_date=datetime.utcnow()
        )
        ab_framework.experiments['realtime_coaching'] = config
        
        # 複数ユーザーを割り当て
        assignments = []
        for i in range(100):
            group = ab_framework.assign_user_to_experiment(i, 'realtime_coaching')
            assignments.append(group)
        
        # controlとtreatmentの両方が存在
        assert 'control' in assignments
        assert 'treatment' in assignments
        
        # 大体半々に分かれる（±20%の許容）
        control_count = assignments.count('control')
        assert 30 <= control_count <= 70
    
    def test_track_metric(self, ab_framework):
        """メトリクス追跡のテスト"""
        # redisをモックして、current_appへのアクセスを回避
        ab_framework.redis_client = None
        
        # ユーザーバリアントを返すようにモック
        ab_framework.get_user_variant = MagicMock(return_value={'name': 'treatment'})
        
        # メトリクスを追跡
        ab_framework.track_metric(1, 'hint_helpful', 1.0, 'realtime_coaching')
        ab_framework.track_metric(2, 'session_rating', 4.0, 'realtime_coaching')
        
        # メトリクスが記録される（内部バッファに）
        assert len(ab_framework.metrics_buffer) > 0
        assert len(ab_framework.metrics) == 2
    
    def test_get_experiment_results(self, ab_framework):
        """実験結果取得のテスト"""
        # テストデータを追加
        for i in range(10):
            group = 'treatment' if i % 2 == 0 else 'control'
            ab_framework.user_assignments[i] = {'realtime_coaching': group}
            ab_framework.track_metric(
                i, 'session_rating', 
                4.5 if group == 'treatment' else 3.5,
                'realtime_coaching'
            )
        
        results = ab_framework.get_experiment_results('realtime_coaching')
        
        assert 'variants' in results
        assert 'statistical_significance' in results
        assert 'recommendations' in results