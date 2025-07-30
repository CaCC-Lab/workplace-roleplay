"""チャットサービス"""
from typing import Optional


from .llm_service import LLMService
from .session_service import SessionService


class ChatService:
    """チャット機能を提供するサービス"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.session_service = SessionService()
    
    def process_message(
        self,
        session_id: str,
        message: str,
        model_name: Optional[str] = None
    ) -> str:
        """メッセージを処理して応答を生成
        
        Args:
            session_id: セッションID
            message: ユーザーメッセージ
            model_name: 使用するモデル名
            
        Returns:
            生成された応答
        """
        # メッセージを履歴に追加
        self.session_service.add_message(
            session_id=session_id,
            role="user",
            content=message
        )
        
        # 会話履歴を取得
        messages = self.session_service.get_messages(session_id, limit=10)
        
        # プロンプトの構築
        prompt = self._build_chat_prompt(messages)
        
        # 応答を生成
        response = self.llm_service.generate_response(
            prompt=prompt,
            model_name=model_name
        )
        
        # 応答を履歴に追加
        self.session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=response
        )
        
        return response
    
    def _build_chat_prompt(self, messages: list) -> str:
        """会話履歴からプロンプトを構築
        
        Args:
            messages: メッセージ履歴
            
        Returns:
            プロンプト文字列
        """
        # システムプロンプト
        system_prompt = """あなたは職場でのコミュニケーションを支援するアシスタントです。
ユーザーの質問や相談に対して、親切で建設的なアドバイスを提供してください。"""
        
        # 会話履歴を整形
        conversation = [f"システム: {system_prompt}"]
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                conversation.append(f"ユーザー: {content}")
            elif role == "assistant":
                conversation.append(f"アシスタント: {content}")
        
        # 最後に応答指示を追加
        conversation.append("アシスタント:")
        
        return "\n\n".join(conversation)