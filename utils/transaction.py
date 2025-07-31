"""
トランザクション管理ユーティリティ

データベーストランザクションを管理するための
コンテキストマネージャーを提供します。
"""
from contextlib import contextmanager
import logging
from models import db

logger = logging.getLogger(__name__)


@contextmanager
def managed_session():
    """
    データベースセッションのトランザクションを管理するコンテキストマネージャ。
    
    ブロックを正常に終了した際に自動的にコミットし、
    例外が発生した際に自動的にロールバックします。
    
    使用例:
        with managed_session():
            user = UserService.create_user("test", "test@example.com", "hash")
            # 他のデータベース操作...
        # ここで自動的にコミットされる
    
    例外が発生した場合:
        try:
            with managed_session():
                # データベース操作...
                raise SomeError()
        except SomeError:
            # ここに到達する前に自動的にロールバックされる
    """
    try:
        yield db.session
        db.session.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        logger.warning(f"Transaction failed. Rolling back session. Reason: {e}")
        db.session.rollback()
        raise


@contextmanager
def read_only_session():
    """
    読み取り専用のセッション管理。
    
    読み取り専用の操作で使用することで、
    誤って書き込み操作が含まれていても安全に処理できます。
    """
    try:
        yield db.session
        # 読み取り専用なのでコミットはしない
    finally:
        # セッションのクリーンアップ
        db.session.rollback()