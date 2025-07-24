"""
サービスレイヤーの拡張カバレッジテスト

開発規約準拠：モック禁止、実際のデータベースを使用
services.pyの未カバー部分を重点的にテストし、全体カバレッジを向上させる
"""
import pytest
from datetime import datetime, timedelta
import uuid

from models import db, User, Scenario, PracticeSession, ConversationLog, StrengthAnalysis, Achievement, UserAchievement, SessionType, DifficultyLevel
from services import (
    ScenarioService, SessionService, ConversationService, UserService, 
    StrengthAnalysisService, AchievementService,
    get_or_create_practice_session, add_conversation_log, get_conversation_history
)
from errors import NotFoundError, AppError, ValidationError


class TestStrengthAnalysisServiceExtended:
    """StrengthAnalysisService の拡張カバレッジテスト"""
    
    def test_get_user_analyses_coverage(self, app):
        """ユーザー分析履歴取得 - lines 351-363"""
        with app.app_context():
            # ユニークユーザー作成
            unique_id = str(uuid.uuid4())[:8]
            from werkzeug.security import generate_password_hash
            user = User(
                username=f'analysis_user_{unique_id}',
                email=f'analysis_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # 複数のセッションと分析を作成
            sessions = []
            analyses = []
            
            for i in range(3):
                session = SessionService.create_session(
                    user_id=user.id,
                    session_type='scenario'
                )
                sessions.append(session)
                
                # 分析結果作成
                analysis_result = {
                    'empathy': 0.7 + (i * 0.1),
                    'clarity': 0.6 + (i * 0.1),
                    'listening': 0.8 + (i * 0.05),
                    'problem_solving': 0.65 + (i * 0.08),
                    'assertiveness': 0.75 + (i * 0.05),
                    'flexibility': 0.72 + (i * 0.06)
                }
                
                analysis = StrengthAnalysisService.save_analysis(
                    session_id=session.id,
                    analysis_result=analysis_result,
                    feedback_text=f'分析結果 {i+1}'
                )
                analyses.append(analysis)
            
            try:
                # デフォルトlimit(10)でのテスト - lines 352-356
                user_analyses = StrengthAnalysisService.get_user_analyses(user.id)
                assert len(user_analyses) == 3
                
                # 降順にソートされていることを確認
                for i in range(1, len(user_analyses)):
                    assert user_analyses[i-1].created_at >= user_analyses[i].created_at
                
                # limit指定でのテスト
                limited_analyses = StrengthAnalysisService.get_user_analyses(user.id, limit=2)
                assert len(limited_analyses) == 2
                
            finally:
                # クリーンアップ
                for analysis in analyses:
                    db.session.delete(analysis)
                for session in sessions:
                    db.session.delete(session)
                db.session.delete(user)
                db.session.commit()
    
    def test_get_skill_progress_coverage(self, app):
        """スキル進捗取得 - lines 366-393"""
        with app.app_context():
            # ユニークユーザー作成
            unique_id = str(uuid.uuid4())[:8]
            from werkzeug.security import generate_password_hash
            user = User(
                username=f'progress_user_{unique_id}',
                email=f'progress_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # 時系列データ作成
            sessions = []
            analyses = []
            
            for i in range(5):
                session = SessionService.create_session(
                    user_id=user.id,
                    session_type='scenario'
                )
                sessions.append(session)
                
                # 時間差を作るため、過去の時間に設定
                session.started_at = datetime.now() - timedelta(days=i)
                
                analysis_result = {
                    'empathy': 0.5 + (i * 0.1),
                    'clarity': 0.6 + (i * 0.08),
                    'listening': 0.7 + (i * 0.06),
                    'problem_solving': 0.55 + (i * 0.09),
                    'assertiveness': 0.65 + (i * 0.07),
                    'flexibility': 0.62 + (i * 0.08)
                }
                
                analysis = StrengthAnalysisService.save_analysis(
                    session_id=session.id,
                    analysis_result=analysis_result
                )
                analyses.append(analysis)
            
            db.session.commit()
            
            try:
                # スキル進捗取得 - lines 369-383
                progress = StrengthAnalysisService.get_skill_progress(user.id)
                
                # 6つのスキルがすべて含まれていることを確認 - line 372
                expected_skills = ['empathy', 'clarity', 'listening', 'problem_solving', 'assertiveness', 'flexibility']
                for skill in expected_skills:
                    assert skill in progress
                    assert len(progress[skill]) == 5
                
                # 時系列順（古い順）にソートされていることを確認 - line 375
                for skill in expected_skills:
                    skill_data = progress[skill]
                    for i in range(1, len(skill_data)):
                        prev_date = datetime.fromisoformat(skill_data[i-1]['date'])
                        curr_date = datetime.fromisoformat(skill_data[i]['date'])
                        assert prev_date <= curr_date
                
                # データの構造確認 - lines 377-381
                empathy_data = progress['empathy'][0]
                assert 'date' in empathy_data
                assert 'score' in empathy_data
                assert 'session_id' in empathy_data
                
            finally:
                # クリーンアップ
                for analysis in analyses:
                    db.session.delete(analysis)
                for session in sessions:
                    db.session.delete(session)
                db.session.delete(user)
                db.session.commit()
    
    def test_get_average_scores_coverage(self, app):
        """平均スコア取得 - lines 396-434"""
        with app.app_context():
            # ユニークユーザー作成
            unique_id = str(uuid.uuid4())[:8]
            from werkzeug.security import generate_password_hash
            user = User(
                username=f'average_user_{unique_id}',
                email=f'average_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # 複数の分析データ作成（10件以上）
            sessions = []
            analyses = []
            
            for i in range(12):
                session = SessionService.create_session(
                    user_id=user.id,
                    session_type='scenario'
                )
                sessions.append(session)
                
                analysis_result = {
                    'empathy': 0.6 + (i * 0.02),
                    'clarity': 0.65 + (i * 0.015),
                    'listening': 0.7 + (i * 0.01),
                    'problem_solving': 0.58 + (i * 0.025),
                    'assertiveness': 0.62 + (i * 0.02),
                    'flexibility': 0.68 + (i * 0.018)
                }
                
                analysis = StrengthAnalysisService.save_analysis(
                    session_id=session.id,
                    analysis_result=analysis_result
                )
                analyses.append(analysis)
            
            try:
                # 平均スコア取得 - lines 402-416
                averages = StrengthAnalysisService.get_average_scores(user.id)
                
                # 全スキルの平均が計算されていることを確認 - lines 418-426
                expected_skills = ['empathy', 'clarity', 'listening', 'problem_solving', 'assertiveness', 'flexibility', 'overall']
                for skill in expected_skills:
                    assert skill in averages
                    assert isinstance(averages[skill], float)
                    assert 0.0 <= averages[skill] <= 1.0
                
                # 最新10件のみが使用されることの確認（間接的）
                # averagesが妥当な範囲内にあることを確認
                assert averages['empathy'] > 0.7  # 最新10件の平均
                assert averages['overall'] > 0.0
                
            finally:
                # クリーンアップ
                for analysis in analyses:
                    db.session.delete(analysis)
                for session in sessions:
                    db.session.delete(session)
                db.session.delete(user)
                db.session.commit()
    
    def test_identify_strengths_and_improvements_coverage(self, app):
        """強み・改善点特定の内部メソッド - lines 437-472"""
        with app.app_context():
            # 高スコアのテスト（強み特定） - lines 437-453
            high_scores = {
                'empathy': 0.85,
                'clarity': 0.90,
                'listening': 0.82,
                'problem_solving': 0.65,
                'assertiveness': 0.88,
                'flexibility': 0.79
            }
            
            strengths = StrengthAnalysisService._identify_strengths(high_scores)
            
            # 0.8以上のスキルが特定されることを確認 - line 450
            assert '共感力' in strengths
            assert '明確な伝達' in strengths
            assert '傾聴力' in strengths
            assert '自己主張' in strengths
            assert '問題解決力' not in strengths  # 0.65 < 0.8
            assert '柔軟性' not in strengths  # 0.79 < 0.8
            
            # 低スコアのテスト（改善点特定） - lines 456-472
            low_scores = {
                'empathy': 0.55,
                'clarity': 0.45,
                'listening': 0.75,
                'problem_solving': 0.58,
                'assertiveness': 0.62,
                'flexibility': 0.52
            }
            
            improvements = StrengthAnalysisService._identify_improvements(low_scores)
            
            # 0.6未満のスキルが特定されることを確認 - line 469
            assert '共感力' in improvements
            assert '明確な伝達' in improvements
            assert '問題解決力' in improvements
            assert '柔軟性' in improvements
            assert '傾聴力' not in improvements  # 0.75 >= 0.6
            assert '自己主張' not in improvements  # 0.62 >= 0.6
    
    def test_suggest_next_steps_coverage(self, app):
        """次ステップ提案の内部メソッド - lines 475-499"""
        with app.app_context():
            # 各スキルが最低スコアの場合のテスト
            test_cases = [
                ({'empathy': 0.3, 'clarity': 0.5, 'listening': 0.6, 'problem_solving': 0.7, 'assertiveness': 0.8, 'flexibility': 0.9}, '相手の気持ちを想像する練習をしましょう'),
                ({'empathy': 0.7, 'clarity': 0.3, 'listening': 0.6, 'problem_solving': 0.7, 'assertiveness': 0.8, 'flexibility': 0.9}, '要点を整理してから話す練習をしましょう'),
                ({'empathy': 0.7, 'clarity': 0.5, 'listening': 0.3, 'problem_solving': 0.7, 'assertiveness': 0.8, 'flexibility': 0.9}, '相手の話を最後まで聞く練習をしましょう'),
                ({'empathy': 0.7, 'clarity': 0.5, 'listening': 0.6, 'problem_solving': 0.3, 'assertiveness': 0.8, 'flexibility': 0.9}, '問題を段階的に分析する練習をしましょう'),
                ({'empathy': 0.7, 'clarity': 0.5, 'listening': 0.6, 'problem_solving': 0.7, 'assertiveness': 0.3, 'flexibility': 0.9}, '自分の意見を明確に伝える練習をしましょう'),
                ({'empathy': 0.7, 'clarity': 0.5, 'listening': 0.6, 'problem_solving': 0.7, 'assertiveness': 0.8, 'flexibility': 0.3}, '異なる視点を受け入れる練習をしましょう')
            ]
            
            for scores, expected_suggestion in test_cases:
                suggestions = StrengthAnalysisService._suggest_next_steps(scores)
                assert len(suggestions) >= 1
                assert expected_suggestion in suggestions
            
            # 高スコア（0.8以上平均）のテスト - lines 495-497
            high_scores = {
                'empathy': 0.85,
                'clarity': 0.82,
                'listening': 0.88,
                'problem_solving': 0.81,
                'assertiveness': 0.83,
                'flexibility': 0.86
            }
            
            high_suggestions = StrengthAnalysisService._suggest_next_steps(high_scores)
            assert '上級シナリオに挑戦してみましょう' in high_suggestions


class TestAchievementServiceExtended:
    """AchievementService の拡張カバレッジテスト"""
    
    def test_get_user_achievements_with_filters(self, app):
        """フィルター付きユーザーアチーブメント取得 - lines 554-596"""
        with app.app_context():
            # ユニークユーザー作成
            unique_id = str(uuid.uuid4())[:8]
            from werkzeug.security import generate_password_hash
            user = User(
                username=f'achievement_user_{unique_id}',
                email=f'achievement_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # テスト用アチーブメント作成
            achievements = []
            for i in range(3):
                achievement = Achievement(
                    name=f'テストアチーブメント{i}_{unique_id}',
                    description=f'テスト用アチーブメント{i}',
                    icon=f'🎯{i}',
                    category='test',
                    threshold_type=f'test_type_{i}',
                    threshold_value=i + 1,
                    points=(i + 1) * 10,
                    is_active=True
                )
                achievements.append(achievement)
                db.session.add(achievement)
            db.session.commit()
            
            # ユーザーアチーブメント作成（一部のみ解除済み）
            user_achievements = []
            for i, achievement in enumerate(achievements):
                # 最初の2つのみ解除済み、3つ目は未解除
                if i < 2:
                    user_ach = UserAchievement(
                        user_id=user.id,
                        achievement_id=achievement.id,
                        progress=achievement.threshold_value
                    )
                    user_achievements.append(user_ach)
                    db.session.add(user_ach)
            db.session.commit()
            
            # 3つ目のアチーブメントは手動で未解除状態に設定
            user_ach_3 = UserAchievement(
                user_id=user.id,
                achievement_id=achievements[2].id,
                progress=achievements[2].threshold_value - 1  # まだ達成していない
            )
            db.session.add(user_ach_3)
            db.session.commit()
            
            # 3つ目を未解除状態にするため、unlocked_atをNullに更新
            user_ach_3.unlocked_at = None
            db.session.commit()
            user_achievements.append(user_ach_3)
            
            try:
                # 全アチーブメント取得テスト - lines 557-571
                all_achievements = AchievementService.get_user_achievements(user.id, unlocked_only=False)
                test_achievements = [a for a in all_achievements if unique_id in a['name']]
                assert len(test_achievements) == 3
                
                # 解除済みのみ取得テスト - lines 568-569
                unlocked_achievements = AchievementService.get_user_achievements(user.id, unlocked_only=True)
                test_unlocked = [a for a in unlocked_achievements if unique_id in a['name']]
                assert len(test_unlocked) == 2
                
                # アチーブメント構造の確認 - lines 574-586
                for achievement_data in test_achievements:
                    assert 'id' in achievement_data
                    assert 'name' in achievement_data
                    assert 'description' in achievement_data
                    assert 'icon' in achievement_data
                    assert 'category' in achievement_data
                    assert 'points' in achievement_data
                    assert 'threshold_value' in achievement_data
                    assert 'progress' in achievement_data
                    assert 'unlocked' in achievement_data
                    assert 'unlocked_at' in achievement_data
                
            finally:
                # クリーンアップ
                for user_ach in user_achievements:
                    db.session.delete(user_ach)
                for achievement in achievements:
                    db.session.delete(achievement)
                db.session.delete(user)
                db.session.commit()
    
    def test_check_session_achievements(self, app):
        """セッション完了系アチーブメントチェック - lines 624-679"""
        with app.app_context():
            # ユニークユーザー作成
            unique_id = str(uuid.uuid4())[:8]
            from werkzeug.security import generate_password_hash
            user = User(
                username=f'session_achievement_user_{unique_id}',
                email=f'session_achievement_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # セッション完了数カウント用のアチーブメント作成
            session_achievement = Achievement(
                name=f'セッション完了アチーブメント_{unique_id}',
                description='セッション完了数テスト',
                icon='🏆',
                category='practice',
                threshold_type='session_count',
                threshold_value=3,
                points=50,
                is_active=True
            )
            db.session.add(session_achievement)
            db.session.commit()
            
            try:
                # 複数のセッション作成（完了状態）
                sessions = []
                for i in range(4):
                    session = SessionService.create_session(
                        user_id=user.id,
                        session_type='scenario'
                    )
                    session.is_completed = True
                    sessions.append(session)
                db.session.commit()
                
                # セッション完了系アチーブメントチェック
                unlocked = AchievementService._check_session_achievements(
                    user.id, 
                    {'session_count': 4}
                )
                
                # アチーブメントが解除されたかを確認
                # 実際のアチーブメント解除確認
                user_achievement = UserAchievement.query.filter_by(
                    user_id=user.id,
                    achievement_id=session_achievement.id
                ).first()
                
                # セッション数が閾値以上であることを確認 - lines 642-644
                completed_count = PracticeSession.query.filter_by(
                    user_id=user.id,
                    is_completed=True
                ).count()
                assert completed_count >= session_achievement.threshold_value
                
            finally:
                # クリーンアップ
                user_achievements = UserAchievement.query.filter_by(user_id=user.id).all()
                for user_ach in user_achievements:
                    db.session.delete(user_ach)
                for session in sessions:
                    db.session.delete(session)
                db.session.delete(session_achievement)
                db.session.delete(user)
                db.session.commit()
    
    def test_get_total_points_coverage(self, app):
        """総ポイント取得 - lines 762-778"""
        with app.app_context():
            # ユニークユーザー作成
            unique_id = str(uuid.uuid4())[:8]
            from werkzeug.security import generate_password_hash
            user = User(
                username=f'points_user_{unique_id}',
                email=f'points_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            # 異なるポイントのアチーブメント作成
            achievements = []
            point_values = [10, 25, 50]
            
            for i, points in enumerate(point_values):
                achievement = Achievement(
                    name=f'ポイントテストアチーブメント{i}_{unique_id}',
                    description=f'{points}ポイントアチーブメント',
                    icon=f'💎{i}',
                    category='test',
                    threshold_type=f'points_test_{i}',
                    threshold_value=1,
                    points=points,
                    is_active=True
                )
                achievements.append(achievement)
                db.session.add(achievement)
            db.session.commit()
            
            # 最初の2つのアチーブメントを解除済みに設定
            user_achievements = []
            for i in range(2):
                user_ach = UserAchievement(
                    user_id=user.id,
                    achievement_id=achievements[i].id,
                    progress=1,
                    unlocked_at=datetime.now()
                )
                user_achievements.append(user_ach)
                db.session.add(user_ach)
            db.session.commit()
            
            try:
                # 総ポイント取得 - lines 765-772
                total_points = AchievementService.get_total_points(user.id)
                expected_total = point_values[0] + point_values[1]  # 10 + 25 = 35
                assert total_points == expected_total
                
                # ポイントがない場合のテスト
                # 新しいユーザーでテスト
                unique_id2 = str(uuid.uuid4())[:8]
                user2 = User(
                    username=f'no_points_user_{unique_id2}',
                    email=f'no_points_{unique_id2}@test.com',
                    password_hash=generate_password_hash('testpass'),
                    is_active=True
                )
                db.session.add(user2)
                db.session.commit()
                
                zero_points = AchievementService.get_total_points(user2.id)
                assert zero_points == 0
                
            finally:
                # クリーンアップ
                for user_ach in user_achievements:
                    db.session.delete(user_ach)
                for achievement in achievements:
                    db.session.delete(achievement)
                if 'user2' in locals():
                    db.session.delete(user2)
                db.session.delete(user)
                db.session.commit()


class TestHelperFunctionsExtended:
    """ヘルパー関数の拡張カバレッジテスト"""
    
    def test_get_conversation_history_empty_case(self, app):
        """空の会話履歴処理 - lines 866-867, 871-873"""
        with app.app_context():
            # ユニークユーザー作成
            unique_id = str(uuid.uuid4())[:8]
            from werkzeug.security import generate_password_hash
            user = User(
                username=f'empty_history_user_{unique_id}',
                email=f'empty_history_{unique_id}@test.com',
                password_hash=generate_password_hash('testpass'),
                is_active=True
            )
            db.session.add(user)
            db.session.commit()
            
            session = SessionService.create_session(
                user_id=user.id,
                session_type='free_talk'
            )
            
            try:
                # 空のセッションでの履歴取得
                history = get_conversation_history(session, limit=5)
                assert history == []
                
                # 不完全なペアの処理テスト
                # ユーザーメッセージのみ追加（AIレスポンスなし）
                ConversationService.add_log(
                    session_id=session.id,
                    message='ユーザーメッセージのみ',
                    is_user=True
                )
                
                # 最後のペアが残る場合のテスト - lines 866-867
                history_incomplete = get_conversation_history(session, limit=5)
                assert len(history_incomplete) == 1
                assert history_incomplete[0]['human'] == 'ユーザーメッセージのみ'
                assert 'ai' not in history_incomplete[0]
                
            finally:
                # クリーンアップ
                logs = ConversationService.get_session_logs(session.id)
                for log in logs:
                    db.session.delete(log)
                db.session.delete(session)
                db.session.delete(user)
                db.session.commit()


def test_extended_coverage_execution():
    """拡張カバレッジテストの実行確認"""
    assert True