"""会話サービス"""
from typing import Dict, Any, Optional, Generator
from flask import session
import logging

from .llm_service import LLMService
from .scenario_service import ScenarioService

logger = logging.getLogger(__name__)


class ConversationService:
    """会話管理サービス"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.scenario_service = ScenarioService()
    
    def get_chat_response_stream(
        self,
        message: str,
        model_id: str,
        mode: str = "chat"
    ) -> Generator[str, None, None]:
        """チャット応答をストリーミング形式で取得"""
        try:
            # 会話履歴を取得
            history_key = f"{mode}_history"
            chat_history = session.get(history_key, [])
            
            # プロンプトを構築
            if mode == "chat":
                system_prompt = "あなたは職場での雑談をサポートするアシスタントです。自然で親しみやすい会話を心がけてください。"
            else:
                system_prompt = "あなたは親切で役立つアシスタントです。"
            
            # LLMサービスでストリーミング応答を生成
            stream = self.llm_service.generate_stream(
                prompt=message,
                system_prompt=system_prompt,
                chat_history=chat_history,
                model_id=model_id
            )
            
            # 応答を蓄積
            full_response = ""
            for chunk in stream:
                full_response += chunk
                yield chunk
            
            # 会話履歴を更新
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": full_response})
            
            # 履歴を保存（最新の10件のみ保持）
            session[history_key] = chat_history[-20:]  # ユーザーとアシスタントで10往復分
            
        except Exception as e:
            logger.error(f"Chat streaming error: {str(e)}")
            yield f"エラーが発生しました: {str(e)}"
    
    def get_scenario_response_stream(
        self,
        message: str,
        scenario_id: str,
        model_id: str,
        is_initial: bool = False
    ) -> Generator[str, None, None]:
        """シナリオ応答をストリーミング形式で取得"""
        try:
            # シナリオ情報を取得
            scenario = self.scenario_service.get_scenario(scenario_id)
            if not scenario:
                yield "シナリオが見つかりません。"
                return
            
            # 会話履歴を取得
            history_key = f"scenario_{scenario_id}_history"
            chat_history = session.get(history_key, [])
            
            if is_initial:
                # 初回メッセージの場合
                # プリロードキャッシュから取得を試みる
                from app import _scenario_initial_cache
                
                if scenario_id in _scenario_initial_cache:
                    initial_message = _scenario_initial_cache[scenario_id]
                else:
                    # キャッシュにない場合は通常の方法で取得
                    initial_message = scenario.get("initial_message", "")
                    if not initial_message:
                        character_setting = scenario.get("character_setting", {})
                        initial_message = character_setting.get("initial_approach", "こんにちは。どのようなご用件でしょうか？")
                
                # 初回メッセージをそのまま返す（高速）
                for char in initial_message:
                    yield char
                
                # 履歴に追加
                chat_history.append({"role": "assistant", "content": initial_message})
                session[history_key] = chat_history
                return
            
            # 通常の応答生成
            # より詳細なシステムプロンプトを構築
            character_setting = scenario.get("character_setting", {})
            ai_role = scenario.get("ai_role", "")
            
            system_prompt = f"""あなたは職場でのコミュニケーション練習のためのロールプレイ相手です。

{ai_role}

【キャラクター設定】
- 性格: {character_setting.get('personality', '優しく親しみやすい人物')}
- 話し方: {character_setting.get('speaking_style', '自然で親しみやすい話し方')}
- 状況: {character_setting.get('situation', '職場での日常的な場面')}

【重要な指示】
1. 相手（ユーザー）は職場でのコミュニケーションに不安を感じている可能性があります
2. プレッシャーを与えず、相手のペースに合わせて対話してください
3. 短く、わかりやすい応答を心がけてください
4. 相手が返答しやすいように、時には質問を含めてください
5. 日本の職場文化に適した自然な対話を心がけてください

必ず上記の設定に従って、自然で優しい応答を生成してください。"""
            
            # LLMサービスでストリーミング応答を生成
            stream = self.llm_service.generate_stream(
                prompt=message,
                system_prompt=system_prompt,
                chat_history=chat_history,
                model_id=model_id
            )
            
            # 応答を蓄積
            full_response = ""
            for chunk in stream:
                full_response += chunk
                yield chunk
            
            # 会話履歴を更新
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": full_response})
            
            # 履歴を保存
            session[history_key] = chat_history
            
        except Exception as e:
            logger.error(f"Scenario streaming error: {str(e)}")
            yield f"エラーが発生しました: {str(e)}"
    
    def get_chat_feedback(self, mode: str = "chat") -> Dict[str, Any]:
        """チャットのフィードバックを取得"""
        try:
            history_key = f"{mode}_history"
            chat_history = session.get(history_key, [])
            
            if not chat_history:
                return {
                    "success": False,
                    "error": "会話履歴がありません"
                }
            
            # フィードバック生成用のプロンプト
            feedback_prompt = """
            以下の会話履歴を分析して、ユーザーのコミュニケーションスキルについてフィードバックを提供してください。
            
            フィードバックには以下を含めてください：
            1. 良かった点（2-3個）
            2. 改善できる点（2-3個）
            3. 具体的なアドバイス（1-2個）
            
            会話履歴：
            """
            
            # 会話履歴を整形
            for msg in chat_history[-10:]:  # 最新の10メッセージ
                role = "ユーザー" if msg["role"] == "user" else "相手"
                feedback_prompt += f"\n{role}: {msg['content']}"
            
            # フィードバックを生成
            feedback = self.llm_service.generate(
                prompt=feedback_prompt,
                model_id=session.get("selected_models", {}).get(mode, "gemini/gemini-1.5-flash")
            )
            
            return {
                "success": True,
                "feedback": feedback
            }
            
        except Exception as e:
            logger.error(f"Get chat feedback error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_history(self, mode: str = "chat", scenario_id: Optional[str] = None) -> None:
        """会話履歴をクリア"""
        if scenario_id:
            history_key = f"scenario_{scenario_id}_history"
        else:
            history_key = f"{mode}_history"
        
        if history_key in session:
            session.pop(history_key)