"""
Common helper functions for the workplace-roleplay application.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from flask import session
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


def extract_content(resp: Union[AIMessage, str, List[Any], Dict[str, Any], Any]) -> str:
    """
    様々な形式のレスポンスから内容を抽出

    Args:
        resp: LLMからのレスポンス

    Returns:
        str: 抽出されたコンテンツ
    """
    if isinstance(resp, AIMessage):
        return str(resp.content)
    elif isinstance(resp, str):
        return resp
    elif isinstance(resp, list):
        if not resp:  # 空リストの場合
            return "応答が空でした。"
        # リストの最後のメッセージを処理
        last_msg = resp[-1]
        return extract_content(last_msg)  # 再帰的に処理
    elif isinstance(resp, dict):
        # 辞書の場合、contentキーを探す
        if "content" in resp:
            return str(resp["content"])
        # その他の既知のキーを確認
        for key in ["text", "message", "response"]:
            if key in resp:
                return str(resp[key])
    # 上記以外の場合は文字列に変換して返す
    try:
        return str(resp)
    except Exception:
        return "応答を文字列に変換できませんでした。"


def format_conversation_history(history: List[Dict[str, Any]]) -> str:
    """
    会話履歴を読みやすい形式にフォーマット（ユーザーの発言のみ）

    Args:
        history: 会話履歴のリスト

    Returns:
        str: フォーマットされた会話履歴
    """
    formatted = []
    for entry in history:
        # ユーザーの発言のみを含める
        if entry.get("human"):
            formatted.append(f"ユーザー: {entry['human']}")
    return "\n".join(formatted)


def format_conversation_history_for_feedback(history: List[Dict[str, Any]]) -> str:
    """
    フィードバック分析用に、AIとユーザー双方の会話履歴をフォーマットする

    Args:
        history: 会話履歴のリスト

    Returns:
        str: フォーマットされた会話履歴
    """
    formatted = []
    for entry in history:
        # 内部的な開始メッセージは分析に不要なため除外
        if entry.get("human") and entry["human"] not in ("[シナリオ開始]", "[雑談開始]"):
            formatted.append(f"ユーザー: {entry['human']}")
        if entry.get("ai"):
            formatted.append(f"AI: {entry['ai']}")
    return "\n".join(formatted)


def get_partner_description(partner_type: str) -> str:
    """
    相手の説明を取得

    Args:
        partner_type: 相手のタイプ

    Returns:
        str: 相手の説明
    """
    descriptions = {
        "colleague": "同年代の同僚",
        "senior": "入社5年目程度の先輩社員",
        "junior": "入社2年目の後輩社員",
        "boss": "40代の課長",
        "client": "取引先の担当者（30代後半）",
    }
    return descriptions.get(partner_type, "同僚")


def get_situation_description(situation: str) -> str:
    """
    状況の説明を取得

    Args:
        situation: 状況のタイプ

    Returns:
        str: 状況の説明
    """
    descriptions = {
        "lunch": "ランチ休憩中のカフェテリアで",
        "break": "午後の休憩時間、休憩スペースで",
        "morning": "朝、オフィスに到着して席に着く前",
        "evening": "終業後、退社準備をしている時間",
        "party": "部署の懇親会で",
    }
    return descriptions.get(situation, "オフィスで")


def get_topic_description(topic: str) -> str:
    """
    話題の説明を取得

    Args:
        topic: 話題のタイプ

    Returns:
        str: 話題の説明
    """
    descriptions = {
        "general": "天気や週末の予定など、一般的な話題",
        "hobby": "趣味や休日の過ごし方について",
        "news": "最近のニュースや時事問題について",
        "food": "ランチや食事、おすすめのお店について",
        "work": "仕事に関する一般的な内容（機密情報は避ける）",
    }
    return descriptions.get(topic, "一般的な話題")


def add_messages_from_history(
    messages: List[BaseMessage], history: List[Dict[str, Any]], max_entries: int = 5
) -> List[BaseMessage]:
    """
    会話履歴からメッセージリストを構築するヘルパー関数

    Args:
        messages: 追加先のメッセージリスト
        history: 会話履歴（辞書のリスト）
        max_entries: 取得する最大エントリ数

    Returns:
        List[BaseMessage]: 更新されたメッセージリスト
    """
    # 直近の会話履歴を追加（トークン数削減のため最新n件のみ）
    recent_history = history[-max_entries:] if history else []

    for entry in recent_history:
        if entry.get("human"):
            messages.append(HumanMessage(content=entry["human"]))
        if entry.get("ai"):
            messages.append(AIMessage(content=entry["ai"]))

    return messages


# ========== セッション管理ヘルパー ==========


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


def add_to_session_history(
    session_key: str, entry: Dict[str, Any], sub_key: Optional[str] = None
) -> None:
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
        session[settings_key] = (
            {} if sub_key else {"start_time": datetime.now().isoformat()}
        )

    # サブキーがある場合
    if sub_key:
        if sub_key not in session[settings_key]:
            session[settings_key][sub_key] = {}
        session[settings_key][sub_key]["start_time"] = datetime.now().isoformat()
    else:
        session[settings_key]["start_time"] = datetime.now().isoformat()

    session.modified = True
