"""
プロンプト生成を管理するサービス
システムプロンプトやフィードバックプロンプトの構築を担当
"""
from typing import Any, Dict, List, Optional

from utils.constants import MAX_FEEDBACK_LENGTH


class PromptService:
    """プロンプト生成を管理するサービス"""

    # 雑談モード用システムプロンプト
    DEFAULT_CHAT_SYSTEM_PROMPT = """あなたは職場での雑談が得意な親しみやすい同僚です。
相手の気持ちに共感し、適度な距離感を保ちながら会話をしてください。
話題は仕事のこと、趣味、最近のニュース、週末の予定など、職場で自然に話すような内容にしてください。
返答は自然で簡潔にし、相手が話しやすい雰囲気を作ってください。"""

    # 観戦モード用基本プロンプト
    WATCH_MODE_BASE_PROMPT = """あなたは職場の同僚です。
今、同僚と「{topic}」について雑談をしています。
自然で親しみやすい会話を心がけ、相手の話に興味を示しながら会話を続けてください。
返答は簡潔にし、会話が続くような内容にしてください。"""

    @classmethod
    def build_scenario_system_prompt(cls, scenario: Dict[str, Any]) -> str:
        """
        シナリオ用システムプロンプトを構築

        Args:
            scenario: シナリオデータ

        Returns:
            str: システムプロンプト
        """
        character = scenario.get("character", {})
        return f"""あなたは{character.get('name', '相手')}という{character.get('role', '同僚')}です。
{character.get('personality', '')}

以下の状況で会話をしてください：
{scenario.get('situation', '')}

{scenario.get('instructions', '')}

相手の言動に対して、{character.get('name', '相手')}らしく自然に反応してください。"""

    @classmethod
    def build_watch_mode_prompt(cls, topic: str, is_initiator: bool = False) -> str:
        """
        観戦モード用プロンプトを構築

        Args:
            topic: 会話のトピック
            is_initiator: 会話の開始者かどうか

        Returns:
            str: プロンプト
        """
        base = cls.WATCH_MODE_BASE_PROMPT.format(topic=topic)
        
        if is_initiator:
            return f"{base}\n\nあなたから話題を始めてください。"
        else:
            return f"{base}\n\n相手の発言に対して自然に返答してください。"

    @classmethod
    def build_chat_feedback_prompt(
        cls,
        conversation_text: str,
        max_length: int = MAX_FEEDBACK_LENGTH
    ) -> str:
        """
        雑談フィードバック用プロンプトを構築

        Args:
            conversation_text: 会話内容テキスト
            max_length: フィードバックの最大文字数

        Returns:
            str: フィードバックプロンプト
        """
        return f"""以下の職場での雑談を分析して、ユーザーのコミュニケーションスキルに関する建設的なフィードバックを提供してください。

※最重要：ユーザーの発言・行動のみを評価し、AIの行動は一切評価しないこと。

会話内容：
{conversation_text}

以下の観点でユーザーの発言・行動のみを評価してください：
1. 話題の選び方と展開
2. 相手への配慮と共感
3. 職場での適切さ
4. 改善できる点

フィードバックは具体的で実践的なアドバイスを含め、{max_length}文字以内でまとめてください。"""

    @classmethod
    def build_scenario_feedback_prompt(
        cls,
        scenario: Dict[str, Any],
        conversation_text: str,
        max_length: int = MAX_FEEDBACK_LENGTH
    ) -> str:
        """
        シナリオフィードバック用プロンプトを構築

        Args:
            scenario: シナリオデータ
            conversation_text: 会話内容テキスト
            max_length: フィードバックの最大文字数

        Returns:
            str: フィードバックプロンプト
        """
        # フィードバックポイントを整形
        feedback_points = "\n".join(
            [f"- {point}" for point in scenario.get("feedback_points", [])]
        )

        return f"""以下のロールプレイシナリオでの会話を分析して、ユーザーのコミュニケーションスキルに関する建設的なフィードバックを提供してください。

※最重要：ユーザーの発言・行動のみを評価し、AIの行動は一切評価しないこと。

シナリオ: {scenario.get('title', 'シナリオ')}
状況: {scenario.get('situation', '')}
あなたの役割: {scenario.get('your_role', 'プレイヤー')}

会話内容：
{conversation_text}

評価ポイント：
{feedback_points}

以下の観点でユーザーの発言・行動のみを評価してください：
1. シナリオの目的に対する達成度
2. コミュニケーションの適切さ
3. 良かった点
4. 改善できる点
5. 次回への具体的なアドバイス

フィードバックは具体的で実践的なアドバイスを含め、{max_length}文字以内でまとめてください。"""

    @classmethod
    def format_conversation_for_feedback(
        cls,
        history: List[Dict[str, Any]],
        ai_name: str = "相手"
    ) -> str:
        """
        フィードバック用に会話履歴をフォーマット

        Args:
            history: 会話履歴
            ai_name: AI側の名前

        Returns:
            str: フォーマットされた会話テキスト
        """
        lines = []
        for entry in history:
            human_msg = entry.get("human", entry.get("user", ""))
            ai_msg = entry.get("ai", entry.get("assistant", ""))
            if human_msg:
                lines.append(f"あなた: {human_msg}")
            if ai_msg:
                lines.append(f"{ai_name}: {ai_msg}")
        return "\n".join(lines)


# シングルトンインスタンス
_prompt_service: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """PromptServiceのシングルトンインスタンスを取得"""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service
