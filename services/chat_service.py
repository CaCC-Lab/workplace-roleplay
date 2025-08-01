"""
チャット機能サービス
雑談チャットの処理ロジックを担当
"""
from typing import Dict, Any, Generator, List
import json
from datetime import datetime
import logging

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from services.llm_service import LLMService
from services.session_service import SessionService
from errors import ValidationError, ExternalAPIError
from utils.security import SecurityUtils


class ChatService:
    """チャット機能のためのサービスクラス"""
    
    # チャットシステムプロンプト
    CHAT_SYSTEM_PROMPT = """あなたは親切で共感的な会話パートナーです。
ユーザーの話に耳を傾け、適切な相槌や質問を交えながら、
自然で楽しい会話を心がけてください。

重要な指針：
1. ユーザーの感情に寄り添い、共感的な返答をする
2. 適度に質問を投げかけて、会話を深める
3. ポジティブで建設的な雰囲気を保つ
4. 相手の興味や関心事を引き出す
5. 自然な日本語で、親しみやすい口調を使う"""
    
    @staticmethod
    def handle_chat_message(message: str, model_name: str = None) -> Generator[str, None, None]:
        """
        チャットメッセージを処理してストリーミングレスポンスを生成
        
        Args:
            message: ユーザーのメッセージ
            model_name: 使用するモデル名（省略時はセッションから取得）
            
        Yields:
            SSE形式のレスポンスチャンク
            
        Raises:
            ValidationError: メッセージが空の場合
            ExternalAPIError: LLM API呼び出しに失敗した場合
        """
        # 入力検証
        if not message or not message.strip():
            raise ValidationError("メッセージを入力してください", field="message")
        
        # XSS対策のためのサニタイズ
        message = SecurityUtils.sanitize_input(message)
        
        # モデル名の取得
        if not model_name:
            model_name = SessionService.get_session_data('selected_model', 'gemini-1.5-flash')
        
        # LLMの初期化
        llm = LLMService.create_llm(model_name)
        
        # チャット履歴の初期化
        SessionService.initialize_session_history('chat_history')
        
        # 開始時刻の設定
        SessionService.set_session_start_time('chat')
        
        # 履歴の取得
        history = SessionService.get_session_history('chat_history')
        
        # プロンプトの構築
        prompt = ChatPromptTemplate.from_messages([
            ("system", ChatService.CHAT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        # メッセージリストの作成
        messages = []
        LLMService.add_messages_from_history(messages, history)
        messages.append(HumanMessage(content=message))
        
        # チェーンの作成と実行
        chain = prompt | llm
        
        try:
            # ストリーミング応答の生成
            assistant_response = ""
            
            for chunk in chain.stream({"input": message, "history": messages[:-1]}):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    assistant_response += content
                    
                    # SSE形式でチャンクを送信
                    data = {
                        'content': content,
                        'type': 'content'
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            
            # 会話履歴に追加
            SessionService.add_to_session_history('chat_history', {
                'user': message,
                'assistant': assistant_response,
                'timestamp': datetime.now().isoformat(),
                'model': model_name
            })
            
            # 完了メッセージ
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            print(f"Chat streaming error: {str(e)}")
            # エラーメッセージをSSE形式で送信
            error_data = {
                'type': 'error',
                'message': 'メッセージの生成中にエラーが発生しました'
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            raise ExternalAPIError("Gemini", "チャット応答の生成に失敗しました", str(e))
    
    @staticmethod
    def generate_chat_feedback() -> Dict[str, Any]:
        """
        チャット練習のフィードバックを生成
        
        Returns:
            フィードバック情報の辞書
        """
        history = SessionService.get_session_history('chat_history')
        
        if not history:
            return {
                'feedback': 'まだ会話履歴がありません。まずは雑談を楽しんでみましょう！',
                'conversation_count': 0
            }
        
        # フィードバック生成用のプロンプト
        feedback_prompt = f"""
以下の会話履歴を分析して、ユーザーのコミュニケーションスキルについて
ポジティブで建設的なフィードバックを200文字程度で生成してください。

会話履歴:
"""
        
        # 最近の5つの会話を使用
        recent_history = history[-5:]
        for entry in recent_history:
            if 'user' in entry:
                feedback_prompt += f"ユーザー: {entry['user']}\n"
            if 'assistant' in entry:
                feedback_prompt += f"アシスタント: {entry['assistant']}\n"
        
        feedback_prompt += """
フィードバックには以下を含めてください:
1. 良かった点
2. さらに良くなるためのアドバイス
3. 励ましのメッセージ
"""
        
        try:
            # フィードバックの生成
            feedback_content, used_model, error = LLMService.try_multiple_models_for_prompt(feedback_prompt)
            
            if error:
                feedback_content = "フィードバックの生成に失敗しました。会話を続けてみてください。"
            
            return {
                'feedback': feedback_content,
                'conversation_count': len(history),
                'recent_topics': ChatService._extract_topics(recent_history),
                'model': used_model
            }
            
        except Exception as e:
            print(f"Feedback generation error: {str(e)}")
            return {
                'feedback': 'フィードバックの生成中にエラーが発生しました。',
                'conversation_count': len(history),
                'error': str(e)
            }
    
    @staticmethod
    def _extract_topics(history: list) -> list:
        """
        会話履歴から話題を抽出（簡易版）
        
        Args:
            history: 会話履歴
            
        Returns:
            話題のリスト
        """
        # TODO: より高度な話題抽出ロジックの実装
        topics = []
        keywords = ['仕事', '趣味', '週末', '料理', 'スポーツ', '映画', '音楽', '旅行']
        
        for entry in history:
            if 'user' in entry:
                for keyword in keywords:
                    if keyword in entry['user']:
                        if keyword not in topics:
                            topics.append(keyword)
        
        return topics[:3]  # 最大3つまで
    
    @staticmethod
    def clear_chat_history() -> Dict[str, str]:
        """
        チャット履歴をクリア
        
        Returns:
            結果メッセージ
        """
        SessionService.clear_session_history('chat_history')
        return {'message': 'チャット履歴をクリアしました'}