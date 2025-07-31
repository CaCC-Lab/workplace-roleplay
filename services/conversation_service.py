"""
会話管理サービス
"""
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage



class ConversationService:
    """会話関連の操作を管理するサービスクラス"""
    
    def format_messages_for_chat(
        self, 
        history: List[Dict[str, Any]], 
        current_message: str
    ) -> List[BaseMessage]:
        """チャット用にメッセージをフォーマット"""
        messages = []
        
        # システムプロンプト
        system_prompt = """あなたは職場での雑談の練習相手です。
自然で親しみやすい会話を心がけ、相手が話しやすい雰囲気を作ってください。
適度に質問を投げかけ、会話が続くようにしてください。
日本の職場文化に適した話し方を使ってください。"""
        
        messages.append(SystemMessage(content=system_prompt))
        
        # 履歴からメッセージを追加（最新の10件まで）
        recent_history = history[-10:] if len(history) > 10 else history
        for entry in recent_history:
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            elif entry["role"] == "assistant":
                messages.append(AIMessage(content=entry["content"]))
        
        # 現在のメッセージを追加
        messages.append(HumanMessage(content=current_message))
        
        return messages
    
    def generate_initial_message(
        self,
        llm: Any,
        partner_type: str,
        situation: str,
        topic: str
    ) -> str:
        """初期メッセージを生成"""
        partner_desc = self.get_partner_description(partner_type)
        situation_desc = self.get_situation_description(situation)
        topic_desc = self.get_topic_description(topic)
        
        prompt = f"""あなたは{partner_desc}です。
{situation_desc}で、{topic_desc}について話しかけます。
自然で親しみやすい挨拶から始めてください。
相手が返答しやすいように、簡単な質問を含めてください。"""
        
        messages = [SystemMessage(content=prompt)]
        
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            response = llm_service.create_and_get_response(llm, messages)
            return response
        except Exception as e:
            # エラー時のフォールバックメッセージ
            return self._get_fallback_initial_message(partner_type, situation, topic)
    
    def generate_chat_feedback(
        self,
        llm: Any,
        history: List[Dict[str, Any]],
        chat_settings: Dict[str, Any]
    ) -> str:
        """雑談練習のフィードバックを生成"""
        # ユーザーのメッセージのみをフォーマット
        conversation_text = self.format_user_messages_only(history)
        
        # フィードバック生成プロンプト
        prompt = f"""以下の職場での雑談を分析し、建設的なフィードバックを提供してください。

会話の状況:
- 相手: {self.get_partner_description(chat_settings.get('partner_type', '同僚'))}
- シチュエーション: {self.get_situation_description(chat_settings.get('situation', '朝の挨拶'))}
- 話題: {self.get_topic_description(chat_settings.get('topic', '天気'))}

ユーザーの発言:
{conversation_text}

以下の観点から具体的なフィードバックを提供してください：

1. 良かった点（2-3点）
2. 改善できる点（2-3点）
3. 次回の練習で意識すると良いポイント（1-2点）

フィードバックは励みになるよう前向きなトーンで、
具体的な例や代替案を含めて提供してください。"""
        
        messages = [SystemMessage(content=prompt)]
        
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            response = llm_service.create_and_get_response(llm, messages)
            return response
        except Exception as e:
            return f"フィードバックの生成中にエラーが発生しました: {str(e)}"
    
    def format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """会話履歴を読みやすい形式にフォーマット"""
        formatted_lines = []
        
        for entry in history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            
            if role == "user":
                formatted_lines.append(f"あなた: {content}")
            elif role == "assistant":
                formatted_lines.append(f"相手: {content}")
            elif role == "system" and entry.get("type") != "feedback":
                formatted_lines.append(f"システム: {content}")
        
        return "\n".join(formatted_lines)
    
    def format_user_messages_only(self, history: List[Dict[str, Any]]) -> str:
        """ユーザーのメッセージのみをフォーマット（フィードバック用）"""
        formatted_lines = []
        user_msg_count = 0
        
        for entry in history:
            if entry.get("role") == "user":
                user_msg_count += 1
                content = entry.get("content", "")
                formatted_lines.append(f"[{user_msg_count}] ユーザー: {content}")
        
        return "\n".join(formatted_lines) if formatted_lines else "（ユーザーの発言なし）"
    
    def get_partner_description(self, partner_type: str) -> str:
        """パートナータイプの説明を取得"""
        descriptions = {
            "colleague": "同僚",
            "supervisor": "上司",
            "subordinate": "部下",
            "client": "クライアント",
            "vendor": "取引先"
        }
        return descriptions.get(partner_type, "同僚")
    
    def get_situation_description(self, situation: str) -> str:
        """シチュエーションの説明を取得"""
        descriptions = {
            "morning_greeting": "朝の挨拶",
            "lunch_break": "昼休み",
            "coffee_break": "休憩時間",
            "before_meeting": "会議前",
            "after_meeting": "会議後",
            "elevator": "エレベーター内"
        }
        return descriptions.get(situation, "職場")
    
    def get_topic_description(self, topic: str) -> str:
        """話題の説明を取得"""
        descriptions = {
            "weather": "天気",
            "weekend": "週末の予定",
            "hobbies": "趣味",
            "food": "食事",
            "news": "最近のニュース",
            "work": "仕事の話"
        }
        return descriptions.get(topic, "雑談")
    
    def _get_fallback_initial_message(
        self, 
        partner_type: str, 
        situation: str, 
        topic: str
    ) -> str:
        """フォールバック用の初期メッセージ"""
        partner = self.get_partner_description(partner_type)
        
        fallback_messages = {
            "morning_greeting": "おはようございます！今日もいい天気ですね。",
            "lunch_break": "お疲れ様です。もうお昼ですね。今日のランチはどうされますか？",
            "coffee_break": "少し休憩しませんか？コーヒーでも飲みながら。",
            "before_meeting": "もうすぐ会議ですね。準備はいかがですか？",
            "after_meeting": "会議お疲れ様でした。なかなか有意義でしたね。",
            "elevator": "こんにちは！今日は忙しそうですね。"
        }
        
        return fallback_messages.get(situation, "こんにちは！最近どうですか？")