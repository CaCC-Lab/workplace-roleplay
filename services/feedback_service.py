"""
Feedback service for the workplace-roleplay application.
Handles feedback generation business logic.
"""

from typing import Any, Dict, Optional, Tuple

from google.api_core.exceptions import ResourceExhausted
from langchain_core.messages import HumanMessage
from services.scenario_service import get_scenario_service

from config import get_cached_config
from utils.helpers import (
    format_conversation_history_for_feedback,
    get_partner_description,
    get_situation_description,
)


class FeedbackService:
    """フィードバック生成関連のビジネスロジックを処理するサービス"""

    def build_chat_feedback_prompt(self, history: list, partner_type: str, situation: str) -> str:
        """
        雑談練習用のフィードバックプロンプトを構築

        Args:
            history: 会話履歴
            partner_type: 相手のタイプ
            situation: 状況

        Returns:
            str: フィードバックプロンプト
        """
        feedback_prompt = f"""【雑談スキル評価】職場コミュニケーション向上支援

# 指示: 必ずユーザーの視点に立ち、ユーザーが明日から使えるような、実践的で勇気づけられるアドバイスを生成してください。

コンテキスト分析：
👥 対話相手：{get_partner_description(partner_type)}
🏢 状況設定：{get_situation_description(situation)}
💬 会話履歴：
{format_conversation_history_for_feedback(history)}

※最重要指示: ユーザーの発言・行動のみを評価してください。AIの行動は評価対象ではありません。
評価対象：「あなた」（ユーザー）の発言・選択・タイミング・配慮のみ

🎯 ユーザースキル評価システム：
AIの行動・対応・努力・理解度は一切評価しないこと。
📈 雑談効果スコア（/100点）：あなたの関係構築スキル
🌟 コミュニケーション強み（2点）：
• 「あなたの○○が自然だった」「あなたの共感表現が良かった」の形式で評価
❗ 成長ポイント（2点）：
• 「あなたがもっと○○に配慮すると良い」「あなたの話題選択を○○すると良い」の形式
💪 即実践アクション（1つ）：「明日の雑談であなたが○○を試してみる」形式

評価視点：あなたの相手理解力・感情配慮・関係構築能力・場面適応性のみ評価
※職場での良好な人間関係構築に役立つフィードバックを提供"""
        return feedback_prompt

    def build_scenario_feedback_prompt(
        self,
        history: list,
        scenario_data: Dict[str, Any],
        is_reverse_role: bool = False,
    ) -> str:
        """
        シナリオ練習用のフィードバックプロンプトを構築

        Args:
            history: 会話履歴
            scenario_data: シナリオデータ
            is_reverse_role: リバースロールの場合True

        Returns:
            str: フィードバックプロンプト
        """
        scenario_service = get_scenario_service()
        user_role = scenario_service.get_user_role(scenario_data, is_reverse_role)

        if is_reverse_role:
            feedback_prompt = f"""【パワハラ防止評価】上司役コミュニケーション分析

シナリオ：{scenario_data.get("title", "上司対応練習")}
会話履歴：
{format_conversation_history_for_feedback(history)}

※最重要指示: ユーザーの発言・行動のみを評価してください。AIの行動は評価対象ではありません。

評価基準（ユーザーのみ対象）：
🎯 基本スコア（/100点）：権力バランス配慮度
📈 コミュニケーション質：
• 良い点（具体例2点）
• 改善点（課題2点）
🛠️ 即実行可能アドバイス：
• 明日から使える改善策（1つ）
• 適切な上司言動例（1つ）"""
        else:
            feedback_prompt = f"""【職場コミュニケーション評価】スキル向上フィードバック

シナリオ分析：{scenario_data.get("title", "コミュニケーション練習")}
ユーザー役割：{user_role}
会話履歴：
{format_conversation_history_for_feedback(history)}

※最重要指示: ユーザーの発言・行動のみを評価してください。AIの行動は評価対象ではありません。

🔍 ユーザーコミュニケーション分析:
📊 総合スコア（/100点）：コミュニケーション効果度
✅ 優秀ポイント（2つ）
⚠️ 成長機会（2つ）
💡 実践アクション"""

        return feedback_prompt

    def try_multiple_models_for_prompt(
        self, prompt: str, preferred_model: Optional[str] = None
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Geminiモデルを使用してプロンプトに対する応答を取得する

        Args:
            prompt: プロンプト
            preferred_model: 優先するモデル名（オプション）

        Returns:
            Tuple[str, Optional[str], Optional[str]]:
            (コンテンツ, 使用モデル, エラーメッセージ)
        """
        from app import create_model_and_get_response

        content = None
        used_model = None
        error_msg = None

        try:
            # 利用可能なモデルを取得
            config = get_cached_config()
            import google.generativeai as genai

            try:
                genai.configure(api_key=config.GOOGLE_API_KEY)
                models = genai.list_models()
                gemini_models = [f"gemini/{m.name.split('/')[-1]}" for m in models if "gemini" in m.name.lower()]
            except Exception:
                gemini_models = ["gemini/gemini-1.5-flash", "gemini/gemini-1.5-pro"]

            if preferred_model:
                # Ollama Cloud 等、Gemini 以外のプロバイダは直接利用（Gemini リスト検証をスキップ）
                if preferred_model.startswith("ollama/"):
                    model_name = preferred_model
                else:
                    if not preferred_model.startswith("gemini/"):
                        normalized_model = f"gemini/{preferred_model}"
                    else:
                        normalized_model = preferred_model

                    if normalized_model in gemini_models:
                        model_name = normalized_model
                    else:
                        flash_models = [m for m in gemini_models if "flash" in m.lower()]
                        model_name = flash_models[0] if flash_models else gemini_models[0] if gemini_models else None
            elif gemini_models:
                flash_models = [m for m in gemini_models if "flash" in m.lower()]
                model_name = flash_models[0] if flash_models else gemini_models[0]
            else:
                model_name = None

            if not model_name:
                error_msg = "No Gemini models available"
                return "", None, error_msg

            messages = [HumanMessage(content=prompt)]
            content_result = create_model_and_get_response(model_name, messages)

            content = str(content_result) if content_result is not None else ""
            used_model = model_name
            return content, used_model, None

        except ResourceExhausted:
            error_msg = "RATE_LIMIT_EXCEEDED"
        except Exception as gemini_error:
            error_msg = str(gemini_error)
            if any(keyword in str(gemini_error).lower() for keyword in ["rate limit", "quota", "429"]):
                error_msg = "RATE_LIMIT_EXCEEDED"

        return "", None, error_msg or "Gemini model error occurred"

    def update_feedback_with_strength_analysis(
        self,
        feedback_response: Dict[str, Any],
        session_type: str,
        scenario_id: Optional[str] = None,
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
            from routes.strength_routes import (
                update_feedback_with_strength_analysis as _update,
            )

            return _update(feedback_response, session_type, scenario_id)
        except Exception as e:
            print(f"Error adding strength analysis to feedback: {str(e)}")
            return feedback_response


# グローバルインスタンス
_feedback_service: Optional[FeedbackService] = None


def get_feedback_service() -> FeedbackService:
    """FeedbackServiceのシングルトンインスタンスを取得"""
    global _feedback_service
    if _feedback_service is None:
        _feedback_service = FeedbackService()
    return _feedback_service
