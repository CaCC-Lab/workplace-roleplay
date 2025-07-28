"""セッション管理サービス"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from flask import session


class SessionService:
    """セッション管理サービス"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self) -> str:
        """新しいセッションを作成
        
        Returns:
            セッションID
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "messages": [],
            "metadata": {}
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッション情報
        """
        return self._sessions.get(session_id)
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """メッセージを追加
        
        Args:
            session_id: セッションID
            role: ロール（user, assistant, system）
            content: メッセージ内容
            metadata: メタデータ
        """
        session_data = self.get_session(session_id)
        if session_data is None:
            raise ValueError(f"Session not found: {session_id}")
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        
        session_data["messages"].append(message)
        session_data["updated_at"] = datetime.now()
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """メッセージ履歴を取得
        
        Args:
            session_id: セッションID
            limit: 取得件数の上限
            
        Returns:
            メッセージリスト
        """
        session_data = self.get_session(session_id)
        if session_data is None:
            return []
        
        messages = session_data["messages"]
        if limit is not None:
            messages = messages[-limit:]
        
        return messages
    
    def clear_session(self, session_id: str) -> None:
        """セッションをクリア
        
        Args:
            session_id: セッションID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def get_or_create_session(self) -> str:
        """現在のセッションIDを取得（なければ作成）
        
        Returns:
            セッションID
        """
        session_id = session.get("session_id")
        if session_id is None or session_id not in self._sessions:
            session_id = self.create_session()
            session["session_id"] = session_id
        return session_id