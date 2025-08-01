"""
セッション管理サービス
会話履歴やセッションデータの管理を担当
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import session


class SessionService:
    """セッション管理のためのサービスクラス"""
    
    @staticmethod
    def initialize_session_history(session_key: str, sub_key: Optional[str] = None) -> None:
        """
        セッション内に新しい履歴リストを初期化する
        
        Args:
            session_key: セッションキー（'chat_history', 'scenario_history'など）
            sub_key: サブキー（シナリオIDなど）
        """
        if session_key not in session:
            session[session_key] = {}
        
        if sub_key:
            if sub_key not in session[session_key]:
                session[session_key][sub_key] = []
        else:
            if not isinstance(session.get(session_key), list):
                session[session_key] = []
    
    @staticmethod
    def add_to_session_history(session_key: str, entry: Dict[str, Any], 
                             sub_key: Optional[str] = None, max_entries: int = 50) -> None:
        """
        セッション履歴にエントリを追加
        
        Args:
            session_key: セッションキー
            entry: 追加するエントリ
            sub_key: サブキー（オプション）
            max_entries: 最大保持エントリ数
        """
        # 履歴の初期化を確認
        SessionService.initialize_session_history(session_key, sub_key)
        
        if sub_key:
            history = session[session_key][sub_key]
        else:
            history = session[session_key]
        
        # エントリを追加
        history.append(entry)
        
        # 最大エントリ数を超えた場合は古いものを削除
        if len(history) > max_entries:
            history[:] = history[-max_entries:]
        
        # セッションの変更を確定
        session.modified = True
    
    @staticmethod
    def get_session_history(session_key: str, sub_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        セッション履歴を取得
        
        Args:
            session_key: セッションキー
            sub_key: サブキー（オプション）
            
        Returns:
            履歴のリスト
        """
        if session_key not in session:
            return []
        
        if sub_key:
            return session.get(session_key, {}).get(sub_key, [])
        
        history = session.get(session_key, [])
        return history if isinstance(history, list) else []
    
    @staticmethod
    def clear_session_history(session_key: str, sub_key: Optional[str] = None) -> None:
        """
        セッション履歴をクリア
        
        Args:
            session_key: セッションキー
            sub_key: サブキー（オプション）
        """
        if session_key in session:
            if sub_key and isinstance(session.get(session_key), dict):
                if sub_key in session[session_key]:
                    session[session_key][sub_key] = []
            else:
                session[session_key] = {} if sub_key else []
            session.modified = True
    
    @staticmethod
    def set_session_start_time(session_key: str, sub_key: Optional[str] = None) -> None:
        """
        セッション開始時刻を設定
        
        Args:
            session_key: セッションキー
            sub_key: サブキー（オプション）
        """
        start_time_key = f"{session_key}_start_time"
        current_time = datetime.now().isoformat()
        
        if sub_key:
            if start_time_key not in session:
                session[start_time_key] = {}
            session[start_time_key][sub_key] = current_time
        else:
            session[start_time_key] = current_time
        
        session.modified = True
    
    @staticmethod
    def get_session_start_time(session_key: str, sub_key: Optional[str] = None) -> Optional[str]:
        """
        セッション開始時刻を取得
        
        Args:
            session_key: セッションキー
            sub_key: サブキー（オプション）
            
        Returns:
            開始時刻のISO形式文字列
        """
        start_time_key = f"{session_key}_start_time"
        
        if sub_key:
            return session.get(start_time_key, {}).get(sub_key)
        
        return session.get(start_time_key)
    
    @staticmethod
    def get_session_data(key: str, default: Any = None) -> Any:
        """
        セッションから任意のデータを取得
        
        Args:
            key: データのキー
            default: デフォルト値
            
        Returns:
            セッションデータまたはデフォルト値
        """
        return session.get(key, default)
    
    @staticmethod
    def set_session_data(key: str, value: Any) -> None:
        """
        セッションに任意のデータを設定
        
        Args:
            key: データのキー
            value: 設定する値
        """
        session[key] = value
        session.modified = True
    
    @staticmethod
    def remove_session_data(key: str) -> None:
        """
        セッションからデータを削除
        
        Args:
            key: 削除するデータのキー
        """
        if key in session:
            del session[key]
            session.modified = True