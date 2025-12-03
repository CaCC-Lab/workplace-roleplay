"""
Watch service for the workplace-roleplay application.
Handles watch mode (AI conversation observation) business logic.
"""

import re
from typing import Any, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from utils.helpers import (
    extract_content,
    get_partner_description,
    get_situation_description,
    get_topic_description,
)


class WatchService:
    """観戦モード関連のビジネスロジックを処理するサービス"""

    def generate_initial_message(self, llm: BaseChatModel, partner_type: str, situation: str, topic: str) -> str:
        """
        観戦モードの最初のメッセージを生成

        Args:
            llm: LLMインスタンス
            partner_type: 相手のタイプ
            situation: 状況
            topic: 話題

        Returns:
            str: 生成されたメッセージ
        """
        system_prompt = f"""あなたは職場での自然な会話を行うAIです。
以下の点に注意して会話を始めてください：

設定：
- あなたは太郎という名前の社員です
- 相手: 花子という名前の{get_partner_description(partner_type)}
- 状況: {get_situation_description(situation)}
- 話題: {get_topic_description(topic)}

会話の注意点：
1. 設定された相手や状況に応じた適切な話し方をする
2. 自然な会話の流れを作る
3. 相手が話しやすい雰囲気を作る
4. 職場での適切な距離感を保つ

応答の制約：
- 感情や仕草は（）内に記述
- 発言は「」で囲む
- 1回の応答は3行程度まで
- 必ず日本語のみを使用する
- ローマ字や英語は使用しない
- 相手の名前は「花子さん」と呼ぶ

最初の声掛けをしてください。
"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="会話を始めてください。"),
        ]
        response = llm.invoke(messages)
        return extract_content(response)

    def generate_next_message(self, llm: BaseChatModel, history: List[Dict[str, Any]]) -> str:
        """
        観戦モードの次のメッセージを生成

        Args:
            llm: LLMインスタンス
            history: 会話履歴

        Returns:
            str: 生成されたメッセージ
        """
        # 会話履歴をフォーマット
        formatted_history = []
        for entry in history:
            speaker_name = "太郎" if entry["speaker"] == "A" else "花子"
            formatted_history.append(f"{speaker_name}: {entry['message']}")

        system_prompt = """あなたは職場での自然な会話を行うAIです。
以下の点に注意して会話を続けてください：

1. 前の発言に適切に応答する
2. 職場での適切な距離感を保つ
3. 自然な会話の流れを維持する
4. 話題を適度に展開する

応答の制約：
- 感情や仕草は（）内に記述
- 発言は「」で囲む
- 1回の応答は3行程度まで
- 必ず日本語のみを使用する
- ローマ字や英語は使用しない
- 重要：話者名（太郎、花子など）を含めず、発言内容のみを返してください
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="以下の会話履歴に基づいて、次の発言をしてください：\n\n" + "\n".join(formatted_history)),
        ]

        response = llm.invoke(messages)
        content = extract_content(response)

        # バックアップ機能：名前パターンを除去
        content = re.sub(r"^(太郎|花子):\s*", "", content.strip())

        return content

    def switch_speaker(self, current_speaker: str) -> str:
        """
        話者を切り替える

        Args:
            current_speaker: 現在の話者（"A"または"B"）

        Returns:
            str: 次の話者（"B"または"A"）
        """
        return "B" if current_speaker == "A" else "A"

    def get_speaker_display_name(self, speaker: str) -> str:
        """
        話者の表示名を取得

        Args:
            speaker: 話者ID（"A"または"B"）

        Returns:
            str: 表示名（"太郎"または"花子"）
        """
        return "太郎" if speaker == "A" else "花子"


# グローバルインスタンス
_watch_service: "WatchService" = None


def get_watch_service() -> WatchService:
    """WatchServiceのシングルトンインスタンスを取得"""
    global _watch_service
    if _watch_service is None:
        _watch_service = WatchService()
    return _watch_service
