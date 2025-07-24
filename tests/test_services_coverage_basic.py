"""
サービスレイヤーの基本カバレッジテスト

開発規約準拠：モック禁止、実際のデータベースを使用
services.pyの主要な未カバー部分のみに集中したシンプルなテスト
"""
import pytest
from datetime import datetime, timedelta

from models import db, User, Scenario, PracticeSession, ConversationLog, StrengthAnalysis, Achievement, UserAchievement, SessionType, DifficultyLevel
from services import (
    ScenarioService, SessionService, ConversationService, UserService, 
    StrengthAnalysisService, AchievementService,
    get_or_create_practice_session, add_conversation_log, get_conversation_history
)
from errors import NotFoundError, AppError, ValidationError


class TestScenarioServiceBasic:
    """ScenarioService の基本カバレッジテスト"""
    
    def test_scenario_basic_operations(self, app):
        """シナリオの基本操作テスト"""
        with app.app_context():
            # テスト用シナリオ作成
            scenario = Scenario(
                yaml_id='basic_test_scenario',
                title='Basic Test Scenario',
                summary='Basic test',
                difficulty=DifficultyLevel.BEGINNER,
                category='test'
            )
            db.session.add(scenario)
            db.session.commit()
            
            try:
                # get_by_id テスト
                result = ScenarioService.get_by_id(scenario.id)
                assert result.id == scenario.id
                assert result.title == 'Basic Test Scenario'
                
                # get_by_yaml_id テスト
                result_yaml = ScenarioService.get_by_yaml_id('basic_test_scenario')
                assert result_yaml.id == scenario.id
                
                # 存在しないIDでのエラーテスト
                with pytest.raises(NotFoundError):
                    ScenarioService.get_by_id(999999)
                
            finally:
                db.session.delete(scenario)
                db.session.commit()


class TestSessionServiceBasic:
    """SessionService の基本カバレッジテスト"""
    
    def test_session_basic_operations(self, app):
        """セッションの基本操作テスト"""
        with app.app_context():
            # テスト用ユーザー作成（重複を避けるためUUID使用）
            import uuid
            from werkzeug.security import generate_password_hash
            unique_id = str(uuid.uuid4())[:8]
            user = User(
                username=f'basic_test_user_{unique_id}',
                email=f'basic_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            try:
                # チャットセッション作成
                session = SessionService.create_session(
                    user_id=user.id,
                    session_type='free_talk'
                )
                
                assert session.id is not None
                assert session.user_id == user.id
                assert session.session_type == SessionType.FREE_TALK
                
                # 無効なセッションタイプテスト
                with pytest.raises(ValidationError):
                    SessionService.create_session(
                        user_id=user.id,
                        session_type='invalid_type'
                    )
                
            finally:
                # クリーンアップ
                if 'session' in locals():
                    db.session.delete(session)
                db.session.delete(user)
                db.session.commit()


class TestConversationServiceBasic:
    """ConversationService の基本カバレッジテスト"""
    
    def test_conversation_basic_operations(self, app):
        """会話の基本操作テスト"""
        with app.app_context():
            # テスト用ユーザー作成（重複を避けるためUUID使用）
            import uuid
            from werkzeug.security import generate_password_hash
            unique_id = str(uuid.uuid4())[:8]
            user = User(
                username=f'conv_test_user_{unique_id}',
                email=f'conv_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # セッション作成
            session = SessionService.create_session(
                user_id=user.id,
                session_type='free_talk'
            )
            
            try:
                # 会話ログ追加
                user_log = ConversationService.add_log(
                    session_id=session.id,
                    message='テストメッセージ',
                    is_user=True
                )
                
                ai_log = ConversationService.add_log(
                    session_id=session.id,
                    message='AIレスポンス',
                    is_user=False
                )
                
                assert user_log.speaker == 'user'
                assert ai_log.speaker == 'ai'
                
                # ログ取得
                logs = ConversationService.get_session_logs(session.id)
                assert len(logs) == 2
                
                # 存在しないセッションIDでのエラーテスト
                with pytest.raises(NotFoundError):
                    ConversationService.add_log(
                        session_id=999999,
                        message='エラーテスト',
                        is_user=True
                    )
                
            finally:
                # クリーンアップ
                logs = ConversationService.get_session_logs(session.id)
                for log in logs:
                    db.session.delete(log)
                db.session.delete(session)
                db.session.delete(user)
                db.session.commit()


class TestUserServiceBasic:
    """UserService の基本カバレッジテスト"""
    
    def test_user_basic_operations(self, app):
        """ユーザーの基本操作テスト"""
        with app.app_context():
            # ユーザー作成（重複を避けるためUUID使用）
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            user = UserService.create_user(
                username=f'user_basic_test_{unique_id}',
                email=f'userbasic_{unique_id}@test.com',
                password_hash='hashed_password'
            )
            
            try:
                # ユーザー取得
                retrieved_user = UserService.get_by_id(user.id)
                assert retrieved_user.username == f'user_basic_test_{unique_id}'
                
                # 重複ユーザー作成エラー
                with pytest.raises(ValidationError) as exc_info:
                    UserService.create_user(
                        username=f'user_basic_test_{unique_id}',  # 重複
                        email='different@test.com',
                        password_hash='different_password'
                    )
                assert "このユーザー名は既に使用されています" in str(exc_info.value.message)
                
                # 存在しないユーザー取得エラー
                with pytest.raises(NotFoundError):
                    UserService.get_by_id(999999)
                
            finally:
                db.session.delete(user)
                db.session.commit()


class TestHelperFunctionsBasic:
    """ヘルパー関数の基本カバレッジテスト"""
    
    def test_helper_functions_basic(self, app):
        """ヘルパー関数の基本テスト"""
        with app.app_context():
            # テスト用ユーザー作成（重複を避けるためUUID使用）
            import uuid
            from werkzeug.security import generate_password_hash
            unique_id = str(uuid.uuid4())[:8]
            user = User(
                username=f'helper_test_user_{unique_id}',
                email=f'helper_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            try:
                # get_or_create_practice_session テスト
                session1 = get_or_create_practice_session(
                    user_id=user.id,
                    scenario_id=None,  # シナリオIDはNoneまたは整数のみ
                    session_type='free_talk'
                )
                
                assert session1 is not None
                
                # 同じパラメータで再度呼び出し（再利用されるはず）
                session2 = get_or_create_practice_session(
                    user_id=user.id,
                    scenario_id=None,
                    session_type='free_talk'
                )
                
                assert session2.id == session1.id
                
                # add_conversation_log テスト
                result = add_conversation_log(
                    session=session1,
                    user_message='テストユーザーメッセージ',
                    ai_response='テストAIレスポンス'
                )
                
                assert result is True
                
                # get_conversation_history テスト
                history = get_conversation_history(session1, limit=5)
                assert len(history) == 1
                assert history[0]['human'] == 'テストユーザーメッセージ'
                assert history[0]['ai'] == 'テストAIレスポンス'
                
                # session=None でのテスト
                assert add_conversation_log(None, 'test', 'test') is False
                assert get_conversation_history(None) == []
                
            finally:
                # クリーンアップ
                if 'session1' in locals():
                    logs = ConversationService.get_session_logs(session1.id)
                    for log in logs:
                        db.session.delete(log)
                    db.session.delete(session1)
                db.session.delete(user)
                db.session.commit()


class TestStrengthAnalysisBasic:
    """StrengthAnalysisService の基本カバレッジテスト"""
    
    def test_strength_analysis_basic(self, app):
        """強み分析の基本操作テスト"""
        with app.app_context():
            # テスト用ユーザー作成（重複を避けるためUUID使用）
            import uuid
            from werkzeug.security import generate_password_hash
            unique_id = str(uuid.uuid4())[:8]
            user = User(
                username=f'strength_test_user_{unique_id}',
                email=f'strength_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # セッション作成
            session = SessionService.create_session(
                user_id=user.id,
                session_type='scenario'
            )
            
            try:
                # 分析結果保存
                analysis_result = {
                    'empathy': 0.8,
                    'clarity': 0.7,
                    'listening': 0.9,
                    'problem_solving': 0.6,
                    'assertiveness': 0.75,
                    'flexibility': 0.85
                }
                
                analysis = StrengthAnalysisService.save_analysis(
                    session_id=session.id,
                    analysis_result=analysis_result,
                    feedback_text='テストフィードバック'
                )
                
                assert analysis.empathy == 0.8
                assert analysis.clarity == 0.7
                assert analysis.feedback_text == 'テストフィードバック'
                
                # 総合スコア計算確認
                expected_overall = sum(analysis_result.values()) / 6.0
                assert abs(analysis.overall_score - expected_overall) < 0.001
                
            finally:
                # クリーンアップ
                if 'analysis' in locals():
                    db.session.delete(analysis)
                db.session.delete(session)
                db.session.delete(user)
                db.session.commit()


def test_services_coverage_execution():
    """テスト実行確認用"""
    assert True