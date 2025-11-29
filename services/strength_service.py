"""
Strength analysis service for the workplace-roleplay application.
Handles user strength analysis business logic.
"""

from typing import Any, Dict, List

from strength_analyzer import (
    analyze_user_strengths,
    generate_encouragement_messages,
    get_top_strengths,
)
from utils.helpers import format_conversation_history


class StrengthService:
    """強み分析関連のビジネスロジックを処理するサービス"""

    def analyze_user_strengths_from_history(
        self, history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        会話履歴からユーザーの強みを分析

        Args:
            history: 会話履歴

        Returns:
            Dict[str, Any]: 分析結果（スコア、メッセージ等）
        """
        if not history:
            return {
                "scores": {
                    key: 50
                    for key in [
                        "empathy",
                        "clarity",
                        "active_listening",
                        "adaptability",
                        "positivity",
                        "professionalism",
                    ]
                },
                "messages": ["まだ練習履歴がありません。会話を始めてみましょう！"],
                "history": [],
            }

        # 会話履歴をフォーマット
        formatted_history = format_conversation_history(history)

        # 強み分析を実行
        scores = analyze_user_strengths(formatted_history)

        # 励ましメッセージを生成
        messages = generate_encouragement_messages(scores, [])

        # パーソナライズされたメッセージを追加
        if messages and len(messages) < 3:
            top_strength = get_top_strengths(scores, 1)[0]
            import random

            additional_messages = [
                f"{top_strength['name']}の才能が光っています！この強みを活かしてさらに成長しましょう。",
                f"素晴らしい{top_strength['name']}ですね！次回はさらに磨きをかけていきましょう。",
                f"{top_strength['name']}が{top_strength['score']}点！あなたの強みを自信にして前進しましょう。",
            ]
            messages.append(random.choice(additional_messages))

        return {"scores": scores, "messages": messages}

    def get_top_strengths(
        self, scores: Dict[str, int], top_n: int = 3
    ) -> List[Dict[str, Any]]:
        """
        トップNの強みを取得

        Args:
            scores: スコア辞書
            top_n: 取得する強みの数

        Returns:
            List[Dict[str, Any]]: トップNの強みリスト
        """
        return get_top_strengths(scores, top_n)

    def generate_encouragement_messages(
        self, scores: Dict[str, int], previous_history: List[Dict[str, Any]] = None
    ) -> List[str]:
        """
        励ましメッセージを生成

        Args:
            scores: スコア辞書
            previous_history: 過去の分析履歴（オプション）

        Returns:
            List[str]: 励ましメッセージのリスト
        """
        if previous_history is None:
            previous_history = []
        return generate_encouragement_messages(scores, previous_history)

    def update_feedback_with_strength_analysis(
        self,
        feedback_response: Dict[str, Any],
        session_type: str,
        scenario_id: str = None,
    ) -> Dict[str, Any]:
        """
        既存のフィードバックレスポンスに強み分析を追加

        Args:
            feedback_response: フィードバックレスポンス
            session_type: セッションタイプ（"chat"または"scenario"）
            scenario_id: シナリオID（オプション）

        Returns:
            Dict[str, Any]: 強み分析を追加したフィードバックレスポンス
        """
        try:
            from flask import session

            # 会話履歴を取得
            if session_type == "chat":
                history = session.get("chat_history", [])
            else:
                history = session.get("scenario_history", {}).get(scenario_id, [])

            if history:
                # 強み分析を実行
                formatted_history = format_conversation_history(history)
                scores = analyze_user_strengths(formatted_history)

                # トップ3の強みを取得
                top_strengths = get_top_strengths(scores, 3)

                # フィードバックレスポンスに追加
                feedback_response["strength_analysis"] = {
                    "scores": scores,
                    "top_strengths": top_strengths,
                }
        except Exception as e:
            print(f"Error adding strength analysis to feedback: {str(e)}")

        return feedback_response


# グローバルインスタンス
_strength_service: "StrengthService" = None


def get_strength_service() -> StrengthService:
    """StrengthServiceのシングルトンインスタンスを取得"""
    global _strength_service
    if _strength_service is None:
        _strength_service = StrengthService()
    return _strength_service
