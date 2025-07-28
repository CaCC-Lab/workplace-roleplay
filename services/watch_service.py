"""
観戦モードサービス
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage


class WatchService:
    """観戦モード関連の操作を管理するサービスクラス"""
    
    def generate_initial_prompt(self, topic: str) -> str:
        """観戦モードの初期プロンプトを生成"""
        return f"""あなたは職場でのコミュニケーションの専門家です。
以下のトピックについて、建設的で実践的な意見を述べてください。

トピック: {topic}

最初の発言として、このトピックについてのあなたの考えを
2-3文で簡潔に述べてください。相手が返答しやすいように、
質問や意見を求める形で締めくくってください。"""
    
    def format_messages_for_watch(
        self,
        history: List[Dict[str, Any]],
        current_role: str
    ) -> List[BaseMessage]:
        """観戦モード用にメッセージをフォーマット"""
        messages = []
        
        # パートナー用のシステムプロンプト
        system_prompt = self._get_partner_system_prompt(current_role)
        messages.append(SystemMessage(content=system_prompt))
        
        # 履歴を変換（自分と相手の役割を適切に設定）
        for entry in history:
            entry_role = entry.get("role", "")
            content = entry.get("content", "")
            
            if entry_role == current_role:
                # 自分の過去の発言
                messages.append(AIMessage(content=content))
            else:
                # 相手の発言
                messages.append(HumanMessage(content=content))
        
        return messages
    
    def generate_watch_feedback(
        self,
        llm: Any,
        history: List[Dict[str, Any]],
        watch_settings: Dict[str, Any]
    ) -> str:
        """観戦モードのフィードバックを生成"""
        # 会話履歴をフォーマット
        conversation_text = self._format_watch_conversation(history)
        topic = watch_settings.get("topic", "不明")
        
        prompt = f"""以下の2人の職場でのコミュニケーションを分析し、
学習ポイントをまとめてください。

トピック: {topic}

会話内容:
{conversation_text}

以下の観点から分析してください：

1. 効果的なコミュニケーション技術の例（3-4点）
2. それぞれの参加者の強み
3. 実際の職場で応用できるポイント（2-3点）
4. この会話から学べる重要な教訓

分析は具体的で、実践的なアドバイスを含めてください。"""
        
        messages = [SystemMessage(content=prompt)]
        
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            response = llm_service.create_and_get_response(llm, messages)
            return response
        except Exception as e:
            return f"フィードバックの生成中にエラーが発生しました: {str(e)}"
    
    def calculate_duration(self, history: List[Dict[str, Any]]) -> str:
        """会話の継続時間を計算"""
        if not history:
            return "0分"
        
        try:
            first_timestamp = history[0].get("timestamp", "")
            last_timestamp = history[-1].get("timestamp", "")
            
            if not first_timestamp or not last_timestamp:
                return "不明"
            
            first_time = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
            
            duration = last_time - first_time
            minutes = int(duration.total_seconds() / 60)
            
            if minutes < 1:
                return "1分未満"
            elif minutes < 60:
                return f"{minutes}分"
            else:
                hours = minutes // 60
                remaining_minutes = minutes % 60
                return f"{hours}時間{remaining_minutes}分"
                
        except Exception:
            return "不明"
    
    def _get_partner_system_prompt(self, role: str) -> str:
        """パートナー用のシステムプロンプトを取得"""
        if role == "partner1":
            return """あなたは経験豊富なビジネスパーソンです。
相手の意見に対して建設的に反応し、議論を深めていきます。
具体例や実体験を交えながら、実践的な視点で会話を進めてください。
時には異なる視点を提示して、議論を活性化させてください。"""
        else:
            return """あなたは向上心のある若手ビジネスパーソンです。
相手の意見から学ぼうとする姿勢を持ちながらも、
自分の考えもしっかりと伝えます。
質問を通じて理解を深め、新しいアイデアも積極的に提案してください。"""
    
    def _format_watch_conversation(self, history: List[Dict[str, Any]]) -> str:
        """観戦モードの会話履歴をフォーマット"""
        formatted_lines = []
        
        for i, entry in enumerate(history):
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            
            if role == "partner1":
                formatted_lines.append(f"[{i+1}] 参加者A: {content}")
            elif role == "partner2":
                formatted_lines.append(f"[{i+1}] 参加者B: {content}")
            elif role == "system" and entry.get("type") != "feedback":
                formatted_lines.append(f"[{i+1}] システム: {content}")
        
        return "\n".join(formatted_lines)
    
    def generate_next_message(
        self,
        llm: Any,
        history: List[Dict[str, Any]],
        current_role: str
    ) -> str:
        """次のメッセージを生成"""
        messages = self.format_messages_for_watch(history, current_role)
        
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            response = llm_service.create_and_get_response(llm, messages)
            return response
        except Exception as e:
            return "申し訳ありません。応答の生成中にエラーが発生しました。"