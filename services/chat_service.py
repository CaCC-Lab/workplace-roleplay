"""
チャット機能を管理するサービス
雑談、シナリオ、観戦モードのビジネスロジックを担当
"""
from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple
from datetime import datetime
import json
import asyncio

# プロジェクトルートからインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_service import LLMService
from services.session_service import SessionService
from scenarios import get_scenario_by_id, get_all_scenarios
from utils.constants import (
    MAX_MESSAGE_LENGTH,
    MAX_FEEDBACK_LENGTH,
    EMOTION_VOICE_MAPPING
)


class ChatService:
    """チャット機能を管理するサービス"""
    
    def __init__(self, llm_service: Optional[LLMService] = None, session_service: Optional[SessionService] = None):
        """
        ChatServiceの初期化
        
        Args:
            llm_service: LLMサービスインスタンス（オプション）
            session_service: セッションサービスインスタンス（オプション）
        """
        self.llm_service = llm_service or LLMService()
        self.session_service = session_service or SessionService()
    
    async def process_chat_message(
        self,
        message: str,
        model_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        雑談モードでメッセージを処理
        
        Args:
            message: ユーザーからのメッセージ
            model_name: 使用するモデル名（オプション）
            
        Yields:
            str: レスポンスのチャンク
        """
        # メッセージの検証
        if not message or len(message) > MAX_MESSAGE_LENGTH:
            yield "メッセージが無効です。"
            return
        
        # モデル名が指定されていない場合は現在のモデルを使用
        if not model_name:
            model_name = self.session_service.get_current_model()
        
        # 会話履歴を取得
        chat_history = self.session_service.get_chat_history()
        
        # システムプロンプト
        system_prompt = """あなたは職場での雑談が得意な親しみやすい同僚です。
相手の気持ちに共感し、適度な距離感を保ちながら会話をしてください。
話題は仕事のこと、趣味、最近のニュース、週末の予定など、職場で自然に話すような内容にしてください。
返答は自然で簡潔にし、相手が話しやすい雰囲気を作ってください。"""
        
        # LLMからストリーミングレスポンスを取得
        accumulated_response = ""
        async for chunk in self.llm_service.stream_chat_response(
            message=message,
            history=chat_history,
            model_name=model_name,
            system_prompt=system_prompt
        ):
            accumulated_response += chunk
            yield chunk
        
        # セッションに履歴を保存
        if accumulated_response:
            self.session_service.add_chat_message(message, accumulated_response)
    
    async def process_scenario_message(
        self,
        scenario_id: str,
        message: str,
        model_name: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        シナリオモードでメッセージを処理
        
        Args:
            scenario_id: シナリオID
            message: ユーザーからのメッセージ
            model_name: 使用するモデル名（オプション）
            
        Yields:
            str: レスポンスのチャンク
        """
        # メッセージの検証
        if not message or len(message) > MAX_MESSAGE_LENGTH:
            yield "メッセージが無効です。"
            return
        
        # シナリオを取得
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            yield "シナリオが見つかりません。"
            return
        
        # モデル名が指定されていない場合は現在のモデルを使用
        if not model_name:
            model_name = self.session_service.get_current_model()
        
        # 現在のシナリオIDを設定
        self.session_service.set_current_scenario_id(scenario_id)
        
        # シナリオ履歴を取得
        scenario_history = self.session_service.get_scenario_history(scenario_id)
        
        # システムプロンプトを構築
        system_prompt = f"""あなたは{scenario['character']['name']}という{scenario['character']['role']}です。
{scenario['character']['personality']}

以下の状況で会話をしてください：
{scenario['situation']}

{scenario.get('instructions', '')}

相手の言動に対して、{scenario['character']['name']}らしく自然に反応してください。"""
        
        # LLMからストリーミングレスポンスを取得
        accumulated_response = ""
        async for chunk in self.llm_service.stream_chat_response(
            message=message,
            history=scenario_history,
            model_name=model_name,
            system_prompt=system_prompt
        ):
            accumulated_response += chunk
            yield chunk
        
        # セッションに履歴を保存
        if accumulated_response:
            self.session_service.add_scenario_message(
                scenario_id=scenario_id,
                human_message=message,
                ai_response=accumulated_response,
                role=scenario['character']['role']
            )
    
    async def start_watch_conversation(
        self,
        topic: str,
        model1: Optional[str] = None,
        model2: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        観戦モードで会話を開始
        
        Args:
            topic: 会話のトピック
            model1: モデル1の名前
            model2: モデル2の名前
            
        Yields:
            str: 会話の内容（JSON形式）
        """
        # モデルが指定されていない場合はデフォルトを使用
        watch_models = self.session_service.get_watch_models()
        if not model1:
            model1 = watch_models['model1']
        if not model2:
            model2 = watch_models['model2']
        
        # モデルとトピックを保存
        self.session_service.set_watch_models(model1, model2)
        self.session_service.set_watch_topic(topic)
        
        # 履歴をクリア
        self.session_service.clear_watch_history()
        
        # システムプロンプト
        base_prompt = f"""あなたは職場の同僚です。
今、同僚と「{topic}」について雑談をしています。
自然で親しみやすい会話を心がけ、相手の話に興味を示しながら会話を続けてください。
返答は簡潔にし、会話が続くような内容にしてください。"""
        
        # モデル1の初期メッセージを生成
        model1_prompt = f"{base_prompt}\n\nあなたから話題を始めてください。"
        
        model1_message = ""
        async for chunk in self.llm_service.stream_chat_response(
            message="会話を始めてください",
            history=[],
            model_name=model1,
            system_prompt=model1_prompt
        ):
            model1_message += chunk
        
        # 結果を返す
        yield json.dumps({
            'speaker': 'model1',
            'model': model1,
            'message': model1_message
        }, ensure_ascii=False)
        
        # 履歴に保存
        self.session_service.add_watch_message(
            model1_message=model1_message,
            model2_message="",
            model1_name=model1,
            model2_name=model2
        )
    
    async def continue_watch_conversation(self) -> AsyncGenerator[str, None]:
        """
        観戦モードで次の会話を生成
        
        Yields:
            str: 会話の内容（JSON形式）
        """
        # 現在の設定を取得
        watch_models = self.session_service.get_watch_models()
        topic = self.session_service.get_watch_topic()
        history = self.session_service.get_watch_history()
        
        if not topic or not history:
            yield json.dumps({
                'error': '会話が開始されていません'
            }, ensure_ascii=False)
            return
        
        # 最後の会話を取得
        last_entry = history[-1]
        
        # 会話履歴を構築（交互に話す形式）
        conversation_history = []
        for entry in history:
            if entry['model1']['message']:
                conversation_history.append({
                    'human': 'model1',
                    'ai': entry['model1']['message']
                })
            if entry['model2']['message']:
                conversation_history.append({
                    'human': 'model2',
                    'ai': entry['model2']['message']
                })
        
        # システムプロンプト
        base_prompt = f"""あなたは職場の同僚です。
今、同僚と「{topic}」について雑談をしています。
自然で親しみやすい会話を心がけ、相手の話に興味を示しながら会話を続けてください。
返答は簡潔にし、会話が続くような内容にしてください。"""
        
        # 次の話者を決定
        if last_entry['model2']['message']:
            # Model1の番
            next_model = watch_models['model1']
            speaker = 'model1'
            prompt = f"{base_prompt}\n\n相手の発言に対して自然に返答してください。"
            last_message = last_entry['model2']['message']
        else:
            # Model2の番
            next_model = watch_models['model2']
            speaker = 'model2'
            prompt = f"{base_prompt}\n\n相手の発言に対して自然に返答してください。"
            last_message = last_entry['model1']['message']
        
        # レスポンスを生成
        response_message = ""
        async for chunk in self.llm_service.stream_chat_response(
            message=last_message,
            history=conversation_history[:-1],  # 最後のメッセージは含めない
            model_name=next_model,
            system_prompt=prompt
        ):
            response_message += chunk
        
        # 結果を返す
        yield json.dumps({
            'speaker': speaker,
            'model': next_model,
            'message': response_message
        }, ensure_ascii=False)
        
        # 履歴を更新
        if speaker == 'model1':
            self.session_service.add_watch_message(
                model1_message=response_message,
                model2_message="",
                model1_name=next_model,
                model2_name=watch_models['model2']
            )
        else:
            # 既存のエントリを更新する必要がある
            history[-1]['model2']['message'] = response_message
    
    async def generate_chat_feedback(self, max_messages: int = 10) -> str:
        """
        雑談練習のフィードバックを生成
        
        Args:
            max_messages: 分析する最大メッセージ数
            
        Returns:
            str: フィードバックテキスト
        """
        # 会話履歴を取得
        chat_history = self.session_service.get_chat_history()
        
        if not chat_history:
            return "まだ会話がありません。雑談を始めてみましょう！"
        
        # 最新のメッセージを分析
        recent_history = chat_history[-max_messages:] if len(chat_history) > max_messages else chat_history
        
        # 会話内容を整形
        conversation_text = "\n".join([
            f"あなた: {entry['human']}\n相手: {entry['ai']}"
            for entry in recent_history
        ])
        
        # フィードバックを生成
        feedback_prompt = f"""以下の職場での雑談を分析して、建設的なフィードバックを提供してください。

会話内容：
{conversation_text}

以下の観点でフィードバックをお願いします：
1. 話題の選び方と展開
2. 相手への配慮と共感
3. 職場での適切さ
4. 改善できる点

フィードバックは具体的で実践的なアドバイスを含め、{MAX_FEEDBACK_LENGTH}文字以内でまとめてください。"""
        
        # LLMでフィードバックを生成
        feedback = self.llm_service.invoke_sync(
            messages_or_prompt=feedback_prompt,
            model_name=self.session_service.get_current_model()
        )
        
        # 文字数制限
        if len(feedback) > MAX_FEEDBACK_LENGTH:
            feedback = feedback[:MAX_FEEDBACK_LENGTH-3] + "..."
        
        return feedback
    
    async def generate_scenario_feedback(self, scenario_id: str, max_messages: int = 10) -> str:
        """
        シナリオ練習のフィードバックを生成
        
        Args:
            scenario_id: シナリオID
            max_messages: 分析する最大メッセージ数
            
        Returns:
            str: フィードバックテキスト
        """
        # シナリオと履歴を取得
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            return "シナリオが見つかりません。"
        
        scenario_history = self.session_service.get_scenario_history(scenario_id)
        
        if not scenario_history:
            return "まだ会話がありません。シナリオを始めてみましょう！"
        
        # 最新のメッセージを分析
        recent_history = scenario_history[-max_messages:] if len(scenario_history) > max_messages else scenario_history
        
        # 会話内容を整形
        conversation_text = "\n".join([
            f"あなた: {entry['human']}\n{scenario['character']['name']}: {entry['ai']}"
            for entry in recent_history
        ])
        
        # フィードバックポイントを含める
        feedback_points = "\n".join([f"- {point}" for point in scenario.get('feedback_points', [])])
        
        # フィードバックを生成
        feedback_prompt = f"""以下のロールプレイシナリオでの会話を分析して、建設的なフィードバックを提供してください。

シナリオ: {scenario['title']}
状況: {scenario['situation']}
あなたの役割: {scenario.get('your_role', 'プレイヤー')}

会話内容：
{conversation_text}

評価ポイント：
{feedback_points}

以下の観点でフィードバックをお願いします：
1. シナリオの目的に対する達成度
2. コミュニケーションの適切さ
3. 良かった点
4. 改善できる点
5. 次回への具体的なアドバイス

フィードバックは具体的で実践的なアドバイスを含め、{MAX_FEEDBACK_LENGTH}文字以内でまとめてください。"""
        
        # LLMでフィードバックを生成
        feedback = self.llm_service.invoke_sync(
            messages_or_prompt=feedback_prompt,
            model_name=self.session_service.get_current_model()
        )
        
        # 文字数制限
        if len(feedback) > MAX_FEEDBACK_LENGTH:
            feedback = feedback[:MAX_FEEDBACK_LENGTH-3] + "..."
        
        # 学習記録を追加
        self.session_service.add_learning_record(
            activity_type='scenario',
            scenario_id=scenario_id,
            feedback={'generated_feedback': feedback}
        )
        
        return feedback
    
    def get_recommended_voice(self, emotion: Optional[str] = None) -> str:
        """
        感情に基づいて推奨音声を取得
        
        Args:
            emotion: 感情（happy, sad, angry など）
            
        Returns:
            str: 推奨音声名
        """
        if emotion and emotion in EMOTION_VOICE_MAPPING:
            return EMOTION_VOICE_MAPPING[emotion]
        
        return self.session_service.get_current_voice()
    
    def validate_message(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        メッセージの検証
        
        Args:
            message: 検証するメッセージ
            
        Returns:
            Tuple[bool, Optional[str]]: (有効かどうか, エラーメッセージ)
        """
        if not message:
            return False, "メッセージを入力してください。"
        
        if len(message) > MAX_MESSAGE_LENGTH:
            return False, f"メッセージは{MAX_MESSAGE_LENGTH}文字以内で入力してください。"
        
        # 不適切な内容のチェック（簡易版）
        inappropriate_words = ['死ね', '殺す', 'ばか', 'あほ']
        for word in inappropriate_words:
            if word in message:
                return False, "不適切な表現が含まれています。"
        
        return True, None