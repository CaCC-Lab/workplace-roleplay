"""
サービスレイヤー

ビジネスロジックとデータベース操作を集約し、
app.pyから循環インポートを排除するためのレイヤー
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from models import db, Scenario, PracticeSession, ConversationLog, User, SessionType, StrengthAnalysis, Achievement, UserAchievement
from errors import NotFoundError, AppError, ValidationError
from database import sync_scenarios_from_yaml

logger = logging.getLogger(__name__)


class ScenarioService:
    """シナリオ関連のビジネスロジック"""
    
    @staticmethod
    def get_by_id(scenario_id: int) -> Scenario:
        """IDでシナリオを1件取得"""
        try:
            scenario = Scenario.query.get(scenario_id)
            if not scenario:
                raise NotFoundError("シナリオ", str(scenario_id))
            return scenario
        except SQLAlchemyError as e:
            logger.error(f"シナリオ取得エラー (ID: {scenario_id}): {e}")
            raise AppError(
                message="シナリオの取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def get_by_yaml_id(yaml_id: str) -> Optional[Scenario]:
        """YAML IDでシナリオを取得"""
        try:
            return Scenario.query.filter_by(yaml_id=yaml_id).first()
        except SQLAlchemyError as e:
            logger.error(f"シナリオ取得エラー (YAML ID: {yaml_id}): {e}")
            raise AppError(
                message="シナリオの取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def get_all(is_active: bool = True) -> List[Scenario]:
        """全シナリオ取得"""
        try:
            query = Scenario.query
            if is_active:
                query = query.filter_by(is_active=True)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"シナリオ一覧取得エラー: {e}")
            raise AppError(
                message="シナリオ一覧の取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def sync_from_yaml():
        """YAMLファイルからシナリオを同期"""
        try:
            sync_scenarios_from_yaml()
        except Exception as e:
            logger.error(f"シナリオ同期エラー: {e}")
            raise AppError(
                message="シナリオの同期中にエラーが発生しました",
                code="SYNC_ERROR",
                status_code=500
            ) from e


class SessionService:
    """練習セッション関連のビジネスロジック"""
    
    @staticmethod
    def create_session(
        user_id: Optional[int],
        session_type: str,
        scenario_id: Optional[int] = None,
        ai_model: Optional[str] = None
    ) -> PracticeSession:
        """新しい練習セッションを作成"""
        try:
            # セッションタイプの検証
            try:
                session_type_enum = SessionType(session_type)
            except ValueError as e:
                raise ValidationError(f"無効なセッションタイプです: {session_type}") from e
            
            # シナリオIDの検証（指定された場合）
            if scenario_id:
                scenario = ScenarioService.get_by_id(scenario_id)
                if not scenario:
                    raise NotFoundError("シナリオ", str(scenario_id))
            
            session = PracticeSession(
                user_id=user_id,
                session_type=session_type_enum,
                scenario_id=scenario_id,
                ai_model=ai_model
            )
            
            db.session.add(session)
            db.session.commit()
            
            logger.info(f"練習セッション作成完了: {session.id}")
            return session
            
        except AppError:
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"練習セッション作成エラー: {e}")
            raise AppError(
                message="練習セッションの作成中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def get_session_by_id(session_id: int) -> PracticeSession:
        """IDで練習セッションを取得"""
        try:
            session = PracticeSession.query.get(session_id)
            if not session:
                raise NotFoundError("練習セッション", str(session_id))
            return session
        except SQLAlchemyError as e:
            logger.error(f"練習セッション取得エラー (ID: {session_id}): {e}")
            raise AppError(
                message="練習セッションの取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def get_user_sessions(user_id: int, limit: int = 10) -> List[PracticeSession]:
        """ユーザーの練習セッション履歴を取得"""
        try:
            # N+1問題を回避するため、関連するscenarioを事前にロード
            return PracticeSession.query.filter_by(user_id=user_id)\
                                       .options(joinedload(PracticeSession.scenario))\
                                       .order_by(PracticeSession.started_at.desc())\
                                       .limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"ユーザーセッション取得エラー (User ID: {user_id}): {e}")
            raise AppError(
                message="ユーザーセッション履歴の取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e


class ConversationService:
    """会話ログ関連のビジネスロジック"""
    
    @staticmethod
    def add_log(
        session_id: int,
        message: str,
        is_user: bool,
        response_time: Optional[float] = None,
        token_count: Optional[int] = None
    ) -> ConversationLog:
        """会話ログを追加"""
        try:
            # セッションの存在確認（存在しない場合は例外が発生）
            SessionService.get_session_by_id(session_id)
            
            log = ConversationLog(
                session_id=session_id,
                speaker='user' if is_user else 'ai',
                message=message,
                message_type='text'
            )
            
            db.session.add(log)
            db.session.commit()
            
            return log
            
        except AppError:
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"会話ログ追加エラー: {e}")
            raise AppError(
                message="会話ログの保存中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def get_session_logs(session_id: int, limit: Optional[int] = None) -> List[ConversationLog]:
        """セッションの会話ログを取得"""
        try:
            query = ConversationLog.query.filter_by(session_id=session_id)\
                                        .order_by(ConversationLog.timestamp)
            if limit:
                query = query.limit(limit)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"会話ログ取得エラー (Session ID: {session_id}): {e}")
            raise AppError(
                message="会話ログの取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e


class UserService:
    """ユーザー関連のビジネスロジック"""
    
    @staticmethod
    def get_by_id(user_id: int) -> User:
        """IDでユーザーを取得"""
        try:
            user = User.query.get(user_id)
            if not user:
                raise NotFoundError("ユーザー", str(user_id))
            return user
        except SQLAlchemyError as e:
            logger.error(f"ユーザー取得エラー (ID: {user_id}): {e}")
            raise AppError(
                message="ユーザーの取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def create_user(username: str, email: str, password_hash: str) -> User:
        """新規ユーザーを作成"""
        try:
            # 重複チェック
            existing_user = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    raise ValidationError("このユーザー名は既に使用されています", field="username")
                else:
                    raise ValidationError("このメールアドレスは既に使用されています", field="email")
            
            user = User(
                username=username,
                email=email,
                password_hash=password_hash
            )
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"ユーザー作成完了: {user.username}")
            return user
            
        except AppError:
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"ユーザー作成エラー: {e}")
            raise AppError(
                message="ユーザーの作成中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e


class StrengthAnalysisService:
    """強み分析・成長記録関連のビジネスロジック"""
    
    @staticmethod
    def save_analysis(
        session_id: int,
        analysis_result: Dict[str, float],
        feedback_text: Optional[str] = None
    ) -> StrengthAnalysis:
        """強み分析結果を保存"""
        try:
            # セッションの存在確認
            session = SessionService.get_session_by_id(session_id)
            
            # 既存の分析結果があれば更新、なければ新規作成
            analysis = StrengthAnalysis.query.filter_by(session_id=session_id).first()
            
            if not analysis:
                analysis = StrengthAnalysis(session_id=session_id)
            
            # スコアを更新
            analysis.empathy = analysis_result.get('empathy', 0.0)
            analysis.clarity = analysis_result.get('clarity', 0.0)
            analysis.listening = analysis_result.get('listening', 0.0)
            analysis.problem_solving = analysis_result.get('problem_solving', 0.0)
            analysis.assertiveness = analysis_result.get('assertiveness', 0.0)
            analysis.flexibility = analysis_result.get('flexibility', 0.0)
            
            # フィードバックと改善提案
            analysis.feedback_text = feedback_text
            analysis.overall_score = sum([
                analysis.empathy, analysis.clarity, analysis.listening,
                analysis.problem_solving, analysis.assertiveness, analysis.flexibility
            ]) / 6.0
            
            # 改善提案をJSON形式で保存
            analysis.improvement_suggestions = {
                'strengths': StrengthAnalysisService._identify_strengths(analysis_result),
                'areas_for_improvement': StrengthAnalysisService._identify_improvements(analysis_result),
                'next_steps': StrengthAnalysisService._suggest_next_steps(analysis_result)
            }
            
            # バリデーション実行
            try:
                analysis.validate_skill_scores()
            except ValueError as e:
                logger.error(f"スキルスコアのバリデーションエラー: {e}")
                raise ValidationError(str(e))
            
            db.session.add(analysis)
            db.session.commit()
            
            # アチーブメントチェック（バックグラウンドタスクとして実行可能）
            if session.user_id:
                StrengthAnalysisService._check_achievements(session.user_id, analysis)
            
            logger.info(f"強み分析保存完了: Session {session_id}")
            return analysis
            
        except AppError:
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"強み分析保存エラー: {e}")
            raise AppError(
                message="強み分析の保存中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def get_user_analyses(user_id: int, limit: int = 10) -> List[StrengthAnalysis]:
        """ユーザーの強み分析履歴を取得"""
        try:
            return db.session.query(StrengthAnalysis)\
                .join(PracticeSession)\
                .filter(PracticeSession.user_id == user_id)\
                .order_by(StrengthAnalysis.created_at.desc())\
                .limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"強み分析履歴取得エラー (User ID: {user_id}): {e}")
            raise AppError(
                message="強み分析履歴の取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def get_skill_progress(user_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """ユーザーのスキル別進捗を取得"""
        try:
            analyses = StrengthAnalysisService.get_user_analyses(user_id, limit=30)
            
            # スキル別の時系列データを構築
            skills = ['empathy', 'clarity', 'listening', 'problem_solving', 'assertiveness', 'flexibility']
            progress = {skill: [] for skill in skills}
            
            for analysis in reversed(analyses):  # 古い順に並び替え
                for skill in skills:
                    progress[skill].append({
                        'date': analysis.created_at.isoformat(),
                        'score': getattr(analysis, skill),
                        'session_id': analysis.session_id
                    })
            
            return progress
            
        except AppError:
            raise
        except Exception as e:
            logger.error(f"スキル進捗取得エラー: {e}")
            raise AppError(
                message="スキル進捗の取得中にエラーが発生しました",
                code="PROGRESS_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def get_average_scores(user_id: int) -> Dict[str, float]:
        """ユーザーのスキル別平均スコアを取得"""
        try:
            from sqlalchemy import func
            
            # 最新10件の分析結果から平均を計算
            subquery = db.session.query(StrengthAnalysis)\
                .join(PracticeSession)\
                .filter(PracticeSession.user_id == user_id)\
                .order_by(StrengthAnalysis.created_at.desc())\
                .limit(10).subquery()
            
            averages = db.session.query(
                func.avg(subquery.c.empathy).label('empathy'),
                func.avg(subquery.c.clarity).label('clarity'),
                func.avg(subquery.c.listening).label('listening'),
                func.avg(subquery.c.problem_solving).label('problem_solving'),
                func.avg(subquery.c.assertiveness).label('assertiveness'),
                func.avg(subquery.c.flexibility).label('flexibility'),
                func.avg(subquery.c.overall_score).label('overall')
            ).first()
            
            return {
                'empathy': float(averages.empathy or 0),
                'clarity': float(averages.clarity or 0),
                'listening': float(averages.listening or 0),
                'problem_solving': float(averages.problem_solving or 0),
                'assertiveness': float(averages.assertiveness or 0),
                'flexibility': float(averages.flexibility or 0),
                'overall': float(averages.overall or 0)
            }
            
        except SQLAlchemyError as e:
            logger.error(f"平均スコア取得エラー: {e}")
            raise AppError(
                message="平均スコアの取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def _identify_strengths(scores: Dict[str, float]) -> List[str]:
        """高スコアのスキルを特定"""
        strengths = []
        skill_names = {
            'empathy': '共感力',
            'clarity': '明確な伝達',
            'listening': '傾聴力',
            'problem_solving': '問題解決力',
            'assertiveness': '自己主張',
            'flexibility': '柔軟性'
        }
        
        for skill, score in scores.items():
            if skill in skill_names and score >= 0.8:
                strengths.append(skill_names[skill])
        
        return strengths
    
    @staticmethod
    def _identify_improvements(scores: Dict[str, float]) -> List[str]:
        """改善が必要なスキルを特定"""
        improvements = []
        skill_names = {
            'empathy': '共感力',
            'clarity': '明確な伝達',
            'listening': '傾聴力',
            'problem_solving': '問題解決力',
            'assertiveness': '自己主張',
            'flexibility': '柔軟性'
        }
        
        for skill, score in scores.items():
            if skill in skill_names and score < 0.6:
                improvements.append(skill_names[skill])
        
        return improvements
    
    @staticmethod
    def _suggest_next_steps(scores: Dict[str, float]) -> List[str]:
        """次のステップの提案"""
        suggestions = []
        
        # 最も低いスキルを特定
        min_skill = min(scores, key=scores.get)
        
        suggestions_map = {
            'empathy': '相手の気持ちを想像する練習をしましょう',
            'clarity': '要点を整理してから話す練習をしましょう',
            'listening': '相手の話を最後まで聞く練習をしましょう',
            'problem_solving': '問題を段階的に分析する練習をしましょう',
            'assertiveness': '自分の意見を明確に伝える練習をしましょう',
            'flexibility': '異なる視点を受け入れる練習をしましょう'
        }
        
        if min_skill in suggestions_map:
            suggestions.append(suggestions_map[min_skill])
        
        # 全体的なスコアが高い場合は上級シナリオを推奨
        overall_avg = sum(scores.values()) / len(scores)
        if overall_avg >= 0.8:
            suggestions.append('上級シナリオに挑戦してみましょう')
        
        return suggestions
    
    @staticmethod
    def _check_achievements(user_id: int, analysis: StrengthAnalysis):
        """分析結果に基づいてアチーブメントをチェック（N+1最適化版）"""
        try:
            # スキル系アチーブメントのスコアを定義
            skill_achievements = {
                'skill_empathy': analysis.empathy,
                'skill_clarity': analysis.clarity,
                'skill_listening': analysis.listening
            }
            
            # 80%以上のスキルのみ対象
            high_skill_types = [skill_type for skill_type, score in skill_achievements.items() if score >= 0.8]
            
            if not high_skill_types:
                return  # 対象スキルがない場合は早期リターン
            
            # 必要なアチーブメントを一括取得
            achievements = Achievement.query.filter(
                Achievement.threshold_type.in_(high_skill_types),
                Achievement.is_active == True
            ).all()
            
            if not achievements:
                return  # アチーブメントがない場合は早期リターン
            
            # アチーブメントIDのリスト作成
            achievement_ids = [a.id for a in achievements]
            
            # ユーザーの既存アチーブメントを一括取得
            existing_user_achievements = UserAchievement.query.filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id.in_(achievement_ids)
            ).all()
            
            # 既存アチーブメントをIDでマッピング
            existing_map = {ua.achievement_id: ua for ua in existing_user_achievements}
            
            # 新規追加用のリスト
            new_achievements = []
            
            # アチーブメントごとにチェック
            for achievement in achievements:
                score = skill_achievements.get(achievement.threshold_type, 0)
                
                if achievement.id in existing_map:
                    # 既存のアチーブメント進捗を更新
                    user_achievement = existing_map[achievement.id]
                    user_achievement.progress += 1
                    
                    # 閾値に達したら解除
                    if user_achievement.progress >= achievement.threshold_value and not user_achievement.unlocked_at:
                        user_achievement.unlocked_at = db.func.now()
                        logger.info(f"アチーブメント解除: User {user_id}, Achievement {achievement.name}")
                else:
                    # 新規アチーブメントとして追加
                    user_achievement = UserAchievement(
                        user_id=user_id,
                        achievement_id=achievement.id,
                        progress=1  # 初回は1
                    )
                    
                    # 閾値が1の場合は即座に解除
                    if achievement.threshold_value <= 1:
                        user_achievement.unlocked_at = db.func.now()
                        logger.info(f"アチーブメント解除: User {user_id}, Achievement {achievement.name}")
                    
                    new_achievements.append(user_achievement)
            
            # 新規アチーブメントを一括追加
            if new_achievements:
                db.session.add_all(new_achievements)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"アチーブメントチェックエラー: {e}")
            db.session.rollback()
            # アチーブメントチェックの失敗は分析保存を妨げない


class AchievementService:
    """アチーブメント関連のビジネスロジック"""
    
    @staticmethod
    def get_user_achievements(user_id: int, unlocked_only: bool = False) -> List[Dict[str, Any]]:
        """ユーザーのアチーブメント情報を取得"""
        try:
            query = db.session.query(
                Achievement,
                UserAchievement
            ).outerjoin(
                UserAchievement,
                db.and_(
                    Achievement.id == UserAchievement.achievement_id,
                    UserAchievement.user_id == user_id
                )
            ).filter(Achievement.is_active == True)
            
            if unlocked_only:
                query = query.filter(UserAchievement.unlocked_at.isnot(None))
            
            results = query.all()
            
            achievements = []
            for achievement, user_achievement in results:
                achievements.append({
                    'id': achievement.id,
                    'name': achievement.name,
                    'description': achievement.description,
                    'icon': achievement.icon,
                    'category': achievement.category,
                    'points': achievement.points,
                    'threshold_value': achievement.threshold_value,
                    'progress': user_achievement.progress if user_achievement else 0,
                    'unlocked': bool(user_achievement and user_achievement.unlocked_at),
                    'unlocked_at': user_achievement.unlocked_at.isoformat() if user_achievement and user_achievement.unlocked_at else None
                })
            
            return achievements
            
        except SQLAlchemyError as e:
            logger.error(f"アチーブメント取得エラー: {e}")
            raise AppError(
                message="アチーブメントの取得中にデータベースエラーが発生しました",
                code="DATABASE_ERROR",
                status_code=500
            ) from e
    
    @staticmethod
    def check_and_unlock_achievements(user_id: int, event_type: str, event_data: Dict[str, Any]) -> List[Achievement]:
        """イベントに基づいてアチーブメントをチェックし、解除する"""
        try:
            unlocked_achievements = []
            
            # イベントタイプに応じてチェック
            if event_type == 'session_completed':
                unlocked = AchievementService._check_session_achievements(user_id, event_data)
                unlocked_achievements.extend(unlocked)
            
            elif event_type == 'scenario_completed':
                unlocked = AchievementService._check_scenario_achievements(user_id, event_data)
                unlocked_achievements.extend(unlocked)
            
            elif event_type == 'skill_improved':
                # StrengthAnalysisServiceから呼ばれる場合は既にチェック済み
                pass
            
            return unlocked_achievements
            
        except Exception as e:
            logger.error(f"アチーブメントチェックエラー: {e}")
            return []
    
    @staticmethod
    def _check_session_achievements(user_id: int, event_data: Dict[str, Any]) -> List[Achievement]:
        """セッション完了系のアチーブメントをチェック（N+1最適化版）"""
        unlocked = []
        
        try:
            from datetime import datetime
            
            # セッション数カウント
            session_count = PracticeSession.query.filter_by(
                user_id=user_id,
                is_completed=True
            ).count()
            
            # チェック対象のアチーブメントタイプを定義
            threshold_types = ['session_count']
            
            # 時間帯別アチーブメントの条件チェック
            current_hour = datetime.now().hour
            if 6 <= current_hour < 9:
                threshold_types.append('morning_practice')
            elif current_hour >= 22:
                threshold_types.append('night_practice')
            
            # 週末チェック
            if datetime.now().weekday() >= 5:  # 土日
                threshold_types.append('weekend_practice')
            
            # 関連する全アチーブメントを一括取得
            achievements = Achievement.query.filter(
                Achievement.threshold_type.in_(threshold_types),
                Achievement.is_active == True
            ).all()
            
            if not achievements:
                return unlocked
            
            # アチーブメントIDのリスト作成
            achievement_ids = [a.id for a in achievements]
            
            # 既存のユーザーアチーブメントを一括取得
            existing_achievements = db.session.query(UserAchievement.achievement_id).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id.in_(achievement_ids),
                UserAchievement.unlocked_at.isnot(None)
            ).all()
            
            # 既に解除済みのIDのセット作成
            unlocked_ids = {ua[0] for ua in existing_achievements}
            
            # 新規解除用のリスト
            new_unlocks = []
            
            # 各アチーブメントをチェック
            for achievement in achievements:
                # 既に解除済みならスキップ
                if achievement.id in unlocked_ids:
                    continue
                
                # 条件チェック
                should_unlock = False
                
                if achievement.threshold_type == 'session_count' and session_count >= achievement.threshold_value:
                    should_unlock = True
                elif achievement.threshold_type in ['morning_practice', 'night_practice', 'weekend_practice']:
                    # 時間帯・曜日系はタイプが存在することで条件満たしている
                    should_unlock = True
                
                if should_unlock:
                    new_unlocks.append({
                        'user_id': user_id,
                        'achievement_id': achievement.id,
                        'progress': session_count if achievement.threshold_type == 'session_count' else 1,
                        'unlocked_at': datetime.now()
                    })
                    unlocked.append(achievement)
            
            # 新規アチーブメントを一括挿入
            if new_unlocks:
                db.session.bulk_insert_mappings(UserAchievement, new_unlocks)
                db.session.commit()
                
                for achievement in unlocked:
                    logger.info(f"アチーブメント解除: User {user_id}, Achievement {achievement.name}")
            
            return unlocked
            
        except Exception as e:
            logger.error(f"セッションアチーブメントチェックエラー: {e}")
            db.session.rollback()
            return unlocked
    
    @staticmethod
    def _check_scenario_achievements(user_id: int, event_data: Dict[str, Any]) -> List[Achievement]:
        """シナリオ完了系のアチーブメントをチェック（N+1最適化版）"""
        unlocked = []
        
        try:
            from datetime import datetime
            
            # シナリオ完了数カウント
            completed_scenarios = db.session.query(
                db.func.count(db.distinct(PracticeSession.scenario_id))
            ).filter(
                PracticeSession.user_id == user_id,
                PracticeSession.is_completed == True,
                PracticeSession.scenario_id.isnot(None)
            ).scalar()
            
            # シナリオ完了系アチーブメントを一括取得
            scenario_achievements = Achievement.query.filter(
                Achievement.threshold_type.in_(['scenario_complete', 'unique_scenarios', 'all_scenarios']),
                Achievement.is_active == True
            ).all()
            
            if not scenario_achievements:
                return unlocked
            
            # all_scenariosタイプがある場合のみ総シナリオ数を取得
            total_scenarios = None
            if any(a.threshold_type == 'all_scenarios' for a in scenario_achievements):
                total_scenarios = Scenario.query.filter_by(is_active=True).count()
            
            # アチーブメントIDのリスト作成
            achievement_ids = [a.id for a in scenario_achievements]
            
            # 既存のユーザーアチーブメントを一括取得
            existing_achievements = db.session.query(UserAchievement.achievement_id).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id.in_(achievement_ids),
                UserAchievement.unlocked_at.isnot(None)
            ).all()
            
            # 既に解除済みのIDのセット作成
            unlocked_ids = {ua[0] for ua in existing_achievements}
            
            # 新規解除用のリスト
            new_unlocks = []
            
            # 各アチーブメントをチェック
            for achievement in scenario_achievements:
                # 既に解除済みならスキップ
                if achievement.id in unlocked_ids:
                    continue
                
                # 条件チェック
                should_unlock = False
                
                if achievement.threshold_type == 'scenario_complete' and completed_scenarios >= 1:
                    should_unlock = True
                elif achievement.threshold_type == 'unique_scenarios' and completed_scenarios >= achievement.threshold_value:
                    should_unlock = True
                elif achievement.threshold_type == 'all_scenarios' and total_scenarios and completed_scenarios >= total_scenarios:
                    should_unlock = True
                
                if should_unlock:
                    new_unlocks.append({
                        'user_id': user_id,
                        'achievement_id': achievement.id,
                        'progress': completed_scenarios,
                        'unlocked_at': datetime.now()
                    })
                    unlocked.append(achievement)
            
            # 新規アチーブメントを一括挿入
            if new_unlocks:
                db.session.bulk_insert_mappings(UserAchievement, new_unlocks)
                db.session.commit()
                
                for achievement in unlocked:
                    logger.info(f"アチーブメント解除: User {user_id}, Achievement {achievement.name}")
            
            return unlocked
            
        except Exception as e:
            logger.error(f"シナリオアチーブメントチェックエラー: {e}")
            db.session.rollback()
            return unlocked
    
    @staticmethod
    def _unlock_achievement(user_id: int, achievement_id: int) -> bool:
        """アチーブメントを解除（既に解除済みの場合はFalse）"""
        try:
            user_achievement = UserAchievement.query.filter_by(
                user_id=user_id,
                achievement_id=achievement_id
            ).first()
            
            if not user_achievement:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement_id,
                    progress=1,
                    unlocked_at=db.func.now()
                )
                db.session.add(user_achievement)
                db.session.commit()
                
                achievement = Achievement.query.get(achievement_id)
                logger.info(f"アチーブメント解除: User {user_id}, Achievement {achievement.name}")
                return True
            
            elif not user_achievement.unlocked_at:
                user_achievement.unlocked_at = db.func.now()
                db.session.commit()
                
                achievement = Achievement.query.get(achievement_id)
                logger.info(f"アチーブメント解除: User {user_id}, Achievement {achievement.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"アチーブメント解除エラー: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_total_points(user_id: int) -> int:
        """ユーザーの獲得ポイント合計を取得"""
        try:
            total = db.session.query(
                db.func.sum(Achievement.points)
            ).join(
                UserAchievement
            ).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.unlocked_at.isnot(None)
            ).scalar()
            
            return int(total or 0)
            
        except SQLAlchemyError as e:
            logger.error(f"ポイント合計取得エラー: {e}")
            return 0


# ヘルパー関数（従来のdatabase.pyから移行）
def get_or_create_practice_session(user_id: Optional[int], scenario_id: Optional[str], session_type: str) -> Optional[PracticeSession]:
    """練習セッションを取得または作成（ハイブリッド対応）"""
    if not user_id:
        return None
    
    try:
        # 既存のセッションを検索
        existing_session = PracticeSession.query.filter_by(
            user_id=user_id,
            scenario_id=scenario_id,
            session_type=SessionType(session_type)
        ).order_by(PracticeSession.started_at.desc()).first()
        
        # 最新セッションが1時間以内なら再利用
        if existing_session:
            from datetime import datetime, timedelta, timezone
            now_utc = datetime.now(timezone.utc)
            
            # started_atがtimezone-naiveの場合はUTCとして扱う
            started_at = existing_session.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            
            if started_at > now_utc - timedelta(hours=1):
                return existing_session
        
        # 新しいセッションを作成
        return SessionService.create_session(
            user_id=user_id,
            session_type=session_type,
            scenario_id=scenario_id
        )
        
    except Exception as e:
        logger.error(f"練習セッション取得/作成エラー: {e}")
        return None


def add_conversation_log(session: Optional[PracticeSession], user_message: str, ai_response: str) -> bool:
    """会話ログをデータベースに追加（ハイブリッド対応）"""
    if not session:
        return False
    
    try:
        # ユーザーメッセージを記録
        ConversationService.add_log(
            session_id=session.id,
            message=user_message,
            is_user=True
        )
        
        # AIレスポンスを記録
        ConversationService.add_log(
            session_id=session.id,
            message=ai_response,
            is_user=False
        )
        
        return True
        
    except Exception as e:
        logger.error(f"会話ログ追加エラー: {e}")
        return False


def get_conversation_history(session: Optional[PracticeSession], limit: int = 10) -> List[Dict[str, Any]]:
    """会話履歴を取得（ハイブリッド対応）"""
    if not session:
        return []
    
    try:
        logs = ConversationService.get_session_logs(session.id, limit=limit * 2)  # ユーザー+AI分
        
        # セッション形式に変換（app.pyと同じ形式）
        history = []
        current_pair = {}
        
        for log in logs:
            if log.speaker == 'user':
                if current_pair:  # 前のペアがある場合は追加
                    history.append(current_pair)
                    current_pair = {}
                current_pair['human'] = log.message
            elif log.speaker == 'ai':
                current_pair['ai'] = log.message
                if current_pair:  # AIの応答があれば追加
                    history.append(current_pair)
                    current_pair = {}
        
        # 最後のペアが残っている場合
        if current_pair:
            history.append(current_pair)
        
        return history
        
    except Exception as e:
        logger.error(f"会話履歴取得エラー: {e}")
        return []