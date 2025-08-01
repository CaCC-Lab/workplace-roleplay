"""
シナリオ機能サービス
職場シナリオのロールプレイ処理を担当
"""
from typing import Dict, Any, Generator, Optional
import json
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from services.llm_service import LLMService
from services.session_service import SessionService
from scenarios import load_scenarios
from errors import ValidationError, NotFoundError, ExternalAPIError
from utils.security import SecurityUtils


class ScenarioService:
    """シナリオ機能のためのサービスクラス"""
    
    # シナリオシステムプロンプトテンプレート
    SCENARIO_SYSTEM_PROMPT = """あなたは「{character_name}」という{character_role}役を演じています。

【キャラクター設定】
{character_description}

【シナリオ状況】
{scenario_context}

【あなたの演技指針】
1. {character_name}の性格や立場に基づいて、自然な反応をしてください
2. ユーザーの発言に対して、現実的で職場にふさわしい応答を心がけてください
3. 必要に応じて、ユーザーの成長を促すような反応も含めてください
4. 会話は日本語で、職場での実際の会話のように自然に進めてください

重要: あなたは{character_name}として振る舞い、ユーザーとロールプレイを行います。"""
    
    @staticmethod
    def get_scenario(scenario_id: str) -> Dict[str, Any]:
        """
        シナリオ情報を取得
        
        Args:
            scenario_id: シナリオID
            
        Returns:
            シナリオ情報
            
        Raises:
            NotFoundError: シナリオが見つからない場合
        """
        scenarios = load_scenarios()
        
        if scenario_id not in scenarios:
            raise NotFoundError("シナリオ", scenario_id)
        
        return scenarios[scenario_id]
    
    @staticmethod
    def handle_scenario_message(scenario_id: str, message: str, 
                              model_name: str = None) -> Generator[str, None, None]:
        """
        シナリオメッセージを処理してストリーミングレスポンスを生成
        
        Args:
            scenario_id: シナリオID
            message: ユーザーのメッセージ
            model_name: 使用するモデル名
            
        Yields:
            SSE形式のレスポンスチャンク
            
        Raises:
            ValidationError: 入力が無効な場合
            NotFoundError: シナリオが見つからない場合
            ExternalAPIError: LLM API呼び出しに失敗した場合
        """
        # 入力検証
        if not scenario_id:
            raise ValidationError("シナリオIDが指定されていません", field="scenario_id")
        
        if not message or not message.strip():
            raise ValidationError("メッセージを入力してください", field="message")
        
        # XSS対策
        message = SecurityUtils.sanitize_input(message)
        
        # シナリオの取得
        scenario = ScenarioService.get_scenario(scenario_id)
        
        # モデル名の取得
        if not model_name:
            model_name = SessionService.get_session_data('selected_model', 'gemini-1.5-flash')
        
        # LLMの初期化
        llm = LLMService.create_llm(model_name)
        
        # シナリオ履歴の初期化
        SessionService.initialize_session_history('scenario_history', scenario_id)
        
        # 開始時刻の設定
        SessionService.set_session_start_time('scenario', scenario_id)
        
        # 履歴の取得
        history = SessionService.get_session_history('scenario_history', scenario_id)
        
        # システムプロンプトの作成
        system_prompt = ScenarioService.SCENARIO_SYSTEM_PROMPT.format(
            character_name=scenario['character']['name'],
            character_role=scenario['character']['role'],
            character_description=scenario['character']['personality'],
            scenario_context=scenario['situation']
        )
        
        # プロンプトの構築
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
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
            SessionService.add_to_session_history('scenario_history', {
                'user': message,
                'assistant': assistant_response,
                'timestamp': datetime.now().isoformat(),
                'model': model_name,
                'character': scenario['character']['name']
            }, sub_key=scenario_id)
            
            # 完了メッセージ
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            print(f"Scenario streaming error: {str(e)}")
            # エラーメッセージをSSE形式で送信
            error_data = {
                'type': 'error',
                'message': 'メッセージの生成中にエラーが発生しました'
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            raise ExternalAPIError("Gemini", "シナリオ応答の生成に失敗しました", str(e))
    
    @staticmethod
    def generate_scenario_feedback(scenario_id: str) -> Dict[str, Any]:
        """
        シナリオ練習のフィードバックを生成
        
        Args:
            scenario_id: シナリオID
            
        Returns:
            フィードバック情報
        """
        # シナリオ情報の取得
        scenario = ScenarioService.get_scenario(scenario_id)
        
        # 履歴の取得
        history = SessionService.get_session_history('scenario_history', scenario_id)
        
        if not history:
            return {
                'feedback': 'まだこのシナリオでの練習履歴がありません。',
                'scenario_title': scenario['title']
            }
        
        # フィードバック生成用のプロンプト
        feedback_prompt = f"""
以下は「{scenario['title']}」というシナリオでの練習記録です。

シナリオ説明: {scenario['description']}
練習のポイント: {', '.join(scenario.get('learning_points', []))}

会話履歴:
"""
        
        # 会話履歴を追加
        for entry in history:
            if 'user' in entry:
                feedback_prompt += f"ユーザー: {entry['user']}\n"
            if 'assistant' in entry:
                feedback_prompt += f"{entry.get('character', 'AI')}: {entry['assistant']}\n"
        
        feedback_prompt += f"""
以下の評価基準に基づいて、ユーザーのパフォーマンスについて
具体的で建設的なフィードバックを300文字程度で生成してください:

評価ポイント:
{chr(10).join(f"- {point}" for point in scenario.get('feedback_points', []))}

フィードバックには必ず含めてください:
1. 良かった点（具体的に）
2. 改善できる点（具体的なアドバイスと共に）
3. 次回の練習への励まし
"""
        
        try:
            # フィードバックの生成
            feedback_content, used_model, error = LLMService.try_multiple_models_for_prompt(feedback_prompt)
            
            if error:
                feedback_content = "フィードバックの生成に失敗しました。もう一度お試しください。"
            
            return {
                'feedback': feedback_content,
                'scenario_title': scenario['title'],
                'practice_count': len(history),
                'learning_points': scenario.get('learning_points', []),
                'model': used_model
            }
            
        except Exception as e:
            print(f"Scenario feedback generation error: {str(e)}")
            return {
                'feedback': 'フィードバックの生成中にエラーが発生しました。',
                'scenario_title': scenario['title'],
                'error': str(e)
            }
    
    @staticmethod
    def clear_scenario_history(scenario_id: str = None) -> Dict[str, str]:
        """
        シナリオ履歴をクリア
        
        Args:
            scenario_id: 特定のシナリオIDの履歴のみクリア（省略時は全履歴）
            
        Returns:
            結果メッセージ
        """
        if scenario_id:
            SessionService.clear_session_history('scenario_history', scenario_id)
            message = f'シナリオ {scenario_id} の履歴をクリアしました'
        else:
            SessionService.clear_session_history('scenario_history')
            message = 'すべてのシナリオ履歴をクリアしました'
        
        return {'message': message}
    
    @staticmethod
    def get_initial_message(scenario_id: str) -> Optional[str]:
        """
        シナリオの初期メッセージを取得
        
        Args:
            scenario_id: シナリオID
            
        Returns:
            初期メッセージ（存在する場合）
        """
        scenario = ScenarioService.get_scenario(scenario_id)
        return scenario.get('initial_message')