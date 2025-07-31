"""
セッション管理サービス
"""
from flask import session
from typing import Optional, Dict, List, Any
from datetime import datetime


class SessionService:
    """セッション関連の操作を管理するサービスクラス"""
    
    def initialize_history(self, session_key: str, sub_key: Optional[str] = None) -> None:
        """セッション履歴を初期化"""
        if sub_key:
            # サブキーがある場合（例：シナリオ履歴）
            if session_key not in session:
                session[session_key] = {}
            if sub_key not in session[session_key]:
                session[session_key][sub_key] = []
        else:
            # 単純なリストの場合（例：チャット履歴）
            if session_key not in session:
                session[session_key] = []
    
    def add_to_history(
        self, 
        session_key: str, 
        entry: Dict[str, Any], 
        sub_key: Optional[str] = None
    ) -> None:
        """セッション履歴にエントリを追加"""
        self.initialize_history(session_key, sub_key)
        
        if sub_key:
            session[session_key][sub_key].append(entry)
        else:
            session[session_key].append(entry)
        
        # セッションの変更を明示的にマーク
        session.modified = True
    
    def clear_history(self, session_key: str, sub_key: Optional[str] = None) -> None:
        """セッション履歴をクリア"""
        if sub_key:
            if session_key in session and sub_key in session[session_key]:
                session[session_key][sub_key] = []
        else:
            if session_key in session:
                session[session_key] = []
        
        # セッションの変更を明示的にマーク
        session.modified = True
    
    def get_history(
        self, 
        session_key: str, 
        sub_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """セッション履歴を取得"""
        if sub_key:
            if session_key in session and sub_key in session[session_key]:
                return session[session_key][sub_key]
            return []
        else:
            return session.get(session_key, [])
    
    def set_start_time(self, session_key: str, sub_key: Optional[str] = None) -> None:
        """開始時刻を記録"""
        start_time_key = f"{session_key}_start_time"
        if sub_key:
            start_time_key = f"{session_key}_{sub_key}_start_time"
        
        session[start_time_key] = datetime.now().isoformat()
        session.modified = True
    
    def get_start_time(self, session_key: str, sub_key: Optional[str] = None) -> Optional[str]:
        """開始時刻を取得"""
        start_time_key = f"{session_key}_start_time"
        if sub_key:
            start_time_key = f"{session_key}_{sub_key}_start_time"
        
        return session.get(start_time_key)
    
    def update_session_data(self, key: str, value: Any) -> None:
        """セッションデータを更新"""
        session[key] = value
        session.modified = True
    
    def get_session_data(self, key: str, default: Any = None) -> Any:
        """セッションデータを取得"""
        return session.get(key, default)
    
    def remove_session_data(self, key: str) -> None:
        """セッションデータを削除"""
        if key in session:
            session.pop(key)
            session.modified = True
    
    def get_session_summary(self) -> Dict[str, Any]:
        """セッションのサマリー情報を取得"""
        summary = {
            "session_id": session.get("session_id", "unknown"),
            "user_id": session.get("user_id"),
            "created_at": session.get("created_at", datetime.now().isoformat()),
            "data_keys": list(session.keys()),
            "history_counts": {}
        }
        
        # 各履歴のカウントを追加
        if "chat_history" in session:
            summary["history_counts"]["chat"] = len(session["chat_history"])
        
        if "scenario_histories" in session:
            summary["history_counts"]["scenarios"] = {
                scenario_id: len(history)
                for scenario_id, history in session["scenario_histories"].items()
            }
        
        if "watch_history" in session:
            summary["history_counts"]["watch"] = len(session["watch_history"])
        
        return summary
    
    def clear_all_session_data(self) -> None:
        """すべてのセッションデータをクリア"""
        # 保持すべきキーのリスト
        preserve_keys = ["user_id", "selected_model", "session_id", "created_at"]
        
        # 保持するデータを一時保存
        preserved_data = {
            key: session.get(key) for key in preserve_keys if key in session
        }
        
        # セッションをクリア
        session.clear()
        
        # 保持するデータを復元
        for key, value in preserved_data.items():
            if value is not None:
                session[key] = value
        
        session.modified = True