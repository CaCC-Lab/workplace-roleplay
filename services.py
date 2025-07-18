"""
サービスレイヤー

ビジネスロジックとデータベース操作を集約し、
app.pyから循環インポートを排除するためのレイヤー
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from models import db, Scenario, PracticeSession, ConversationLog, User, SessionType
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
            return PracticeSession.query.filter_by(user_id=user_id)\
                                       .order_by(PracticeSession.created_at.desc())\
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
        ).order_by(PracticeSession.created_at.desc()).first()
        
        # 最新セッションが1時間以内なら再利用
        if existing_session:
            from datetime import datetime, timedelta
            if existing_session.created_at > datetime.utcnow() - timedelta(hours=1):
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