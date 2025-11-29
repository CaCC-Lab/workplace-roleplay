"""
セッション管理サービス
Flask-Sessionのラッパーとして動作し、セッションデータの管理を担当
"""
import json
import os

# プロジェクトルートからインポート
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from flask import session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_VOICE,
    HistoryFormat,
    SessionKeys,
)
from utils.session_utils import (
    add_to_session_history,
    clear_session_history,
    get_conversation_memory,
    get_session_duration,
    initialize_session_history,
)


class SessionService:
    """セッション管理を担当するサービス"""

    # セッションキーの定義
    KEYS = SessionKeys

    def __init__(self):
        """SessionServiceの初期化"""
        pass

    def initialize_session(self) -> None:
        """セッションの初期化"""
        # 各履歴を初期化
        initialize_session_history(self.KEYS.CHAT_HISTORY)
        initialize_session_history(self.KEYS.SCENARIO_HISTORY)
        initialize_session_history(self.KEYS.WATCH_HISTORY)
        initialize_session_history(self.KEYS.LEARNING_HISTORY)

        # デフォルト値を設定
        if self.KEYS.CURRENT_MODEL not in session:
            session[self.KEYS.CURRENT_MODEL] = DEFAULT_CHAT_MODEL

        if self.KEYS.CURRENT_VOICE not in session:
            session[self.KEYS.CURRENT_VOICE] = DEFAULT_VOICE

    def get_user_id(self) -> str:
        """ユーザーIDを取得（なければ生成）"""
        if "user_id" not in session:
            session["user_id"] = str(uuid.uuid4())
        return session["user_id"]

    def get_current_model(self) -> str:
        """現在選択されているモデルを取得"""
        return session.get(self.KEYS.CURRENT_MODEL, DEFAULT_CHAT_MODEL)

    def set_current_model(self, model_name: str) -> None:
        """現在のモデルを設定"""
        session[self.KEYS.CURRENT_MODEL] = model_name

    def get_current_voice(self) -> str:
        """現在選択されている音声を取得"""
        return session.get(self.KEYS.CURRENT_VOICE, DEFAULT_VOICE)

    def set_current_voice(self, voice_name: str) -> None:
        """現在の音声を設定"""
        session[self.KEYS.CURRENT_VOICE] = voice_name

    def get_conversation_id(self) -> str:
        """現在の会話IDを取得（なければ生成）"""
        if "conversation_id" not in session:
            session["conversation_id"] = str(uuid.uuid4())
        return session["conversation_id"]

    def reset_conversation_id(self) -> str:
        """会話IDをリセットして新しいIDを返す"""
        session["conversation_id"] = str(uuid.uuid4())
        return session["conversation_id"]

    # チャット履歴管理
    def add_chat_message(self, human_message: str, ai_response: str) -> None:
        """チャットメッセージを履歴に追加"""
        entry = {
            "human": human_message,
            "ai": ai_response,
            "timestamp": datetime.now().isoformat(),
        }
        add_to_session_history(self.KEYS.CHAT_HISTORY, entry)

    def get_chat_history(
        self, format_type: str = HistoryFormat.FULL
    ) -> List[Dict[str, Any]]:
        """チャット履歴を取得"""
        # get_conversation_memoryを使用
        return get_conversation_memory("chat", max_messages=50)

    def clear_chat_history(self) -> None:
        """チャット履歴をクリア"""
        clear_session_history(self.KEYS.CHAT_HISTORY)

    # シナリオ履歴管理
    def add_scenario_message(
        self,
        scenario_id: str,
        human_message: str,
        ai_response: str,
        role: Optional[str] = None,
    ) -> None:
        """シナリオメッセージを履歴に追加"""
        entry = {
            "human": human_message,
            "ai": ai_response,
            "timestamp": datetime.now().isoformat(),
            "role": role,
        }
        add_to_session_history(self.KEYS.SCENARIO_HISTORY, entry, scenario_id)

    def get_scenario_history(
        self, scenario_id: str, format_type: str = HistoryFormat.FULL
    ) -> List[Dict[str, Any]]:
        """特定のシナリオの履歴を取得"""
        if self.KEYS.SCENARIO_HISTORY not in session:
            return []
        if scenario_id not in session[self.KEYS.SCENARIO_HISTORY]:
            return []
        return session[self.KEYS.SCENARIO_HISTORY][scenario_id]

    def clear_scenario_history(self, scenario_id: Optional[str] = None) -> None:
        """シナリオ履歴をクリア"""
        if scenario_id:
            # 特定のシナリオのみクリア
            if self.KEYS.SCENARIO_HISTORY in session:
                if scenario_id in session[self.KEYS.SCENARIO_HISTORY]:
                    session[self.KEYS.SCENARIO_HISTORY][scenario_id] = []
        else:
            # 全シナリオ履歴をクリア
            clear_session_history(self.KEYS.SCENARIO_HISTORY)

    def get_current_scenario_id(self) -> Optional[str]:
        """現在のシナリオIDを取得"""
        return session.get("current_scenario_id")

    def set_current_scenario_id(self, scenario_id: Optional[str]) -> None:
        """現在のシナリオIDを設定"""
        if scenario_id:
            session["current_scenario_id"] = scenario_id
        elif "current_scenario_id" in session:
            del session["current_scenario_id"]

    # 観戦モード履歴管理
    def add_watch_message(
        self,
        model1_message: str,
        model2_message: str,
        model1_name: str,
        model2_name: str,
    ) -> None:
        """観戦モードのメッセージを履歴に追加"""
        entry = {
            "model1": {"name": model1_name, "message": model1_message},
            "model2": {"name": model2_name, "message": model2_message},
            "timestamp": datetime.now().isoformat(),
        }
        add_to_session_history(self.KEYS.WATCH_HISTORY, entry)

    def get_watch_history(
        self, format_type: str = HistoryFormat.FULL
    ) -> List[Dict[str, Any]]:
        """観戦モードの履歴を取得"""
        return session.get(self.KEYS.WATCH_HISTORY, [])

    def clear_watch_history(self) -> None:
        """観戦モードの履歴をクリア"""
        clear_session_history(self.KEYS.WATCH_HISTORY)

    def get_watch_models(self) -> Dict[str, str]:
        """観戦モードで使用するモデルを取得"""
        return {
            "model1": session.get("watch_model1", DEFAULT_CHAT_MODEL),
            "model2": session.get("watch_model2", DEFAULT_CHAT_MODEL),
        }

    def set_watch_models(self, model1: str, model2: str) -> None:
        """観戦モードで使用するモデルを設定"""
        session["watch_model1"] = model1
        session["watch_model2"] = model2

    def get_watch_topic(self) -> Optional[str]:
        """観戦モードのトピックを取得"""
        return session.get("watch_topic")

    def set_watch_topic(self, topic: Optional[str]) -> None:
        """観戦モードのトピックを設定"""
        if topic:
            session["watch_topic"] = topic
        elif "watch_topic" in session:
            del session["watch_topic"]

    # 学習履歴管理
    def add_learning_record(
        self,
        activity_type: str,
        scenario_id: Optional[str] = None,
        feedback: Optional[Dict[str, Any]] = None,
        duration_seconds: Optional[int] = None,
    ) -> None:
        """学習記録を追加"""
        record = {
            "activity_type": activity_type,
            "timestamp": datetime.now().isoformat(),
            "user_id": self.get_user_id(),
            "conversation_id": self.get_conversation_id(),
        }

        if scenario_id:
            record["scenario_id"] = scenario_id
        if feedback:
            record["feedback"] = feedback
        if duration_seconds:
            record["duration_seconds"] = duration_seconds

        if self.KEYS.LEARNING_HISTORY not in session:
            session[self.KEYS.LEARNING_HISTORY] = []

        session[self.KEYS.LEARNING_HISTORY].append(record)

        # 最新100件のみ保持
        if len(session[self.KEYS.LEARNING_HISTORY]) > 100:
            session[self.KEYS.LEARNING_HISTORY] = session[self.KEYS.LEARNING_HISTORY][
                -100:
            ]

    def get_learning_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """学習履歴を取得"""
        history = session.get(self.KEYS.LEARNING_HISTORY, [])
        return history[-limit:] if history else []

    def get_learning_stats(self) -> Dict[str, Any]:
        """学習統計を取得"""
        history = self.get_learning_history(100)

        stats = {
            "total_sessions": len(history),
            "chat_sessions": 0,
            "scenario_sessions": 0,
            "watch_sessions": 0,
            "total_duration_seconds": 0,
            "scenarios_completed": set(),
        }

        for record in history:
            activity_type = record.get("activity_type")
            if activity_type == "chat":
                stats["chat_sessions"] += 1
            elif activity_type == "scenario":
                stats["scenario_sessions"] += 1
                if record.get("scenario_id"):
                    stats["scenarios_completed"].add(record["scenario_id"])
            elif activity_type == "watch":
                stats["watch_sessions"] += 1

            duration = record.get("duration_seconds", 0)
            stats["total_duration_seconds"] += duration

        stats["scenarios_completed"] = len(stats["scenarios_completed"])
        stats["total_duration_minutes"] = round(stats["total_duration_seconds"] / 60, 1)

        return stats

    # ユーティリティメソッド
    def export_session_data(self) -> Dict[str, Any]:
        """セッションデータをエクスポート（デバッグ用）"""
        return {
            "user_id": self.get_user_id(),
            "conversation_id": self.get_conversation_id(),
            "current_model": self.get_current_model(),
            "current_voice": self.get_current_voice(),
            "current_scenario_id": self.get_current_scenario_id(),
            "chat_history_count": len(self.get_chat_history()),
            "scenario_history_count": len(session.get(self.KEYS.SCENARIO_HISTORY, {})),
            "watch_history_count": len(self.get_watch_history()),
            "learning_stats": self.get_learning_stats(),
        }

    def clear_all_session_data(self) -> None:
        """全セッションデータをクリア（ユーザーIDは保持）"""
        user_id = self.get_user_id()

        # セッションをクリア
        session.clear()

        # ユーザーIDは復元
        session["user_id"] = user_id

        # デフォルト値を再設定
        self.initialize_session()

    def set_session_value(self, key: str, value: Any) -> None:
        """汎用的なセッション値の設定"""
        session[key] = value

    def get_session_value(self, key: str, default: Any = None) -> Any:
        """汎用的なセッション値の取得"""
        return session.get(key, default)

    def delete_session_value(self, key: str) -> None:
        """セッション値の削除"""
        if key in session:
            del session[key]
