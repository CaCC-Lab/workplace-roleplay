"""
セッション管理関連のユーティリティ関数
"""
from flask import session
from datetime import datetime
from typing import Dict, List, Any, Optional


def initialize_session_history(session_key: str, sub_key: Optional[str] = None) -> None:
    """
    セッション履歴を初期化するヘルパー関数
    
    Args:
        session_key: セッションのキー
        sub_key: サブキー（オプション）
    """
    if session_key not in session:
        session[session_key] = {} if sub_key else []
    
    if sub_key and sub_key not in session[session_key]:
        session[session_key][sub_key] = []
    
    session.modified = True


def add_to_session_history(session_key: str, entry: Dict[str, Any], sub_key: Optional[str] = None) -> None:
    """
    セッション履歴にエントリを追加するヘルパー関数
    
    Args:
        session_key: セッションのキー
        entry: 追加するエントリ（辞書）
        sub_key: サブキー（オプション）
    """
    # セッションが初期化されていることを確認
    initialize_session_history(session_key, sub_key)
    
    # エントリがなければタイムスタンプを追加
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now().isoformat()
    
    # 履歴に追加
    if sub_key:
        session[session_key][sub_key].append(entry)
    else:
        session[session_key].append(entry)
    
    session.modified = True


def clear_session_history(session_key: str, sub_key: Optional[str] = None) -> None:
    """
    セッション履歴をクリアするヘルパー関数
    
    Args:
        session_key: クリアするセッションのキー
        sub_key: クリアするサブキー（オプション）
    """
    if session_key in session:
        if sub_key:
            if sub_key in session[session_key]:
                session[session_key][sub_key] = []
        else:
            session[session_key] = {} if isinstance(session[session_key], dict) else []
    
    session.modified = True


def set_session_start_time(session_key: str, sub_key: Optional[str] = None) -> None:
    """
    セッションの開始時間を記録するヘルパー関数
    
    Args:
        session_key: セッションのキー
        sub_key: サブキー（オプション）
    """
    # セッション設定キーを構築
    settings_key = f"{session_key}_settings"
    
    # セッション設定が存在しない場合は初期化
    if settings_key not in session:
        session[settings_key] = {} if sub_key else {"start_time": datetime.now().isoformat()}
    
    # サブキーがある場合
    if sub_key:
        if sub_key not in session[settings_key]:
            session[settings_key][sub_key] = {}
        session[settings_key][sub_key]["start_time"] = datetime.now().isoformat()
    else:
        session[settings_key]["start_time"] = datetime.now().isoformat()
    
    session.modified = True


def get_session_duration(session_key: str, sub_key: Optional[str] = None) -> Optional[float]:
    """
    セッションの継続時間を取得（秒単位）
    
    Args:
        session_key: セッションのキー
        sub_key: サブキー（オプション）
        
    Returns:
        継続時間（秒）、開始時間がない場合はNone
    """
    settings_key = f"{session_key}_settings"
    
    if settings_key not in session:
        return None
    
    # 開始時間を取得
    if sub_key:
        if sub_key not in session[settings_key] or "start_time" not in session[settings_key][sub_key]:
            return None
        start_time_str = session[settings_key][sub_key]["start_time"]
    else:
        if "start_time" not in session[settings_key]:
            return None
        start_time_str = session[settings_key]["start_time"]
    
    # 継続時間を計算
    start_time = datetime.fromisoformat(start_time_str)
    duration = (datetime.now() - start_time).total_seconds()
    
    return duration


def get_conversation_memory(conversation_type: str, max_messages: int = 50) -> List[Dict[str, Any]]:
    """
    会話履歴を取得（メモリ制限付き）
    
    Args:
        conversation_type: 会話タイプ（chat, scenario, watch）
        max_messages: 最大メッセージ数
        
    Returns:
        会話履歴のリスト
    """
    memory_key = f"{conversation_type}_history"
    
    if memory_key not in session:
        return []
    
    history = session[memory_key]
    
    # リストの場合はそのまま、辞書の場合は全体を結合
    if isinstance(history, list):
        messages = history
    else:
        # シナリオ履歴のように辞書形式の場合
        messages = []
        for sub_history in history.values():
            if isinstance(sub_history, list):
                messages.extend(sub_history)
    
    # 最新のメッセージのみ返す
    return messages[-max_messages:] if len(messages) > max_messages else messages