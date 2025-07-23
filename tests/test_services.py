"""
services.py のユニットテスト
ユーザー成長記録システム（StrengthAnalysisService, AchievementService）のテスト
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from models import db, User, Scenario, PracticeSession, ConversationLog, StrengthAnalysis, Achievement, UserAchievement, SessionType
from services import (
    StrengthAnalysisService, 
    AchievementService,
    ScenarioService,
    SessionService,
    ConversationService,
    UserService
)
from errors import NotFoundError, AppError, ValidationError


class TestStrengthAnalysisService:
    """強み分析サービスのテスト"""
    
    @pytest.fixture
    def sample_analysis_result(self):
        """サンプル分析結果"""
        return {
            'empathy': 0.85,
            'clarity': 0.72,
            'listening': 0.90,
            'problem_solving': 0.68,
            'assertiveness': 0.75,
            'flexibility': 0.80
        }
    
    @pytest.fixture
    def mock_session(self, app):
        """モックセッション"""
        with app.app_context():
            session = PracticeSession(
                id=1,
                user_id=1,
                session_type=SessionType.SCENARIO,
                scenario_id=1
            )
            return session
    
    def test_save_analysis_new(self, app, mock_session, sample_analysis_result):
        """新規強み分析の保存テスト"""
        with app.app_context():
            with patch.object(SessionService, 'get_session_by_id', return_value=mock_session):
                with patch.object(db.session, 'add'):
                    with patch.object(db.session, 'commit'):
                        with patch.object(StrengthAnalysis, 'query') as mock_query:
                            mock_query.filter_by.return_value.first.return_value = None
                            
                            analysis = StrengthAnalysisService.save_analysis(
                                session_id=1,
                                analysis_result=sample_analysis_result,
                                feedback_text="よくできました"
                            )
                            
                            # スコアの確認
                            assert analysis.empathy == 0.85
                            assert analysis.clarity == 0.72
                            assert analysis.listening == 0.90
                            assert analysis.problem_solving == 0.68
                            assert analysis.assertiveness == 0.75
                            assert analysis.flexibility == 0.80
                            
                            # 総合スコアの計算確認
                            expected_overall = sum(sample_analysis_result.values()) / 6
                            assert abs(analysis.overall_score - expected_overall) < 0.01
                            
                            # フィードバックの確認
                            assert analysis.feedback_text == "よくできました"
                            
                            # 改善提案の確認
                            assert 'strengths' in analysis.improvement_suggestions
                            assert 'areas_for_improvement' in analysis.improvement_suggestions
                            assert 'next_steps' in analysis.improvement_suggestions
    
    def test_save_analysis_update_existing(self, app, mock_session, sample_analysis_result):
        """既存分析の更新テスト"""
        with app.app_context():
            existing_analysis = StrengthAnalysis(session_id=1)
            
            with patch.object(SessionService, 'get_session_by_id', return_value=mock_session):
                with patch.object(db.session, 'add'):
                    with patch.object(db.session, 'commit'):
                        with patch.object(StrengthAnalysis, 'query') as mock_query:
                            mock_query.filter_by.return_value.first.return_value = existing_analysis
                            
                            analysis = StrengthAnalysisService.save_analysis(
                                session_id=1,
                                analysis_result=sample_analysis_result
                            )
                            
                            # 既存のオブジェクトが更新されることを確認
                            assert analysis is existing_analysis
                            assert analysis.empathy == 0.85
    
    def test_save_analysis_validation_error(self, app, mock_session):
        """不正なスコアでのバリデーションエラーテスト"""
        invalid_result = {
            'empathy': 1.5,  # 1.0を超える不正な値
            'clarity': 0.72,
            'listening': 0.90,
            'problem_solving': 0.68,
            'assertiveness': 0.75,
            'flexibility': 0.80
        }
        
        with app.app_context():
            with patch.object(SessionService, 'get_session_by_id', return_value=mock_session):
                with pytest.raises(ValidationError):
                    StrengthAnalysisService.save_analysis(
                        session_id=1,
                        analysis_result=invalid_result
                    )
    
    def test_identify_strengths(self):
        """強みの特定テスト"""
        scores = {
            'empathy': 0.85,
            'clarity': 0.60,
            'listening': 0.90,
            'problem_solving': 0.45,
            'assertiveness': 0.82,
            'flexibility': 0.70
        }
        
        strengths = StrengthAnalysisService._identify_strengths(scores)
        
        # 0.8以上のスキルが強みとして特定される
        assert '共感力' in strengths
        assert '傾聴力' in strengths
        assert '自己主張' in strengths
        assert '明確な伝達' not in strengths
    
    def test_identify_improvements(self):
        """改善点の特定テスト"""
        scores = {
            'empathy': 0.85,
            'clarity': 0.55,
            'listening': 0.90,
            'problem_solving': 0.45,
            'assertiveness': 0.75,
            'flexibility': 0.30
        }
        
        improvements = StrengthAnalysisService._identify_improvements(scores)
        
        # 0.6未満のスキルが改善点として特定される
        assert '明確な伝達' in improvements
        assert '問題解決力' in improvements
        assert '柔軟性' in improvements
        assert '共感力' not in improvements
    
    def test_get_skill_progress(self, app):
        """スキル進捗の取得テスト"""
        with app.app_context():
            analyses = [
                MagicMock(
                    empathy=0.70, clarity=0.65, listening=0.75,
                    problem_solving=0.60, assertiveness=0.70, flexibility=0.65,
                    created_at=datetime.now() - timedelta(days=i),
                    session_id=i
                ) for i in range(5)
            ]
            
            with patch.object(StrengthAnalysisService, 'get_user_analyses', return_value=analyses):
                progress = StrengthAnalysisService.get_skill_progress(user_id=1)
                
                # 各スキルの進捗データが存在することを確認
                assert 'empathy' in progress
                assert 'clarity' in progress
                assert len(progress['empathy']) == 5
                
                # データが古い順に並んでいることを確認
                for skill_data in progress['empathy']:
                    assert 'date' in skill_data
                    assert 'score' in skill_data
                    assert 'session_id' in skill_data

    def test_get_average_scores_success(self, app):
        """平均スコア取得成功テスト"""
        with app.app_context():
            # subqueryのモックを作成
            mock_subquery = MagicMock()
            mock_subquery.c = MagicMock()
            mock_subquery.c.empathy = MagicMock()
            mock_subquery.c.clarity = MagicMock()
            mock_subquery.c.listening = MagicMock()
            mock_subquery.c.problem_solving = MagicMock()
            mock_subquery.c.assertiveness = MagicMock()
            mock_subquery.c.flexibility = MagicMock()
            mock_subquery.c.overall_score = MagicMock()
            
            # 平均値の結果オブジェクト
            mock_averages = MagicMock()
            mock_averages.empathy = 0.75
            mock_averages.clarity = 0.70
            mock_averages.listening = 0.80
            mock_averages.problem_solving = 0.65
            mock_averages.assertiveness = 0.72
            mock_averages.flexibility = 0.68
            mock_averages.overall = 0.72
            
            with patch.object(db.session, 'query') as mock_query:
                # 最初のクエリ（subquery作成用）
                mock_first_query = MagicMock()
                mock_first_query.join.return_value = mock_first_query
                mock_first_query.filter.return_value = mock_first_query
                mock_first_query.order_by.return_value = mock_first_query
                mock_first_query.limit.return_value = mock_first_query
                mock_first_query.subquery.return_value = mock_subquery
                
                # 2番目のクエリ（平均計算用）
                mock_second_query = MagicMock()
                mock_second_query.first.return_value = mock_averages
                
                # queryの呼び出し順序をモック
                mock_query.side_effect = [mock_first_query, mock_second_query]
                
                result = StrengthAnalysisService.get_average_scores(user_id=1)
                
                assert result['empathy'] == 0.75
                assert result['clarity'] == 0.70
                assert result['listening'] == 0.80
                assert result['problem_solving'] == 0.65
                assert result['assertiveness'] == 0.72
                assert result['flexibility'] == 0.68
                assert result['overall'] == 0.72

    def test_get_average_scores_database_error(self, app):
        """平均スコア取得時のデータベースエラーテスト"""
        with app.app_context():
            with patch.object(db.session, 'query') as mock_query:
                mock_query.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(AppError) as exc_info:
                    StrengthAnalysisService.get_average_scores(user_id=1)
                
                assert exc_info.value.code == "DATABASE_ERROR"
                assert exc_info.value.status_code == 500


class TestAchievementService:
    """アチーブメントサービスのテスト"""
    
    @pytest.fixture
    def sample_achievements(self, app):
        """サンプルアチーブメント"""
        with app.app_context():
            achievements = [
                Achievement(
                    id=1,
                    name='初めての一歩',
                    description='初めての練習セッションを完了しました',
                    icon='🎯',
                    category='練習回数',
                    threshold_type='session_count',
                    threshold_value=1,
                    points=10,
                    is_active=True
                ),
                Achievement(
                    id=2,
                    name='練習の習慣',
                    description='5回の練習セッションを完了しました',
                    icon='📚',
                    category='練習回数',
                    threshold_type='session_count',
                    threshold_value=5,
                    points=50,
                    is_active=True
                )
            ]
            return achievements
    
    def test_get_user_achievements_all(self, app, sample_achievements):
        """ユーザーのアチーブメント取得テスト（全て）"""
        with app.app_context():
            with patch.object(db.session, 'query') as mock_query:
                # モックチェーンの設定
                mock_query.return_value.outerjoin.return_value.filter.return_value.all.return_value = [
                    (sample_achievements[0], None),  # 未解除
                    (sample_achievements[1], MagicMock(
                        progress=5,
                        unlocked_at=datetime.now()
                    ))  # 解除済み
                ]
                
                achievements = AchievementService.get_user_achievements(user_id=1)
                
                assert len(achievements) == 2
                assert achievements[0]['unlocked'] is False
                assert achievements[1]['unlocked'] is True
                assert achievements[1]['progress'] == 5
    
    def test_get_user_achievements_unlocked_only(self, app, sample_achievements):
        """解除済みアチーブメントのみ取得テスト"""
        with app.app_context():
            with patch.object(db.session, 'query') as mock_query:
                mock_chain = MagicMock()
                mock_query.return_value = mock_chain
                mock_chain.outerjoin.return_value = mock_chain
                mock_chain.filter.return_value = mock_chain
                mock_chain.all.return_value = [(
                    sample_achievements[1],
                    MagicMock(progress=5, unlocked_at=datetime.now())
                )]
                
                achievements = AchievementService.get_user_achievements(
                    user_id=1,
                    unlocked_only=True
                )
                
                assert len(achievements) == 1
                assert achievements[0]['unlocked'] is True
    
    def test_unlock_achievement_new(self, app):
        """新規アチーブメント解除テスト"""
        with app.app_context():
            with patch.object(UserAchievement, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                
                with patch.object(db.session, 'add'):
                    with patch.object(db.session, 'commit'):
                        with patch.object(Achievement, 'query') as mock_achievement_query:
                            mock_achievement_query.get.return_value = MagicMock(name='テストアチーブメント')
                            
                            result = AchievementService._unlock_achievement(
                                user_id=1,
                                achievement_id=1
                            )
                            
                            assert result is True
    
    def test_unlock_achievement_already_unlocked(self, app):
        """既に解除済みのアチーブメントテスト"""
        with app.app_context():
            existing_achievement = MagicMock(unlocked_at=datetime.now())
            
            with patch.object(UserAchievement, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = existing_achievement
                
                result = AchievementService._unlock_achievement(
                    user_id=1,
                    achievement_id=1
                )
                
                assert result is False
    
    def test_check_session_achievements(self, app):
        """セッション完了系アチーブメントチェックテスト"""
        with app.app_context():
            with patch.object(PracticeSession, 'query') as mock_query:
                mock_query.filter_by.return_value.count.return_value = 5
                
                with patch.object(Achievement, 'query') as mock_achievement_query:
                    mock_achievements = [
                        MagicMock(id=1, threshold_value=1),
                        MagicMock(id=2, threshold_value=5)
                    ]
                    mock_achievement_query.filter_by.return_value.all.return_value = mock_achievements
                    
                    with patch.object(AchievementService, '_unlock_achievement') as mock_unlock:
                        mock_unlock.side_effect = [True, True]  # 両方解除成功
                        
                        unlocked = AchievementService._check_session_achievements(
                            user_id=1,
                            event_data={}
                        )
                        
                        assert len(unlocked) == 2
                        mock_unlock.assert_called()
    
    def test_get_total_points(self, app):
        """合計ポイント取得テスト"""
        with app.app_context():
            with patch.object(db.session, 'query') as mock_query:
                mock_query.return_value.join.return_value.filter.return_value.scalar.return_value = 150
                
                total = AchievementService.get_total_points(user_id=1)
                
                assert total == 150
    
    def test_get_total_points_no_achievements(self, app):
        """アチーブメントなしの場合のポイントテスト"""
        with app.app_context():
            with patch.object(db.session, 'query') as mock_query:
                mock_query.return_value.join.return_value.filter.return_value.scalar.return_value = None
                
                total = AchievementService.get_total_points(user_id=1)
                
                assert total == 0

    def test_check_and_unlock_achievements_session_completed(self, app):
        """セッション完了イベントでのアチーブメントチェックテスト"""
        with app.app_context():
            event_data = {'session_id': 1, 'scenario_id': 1}
            
            with patch.object(AchievementService, '_check_session_achievements') as mock_check:
                mock_achievement = MagicMock()
                mock_achievement.name = "初めての一歩"
                mock_check.return_value = [mock_achievement]
                
                unlocked = AchievementService.check_and_unlock_achievements(
                    user_id=1,
                    event_type='session_completed',
                    event_data=event_data
                )
                
                assert len(unlocked) == 1
                assert unlocked[0].name == "初めての一歩"
                mock_check.assert_called_once_with(1, event_data)

    def test_check_and_unlock_achievements_scenario_completed(self, app):
        """シナリオ完了イベントでのアチーブメントチェックテスト"""
        with app.app_context():
            event_data = {'scenario_id': 1}
            
            with patch.object(AchievementService, '_check_scenario_achievements') as mock_check:
                mock_achievement = MagicMock()
                mock_achievement.name = "シナリオマスター"
                mock_check.return_value = [mock_achievement]
                
                unlocked = AchievementService.check_and_unlock_achievements(
                    user_id=1,
                    event_type='scenario_completed',
                    event_data=event_data
                )
                
                assert len(unlocked) == 1
                assert unlocked[0].name == "シナリオマスター"

    def test_check_scenario_achievements_success(self, app):
        """シナリオアチーブメントチェック成功テスト"""
        with app.app_context():
            with patch.object(db.session, 'query') as mock_query:
                # 完了シナリオ数を3とする
                mock_query.return_value.filter.return_value.scalar.return_value = 3
                
                # アチーブメントのモック
                mock_achievements = [
                    MagicMock(id=1, threshold_type='scenario_complete', threshold_value=1),
                    MagicMock(id=2, threshold_type='unique_scenarios', threshold_value=3)
                ]
                
                with patch.object(Achievement, 'query') as mock_achievement_query:
                    mock_achievement_query.filter.return_value.all.return_value = mock_achievements
                    
                    with patch.object(AchievementService, '_unlock_achievement') as mock_unlock:
                        mock_unlock.side_effect = [True, True]
                        
                        unlocked = AchievementService._check_scenario_achievements(
                            user_id=1,
                            event_data={}
                        )
                        
                        assert len(unlocked) == 2
                        assert mock_unlock.call_count == 2


class TestScenarioService:
    """シナリオサービスのテスト"""
    
    def test_get_by_id_success(self, app):
        """IDでシナリオ取得成功テスト"""
        with app.app_context():
            mock_scenario = MagicMock(id=1, title="テストシナリオ")
            
            with patch.object(Scenario, 'query') as mock_query:
                mock_query.get.return_value = mock_scenario
                
                result = ScenarioService.get_by_id(1)
                
                assert result is mock_scenario
                mock_query.get.assert_called_once_with(1)
    
    def test_get_by_id_not_found(self, app):
        """存在しないIDでのシナリオ取得エラーテスト"""
        with app.app_context():
            with patch.object(Scenario, 'query') as mock_query:
                mock_query.get.return_value = None
                
                with pytest.raises(NotFoundError):
                    ScenarioService.get_by_id(999)
    
    def test_get_by_id_database_error(self, app):
        """データベースエラー時のテスト"""
        with app.app_context():
            with patch.object(Scenario, 'query') as mock_query:
                mock_query.get.side_effect = SQLAlchemyError("DB Error")
                
                with pytest.raises(AppError) as exc_info:
                    ScenarioService.get_by_id(1)
                
                assert exc_info.value.code == "DATABASE_ERROR"
                assert exc_info.value.status_code == 500
    
    def test_get_by_yaml_id_success(self, app):
        """YAML IDでシナリオ取得成功テスト"""
        with app.app_context():
            mock_scenario = MagicMock(yaml_id="test_scenario")
            
            with patch.object(Scenario, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = mock_scenario
                
                result = ScenarioService.get_by_yaml_id("test_scenario")
                
                assert result is mock_scenario
                mock_query.filter_by.assert_called_once_with(yaml_id="test_scenario")
    
    def test_get_by_yaml_id_not_found(self, app):
        """存在しないYAML IDでのシナリオ取得テスト"""
        with app.app_context():
            with patch.object(Scenario, 'query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = None
                
                result = ScenarioService.get_by_yaml_id("nonexistent")
                
                assert result is None
    
    def test_get_all_active_only(self, app):
        """アクティブシナリオのみ取得テスト"""
        with app.app_context():
            mock_scenarios = [MagicMock(id=i, is_active=True) for i in range(3)]
            
            with patch.object(Scenario, 'query') as mock_query:
                mock_query.filter_by.return_value.all.return_value = mock_scenarios
                
                result = ScenarioService.get_all(is_active=True)
                
                assert result == mock_scenarios
                mock_query.filter_by.assert_called_once_with(is_active=True)
    
    def test_get_all_include_inactive(self, app):
        """全シナリオ取得テスト（非アクティブ含む）"""
        with app.app_context():
            mock_scenarios = [MagicMock(id=i) for i in range(5)]
            
            with patch.object(Scenario, 'query') as mock_query:
                mock_query.all.return_value = mock_scenarios
                
                result = ScenarioService.get_all(is_active=False)
                
                assert result == mock_scenarios
                mock_query.all.assert_called_once()
    
    def test_sync_from_yaml_success(self, app):
        """YAML同期成功テスト"""
        with app.app_context():
            with patch('services.sync_scenarios_from_yaml') as mock_sync:
                ScenarioService.sync_from_yaml()
                
                mock_sync.assert_called_once()
    
    def test_sync_from_yaml_error(self, app):
        """YAML同期エラーテスト"""
        with app.app_context():
            with patch('services.sync_scenarios_from_yaml') as mock_sync:
                mock_sync.side_effect = Exception("Sync error")
                
                with pytest.raises(AppError) as exc_info:
                    ScenarioService.sync_from_yaml()
                
                assert exc_info.value.code == "SYNC_ERROR"


class TestSessionService:
    """セッションサービスのテスト"""
    
    def test_create_session_success(self, app):
        """セッション作成成功テスト"""
        with app.app_context():
            with patch.object(ScenarioService, 'get_by_id') as mock_get_scenario:
                mock_scenario = MagicMock(id=1)
                mock_get_scenario.return_value = mock_scenario
                
                with patch.object(db.session, 'add'):
                    with patch.object(db.session, 'commit'):
                        session = SessionService.create_session(
                            user_id=1,
                            session_type="scenario",
                            scenario_id=1,
                            ai_model="gemini-1.5-flash"
                        )
                        
                        assert session.user_id == 1
                        assert session.session_type == SessionType.SCENARIO
                        assert session.scenario_id == 1
                        assert session.ai_model == "gemini-1.5-flash"
    
    def test_create_session_invalid_type(self, app):
        """無効なセッションタイプでのエラーテスト"""
        with app.app_context():
            with pytest.raises(ValidationError):
                SessionService.create_session(
                    user_id=1,
                    session_type="invalid_type"
                )
    
    def test_create_session_scenario_not_found(self, app):
        """存在しないシナリオIDでのエラーテスト"""
        with app.app_context():
            with patch.object(ScenarioService, 'get_by_id') as mock_get_scenario:
                mock_get_scenario.side_effect = NotFoundError("シナリオ", "999")
                
                with pytest.raises(NotFoundError):
                    SessionService.create_session(
                        user_id=1,
                        session_type="scenario",
                        scenario_id=999
                    )
    
    def test_get_session_by_id_success(self, app):
        """IDでセッション取得成功テスト"""
        with app.app_context():
            mock_session = MagicMock(id=1, user_id=1)
            
            with patch.object(PracticeSession, 'query') as mock_query:
                mock_query.get.return_value = mock_session
                
                result = SessionService.get_session_by_id(1)
                
                assert result is mock_session
    
    def test_get_session_by_id_not_found(self, app):
        """存在しないIDでのセッション取得エラーテスト"""
        with app.app_context():
            with patch.object(PracticeSession, 'query') as mock_query:
                mock_query.get.return_value = None
                
                with pytest.raises(NotFoundError):
                    SessionService.get_session_by_id(999)
    
    def test_get_user_sessions_success(self, app):
        """ユーザーセッション履歴取得成功テスト"""
        with app.app_context():
            mock_sessions = [MagicMock(id=i, user_id=1) for i in range(5)]
            
            with patch.object(PracticeSession, 'query') as mock_query:
                mock_chain = MagicMock()
                mock_query.filter_by.return_value = mock_chain
                mock_chain.order_by.return_value = mock_chain
                mock_chain.limit.return_value = mock_chain
                mock_chain.all.return_value = mock_sessions
                
                result = SessionService.get_user_sessions(user_id=1, limit=5)
                
                assert result == mock_sessions
                mock_query.filter_by.assert_called_once_with(user_id=1)


class TestConversationService:
    """会話サービスのテスト"""
    
    def test_add_log_success(self, app):
        """会話ログ追加成功テスト"""
        with app.app_context():
            mock_session = MagicMock(id=1)
            
            with patch.object(SessionService, 'get_session_by_id', return_value=mock_session):
                with patch.object(db.session, 'add'):
                    with patch.object(db.session, 'commit'):
                        log = ConversationService.add_log(
                            session_id=1,
                            message="テストメッセージ",
                            is_user=True
                        )
                        
                        assert log.session_id == 1
                        assert log.speaker == 'user'
                        assert log.message == "テストメッセージ"
                        assert log.message_type == 'text'
    
    def test_add_log_ai_message(self, app):
        """AI応答ログ追加テスト"""
        with app.app_context():
            mock_session = MagicMock(id=1)
            
            with patch.object(SessionService, 'get_session_by_id', return_value=mock_session):
                with patch.object(db.session, 'add'):
                    with patch.object(db.session, 'commit'):
                        log = ConversationService.add_log(
                            session_id=1,
                            message="AI応答",
                            is_user=False
                        )
                        
                        assert log.speaker == 'ai'
    
    def test_add_log_session_not_found(self, app):
        """存在しないセッションでのログ追加エラーテスト"""
        with app.app_context():
            with patch.object(SessionService, 'get_session_by_id') as mock_get_session:
                mock_get_session.side_effect = NotFoundError("練習セッション", "999")
                
                with pytest.raises(NotFoundError):
                    ConversationService.add_log(
                        session_id=999,
                        message="テストメッセージ",
                        is_user=True
                    )
    
    def test_get_session_logs_success(self, app):
        """セッションログ取得成功テスト"""
        with app.app_context():
            mock_logs = [MagicMock(id=i, session_id=1) for i in range(3)]
            
            with patch.object(ConversationLog, 'query') as mock_query:
                mock_chain = MagicMock()
                mock_query.filter_by.return_value = mock_chain
                mock_chain.order_by.return_value = mock_chain
                mock_chain.all.return_value = mock_logs
                
                result = ConversationService.get_session_logs(session_id=1)
                
                assert result == mock_logs
                mock_query.filter_by.assert_called_once_with(session_id=1)
    
    def test_get_session_logs_with_limit(self, app):
        """制限付きセッションログ取得テスト"""
        with app.app_context():
            mock_logs = [MagicMock(id=i) for i in range(2)]
            
            with patch.object(ConversationLog, 'query') as mock_query:
                mock_chain = MagicMock()
                mock_query.filter_by.return_value = mock_chain
                mock_chain.order_by.return_value = mock_chain
                mock_chain.limit.return_value = mock_chain
                mock_chain.all.return_value = mock_logs
                
                result = ConversationService.get_session_logs(session_id=1, limit=2)
                
                assert result == mock_logs
                mock_chain.limit.assert_called_once_with(2)


class TestUserService:
    """ユーザーサービスのテスト"""
    
    def test_get_by_id_success(self, app):
        """IDでユーザー取得成功テスト"""
        with app.app_context():
            mock_user = MagicMock(id=1, username="testuser")
            
            with patch.object(User, 'query') as mock_query:
                mock_query.get.return_value = mock_user
                
                result = UserService.get_by_id(1)
                
                assert result is mock_user
    
    def test_get_by_id_not_found(self, app):
        """存在しないIDでのユーザー取得エラーテスト"""
        with app.app_context():
            with patch.object(User, 'query') as mock_query:
                mock_query.get.return_value = None
                
                with pytest.raises(NotFoundError):
                    UserService.get_by_id(999)
    
    def test_create_user_success(self, app):
        """ユーザー作成成功テスト"""
        with app.app_context():
            with patch.object(User, 'query') as mock_query:
                mock_query.filter.return_value.first.return_value = None
                
                with patch.object(db.session, 'add'):
                    with patch.object(db.session, 'commit'):
                        user = UserService.create_user(
                            username="newuser",
                            email="new@example.com",
                            password_hash="hashed_password"
                        )
                        
                        assert user.username == "newuser"
                        assert user.email == "new@example.com"
                        assert user.password_hash == "hashed_password"
    
    def test_create_user_duplicate_username(self, app):
        """重複ユーザー名でのエラーテスト"""
        with app.app_context():
            existing_user = MagicMock(username="testuser", email="other@example.com")
            
            with patch.object(User, 'query') as mock_query:
                mock_query.filter.return_value.first.return_value = existing_user
                
                with pytest.raises(ValidationError) as exc_info:
                    UserService.create_user(
                        username="testuser",
                        email="new@example.com",
                        password_hash="hashed_password"
                    )
                
                assert "ユーザー名は既に使用されています" in str(exc_info.value)
    
    def test_create_user_duplicate_email(self, app):
        """重複メールアドレスでのエラーテスト"""
        with app.app_context():
            existing_user = MagicMock(username="otheruser", email="test@example.com")
            
            with patch.object(User, 'query') as mock_query:
                mock_query.filter.return_value.first.return_value = existing_user
                
                with pytest.raises(ValidationError) as exc_info:
                    UserService.create_user(
                        username="newuser",
                        email="test@example.com",
                        password_hash="hashed_password"
                    )
                
                assert "メールアドレスは既に使用されています" in str(exc_info.value)


class TestIntegration:
    """統合テスト"""
    
    def test_strength_analysis_triggers_achievement(self, app):
        """強み分析がアチーブメント解除をトリガーするテスト"""
        with app.app_context():
            mock_session = MagicMock(id=1, user_id=1)
            
            high_score_result = {
                'empathy': 0.85,
                'clarity': 0.82,
                'listening': 0.88,
                'problem_solving': 0.75,
                'assertiveness': 0.78,
                'flexibility': 0.80
            }
            
            with patch.object(SessionService, 'get_session_by_id', return_value=mock_session):
                with patch.object(db.session, 'add'):
                    with patch.object(db.session, 'commit'):
                        with patch.object(StrengthAnalysis, 'query') as mock_query:
                            mock_query.filter_by.return_value.first.return_value = None
                            
                            with patch.object(StrengthAnalysisService, '_check_achievements') as mock_check:
                                analysis = StrengthAnalysisService.save_analysis(
                                    session_id=1,
                                    analysis_result=high_score_result
                                )
                                
                                # アチーブメントチェックが呼ばれたことを確認
                                mock_check.assert_called_once_with(1, analysis)


# ヘルパー関数のテスト
class TestHelperFunctions:
    """services.pyのヘルパー関数のテスト"""
    
    def test_get_or_create_practice_session_no_user(self, app):
        """ユーザーIDなしの場合のテスト"""
        with app.app_context():
            from services import get_or_create_practice_session
            result = get_or_create_practice_session(None, "test_scenario", "scenario")
            assert result is None
    
    def test_get_or_create_practice_session_new_session(self, app, auth_user):
        """新しいセッション作成のテスト"""
        with app.app_context():
            from services import get_or_create_practice_session
            # PracticeSessionクエリを直接モック
            with patch('services.PracticeSession.query') as mock_query:
                mock_query.filter_by.return_value.order_by.return_value.first.return_value = None
                
                # SessionService.create_sessionをモック
                with patch('services.SessionService.create_session') as mock_create:
                    mock_session = MagicMock()
                    mock_create.return_value = mock_session
                    
                    result = get_or_create_practice_session(auth_user.id, 1, "scenario")
                    
                    assert result == mock_session
                    mock_create.assert_called_once_with(
                        user_id=auth_user.id,
                        session_type="scenario",
                        scenario_id=1
                    )
    
    def test_get_or_create_practice_session_reuse_recent(self, app, auth_user):
        """1時間以内のセッション再利用のテスト"""
        with app.app_context():
            from services import get_or_create_practice_session
            from datetime import datetime, timedelta
            
            # 30分前のセッション
            recent_time = datetime.utcnow() - timedelta(minutes=30)
            mock_session = MagicMock()
            mock_session.started_at = recent_time
            
            with patch('services.PracticeSession.query') as mock_query:
                mock_query.filter_by.return_value.order_by.return_value.first.return_value = mock_session
                
                result = get_or_create_practice_session(auth_user.id, 1, "scenario")
                
                assert result == mock_session
    
    def test_get_or_create_practice_session_error(self, app, auth_user):
        """エラー発生時の処理テスト"""
        with app.app_context():
            from services import get_or_create_practice_session
            with patch.object(db.session, 'query') as mock_query:
                mock_query.side_effect = Exception("Database error")
                
                result = get_or_create_practice_session(auth_user.id, 1, "scenario")
                
                assert result is None
    
    def test_add_conversation_log_no_session(self, app):
        """セッションなしの場合のテスト"""
        with app.app_context():
            from services import add_conversation_log
            result = add_conversation_log(None, "user message", "ai response")
            assert result is False
    
    def test_add_conversation_log_success(self, app):
        """正常な会話ログ追加のテスト"""
        with app.app_context():
            from services import add_conversation_log
            mock_session = MagicMock()
            mock_session.id = 123
            
            with patch('services.ConversationService.add_log') as mock_add_log:
                mock_add_log.return_value = True
                
                result = add_conversation_log(mock_session, "user message", "ai response")
                
                assert result is True
                # ユーザーメッセージとAIレスポンス両方が記録される
                assert mock_add_log.call_count == 2
                
                # ユーザーメッセージの呼び出し
                mock_add_log.assert_any_call(
                    session_id=123,
                    message="user message",
                    is_user=True
                )
                
                # AIレスポンスの呼び出し
                mock_add_log.assert_any_call(
                    session_id=123,
                    message="ai response",
                    is_user=False
                )
    
    def test_add_conversation_log_error(self, app):
        """エラー発生時の処理テスト"""
        with app.app_context():
            from services import add_conversation_log
            mock_session = MagicMock()
            mock_session.id = 123
            
            with patch('services.ConversationService.add_log') as mock_add_log:
                mock_add_log.side_effect = Exception("Database error")
                
                result = add_conversation_log(mock_session, "user message", "ai response")
                
                assert result is False
    
    def test_get_conversation_history_no_session(self, app):
        """セッションなしの場合のテスト"""
        with app.app_context():
            from services import get_conversation_history
            result = get_conversation_history(None)
            assert result == []
    
    def test_get_conversation_history_success(self, app):
        """正常な会話履歴取得のテスト"""
        with app.app_context():
            from services import get_conversation_history
            mock_session = MagicMock()
            mock_session.id = 123
            
            # モックログデータ
            mock_log1 = MagicMock()
            mock_log1.speaker = 'user'
            mock_log1.message = 'Hello'
            
            mock_log2 = MagicMock()
            mock_log2.speaker = 'ai'
            mock_log2.message = 'Hi there!'
            
            mock_log3 = MagicMock()
            mock_log3.speaker = 'user'
            mock_log3.message = 'How are you?'
            
            mock_logs = [mock_log1, mock_log2, mock_log3]
            
            with patch('services.ConversationService.get_session_logs') as mock_get_logs:
                mock_get_logs.return_value = mock_logs
                
                result = get_conversation_history(mock_session, limit=10)
                
                mock_get_logs.assert_called_once_with(123, limit=20)  # limit * 2
                
                # 結果の検証
                expected = [
                    {'human': 'Hello', 'ai': 'Hi there!'},
                    {'human': 'How are you?'}  # AIレスポンスがない場合
                ]
                assert result == expected
    
    def test_get_conversation_history_error(self, app):
        """エラー発生時の処理テスト"""
        with app.app_context():
            from services import get_conversation_history
            mock_session = MagicMock()
            mock_session.id = 123
            
            with patch('services.ConversationService.get_session_logs') as mock_get_logs:
                mock_get_logs.side_effect = Exception("Database error")
                
                result = get_conversation_history(mock_session)
                
                assert result == []


class TestAchievementServiceTimeBasedTests:
    """AchievementServiceの時間帯別アチーブメントテスト"""
    
    def test_check_session_achievements_morning_practice(self, app):
        """朝練習アチーブメントのテスト"""
        with app.app_context():
            # datetime.datetime.now()をモック（これが実際に呼ばれる）
            with patch('datetime.datetime') as mock_datetime_class:
                # 朝8時の時間をモック
                mock_now = MagicMock()
                mock_now.hour = 8
                mock_now.weekday.return_value = 1  # 火曜日
                mock_datetime_class.now.return_value = mock_now
                
                # セッション数のモック
                with patch.object(PracticeSession, 'query') as mock_query:
                    mock_query.filter_by.return_value.count.return_value = 5
                    
                    # 朝練習アチーブメントのモック
                    mock_achievement = MagicMock()
                    mock_achievement.id = 1
                    mock_achievement.name = "朝練習"
                    
                    with patch.object(Achievement, 'query') as mock_ach_query:
                        mock_ach_query.filter_by.return_value.first.return_value = mock_achievement
                        
                        with patch.object(AchievementService, '_unlock_achievement', return_value=True):
                            unlocked = AchievementService._check_session_achievements(1, {})
                            
                            assert len(unlocked) >= 1
                            # 朝練習アチーブメントが含まれている
                            assert any(ach.name == "朝練習" for ach in unlocked)
    
    def test_check_session_achievements_night_practice(self, app):
        """夜練習アチーブメントのテスト"""
        with app.app_context():
            # datetime.datetime.now()をモック（これが実際に呼ばれる）
            with patch('datetime.datetime') as mock_datetime_class:
                # 夜23時の時間をモック
                mock_now = MagicMock()
                mock_now.hour = 23
                mock_now.weekday.return_value = 1  # 火曜日
                mock_datetime_class.now.return_value = mock_now
                
                # セッション数のモック
                with patch.object(PracticeSession, 'query') as mock_query:
                    mock_query.filter_by.return_value.count.return_value = 5
                    
                    # 夜練習アチーブメントのモック
                    mock_achievement = MagicMock()
                    mock_achievement.id = 2
                    mock_achievement.name = "夜練習"
                    
                    with patch.object(Achievement, 'query') as mock_ach_query:
                        mock_ach_query.filter_by.return_value.first.return_value = mock_achievement
                        
                        with patch.object(AchievementService, '_unlock_achievement', return_value=True):
                            unlocked = AchievementService._check_session_achievements(1, {})
                            
                            assert len(unlocked) >= 1
                            # 夜練習アチーブメントが含まれている
                            assert any(ach.name == "夜練習" for ach in unlocked)
    
    def test_check_session_achievements_weekend_practice(self, app):
        """週末練習アチーブメントのテスト"""
        with app.app_context():
            # datetime.datetime.now()をモック（これが実際に呼ばれる）
            with patch('datetime.datetime') as mock_datetime_class:
                # 土曜日の時間をモック
                mock_now = MagicMock()
                mock_now.hour = 14
                mock_now.weekday.return_value = 5  # 土曜日
                mock_datetime_class.now.return_value = mock_now
                
                # セッション数のモック
                with patch.object(PracticeSession, 'query') as mock_query:
                    mock_query.filter_by.return_value.count.return_value = 5
                    
                    # 週末練習アチーブメントのモック
                    mock_achievement = MagicMock()
                    mock_achievement.id = 3
                    mock_achievement.name = "週末練習"
                    
                    with patch.object(Achievement, 'query') as mock_ach_query:
                        mock_ach_query.filter_by.return_value.first.return_value = mock_achievement
                        
                        with patch.object(AchievementService, '_unlock_achievement', return_value=True):
                            unlocked = AchievementService._check_session_achievements(1, {})
                            
                            assert len(unlocked) >= 1
                            # 週末練習アチーブメントが含まれている
                            assert any(ach.name == "週末練習" for ach in unlocked)
    
    def test_check_scenario_achievements_all_scenarios(self, app):
        """全シナリオ完了アチーブメントのテスト"""
        with app.app_context():
            # 全シナリオ完了のケースをテスト（lines 711-715）
            with patch.object(db.session, 'query') as mock_session_query:
                # 完了シナリオ数のモック
                mock_session_query.return_value.filter.return_value.scalar.return_value = 30
                
                # 全シナリオアチーブメントのモック
                mock_achievement = MagicMock()
                mock_achievement.id = 4
                mock_achievement.name = "全シナリオ制覇"
                mock_achievement.threshold_type = "all_scenarios"
                
                with patch.object(Achievement, 'query') as mock_ach_query:
                    mock_ach_query.filter.return_value.all.return_value = [mock_achievement]
                    
                    # 全シナリオ数のモック
                    with patch.object(Scenario, 'query') as mock_scenario_query:
                        mock_scenario_query.filter_by.return_value.count.return_value = 30
                        
                        with patch.object(AchievementService, '_unlock_achievement', return_value=True):
                            unlocked = AchievementService._check_scenario_achievements(1, {})
                            
                            assert len(unlocked) >= 1
                            # 全シナリオ制覇アチーブメントが含まれている
                            assert any(ach.name == "全シナリオ制覇" for ach in unlocked)