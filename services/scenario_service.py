"""
シナリオ管理サービス
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage

from errors import ValidationError


class ScenarioService:
    """シナリオ関連の操作を管理するサービスクラス"""
    
    def format_messages_for_scenario(
        self,
        scenario: Dict[str, Any],
        history: List[Dict[str, Any]],
        current_message: str
    ) -> List[BaseMessage]:
        """シナリオ用にメッセージをフォーマット"""
        messages = []
        
        # シナリオ固有のシステムプロンプト
        system_prompt = f"""あなたは{scenario.get('partner_role', '職場の同僚')}です。
        
シナリオ: {scenario.get('title', '')}
状況: {scenario.get('situation', '')}
あなたの役割の詳細: {scenario.get('partner_personality', '')}

{scenario.get('additional_context', '')}

相手との会話では、以下の点に注意してください：
- 設定された役割と性格に忠実に振る舞う
- 現実的で自然な反応をする
- 相手の対応に応じて適切に反応する
- 必要に応じて感情を表現する"""
        
        messages.append(SystemMessage(content=system_prompt))
        
        # 初期プロンプトがある場合
        if history == [] and scenario.get('initial_message'):
            messages.append(SystemMessage(content=scenario['initial_message']))
        
        # 履歴からメッセージを追加
        for entry in history:
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            elif entry["role"] == "assistant":
                messages.append(AIMessage(content=entry["content"]))
        
        # 現在のメッセージを追加
        messages.append(HumanMessage(content=current_message))
        
        return messages
    
    def generate_scenario_feedback(
        self,
        llm: Any,
        scenario: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> str:
        """シナリオ練習のフィードバックを生成"""
        # 会話履歴をフォーマット
        conversation_text = self._format_scenario_conversation(history)
        
        # フィードバックポイントを取得
        feedback_points = scenario.get('feedback_points', [])
        feedback_points_text = "\n".join([f"- {point}" for point in feedback_points])
        
        # 学習ポイントを取得
        learning_points = scenario.get('learning_points', [])
        learning_points_text = "\n".join([f"- {point}" for point in learning_points])
        
        prompt = f"""以下のシナリオ練習を分析し、詳細なフィードバックを提供してください。

シナリオ: {scenario.get('title', '')}
状況: {scenario.get('situation', '')}
難易度: {scenario.get('difficulty', '中級')}

学習ポイント:
{learning_points_text}

会話内容:
{conversation_text}

以下の観点から評価してください：
{feedback_points_text}

フィードバックには以下を含めてください：
1. 総合評価（100点満点）
2. 良かった点（具体例を含めて3-4点）
3. 改善が必要な点（具体的な改善案を含めて2-3点）
4. 次のステップの提案

評価は建設的で励みになるトーンで、
具体的な例文や代替案を含めて提供してください。"""
        
        messages = [SystemMessage(content=prompt)]
        
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            response = llm_service.create_and_get_response(llm, messages)
            return response
        except Exception as e:
            return f"フィードバックの生成中にエラーが発生しました: {str(e)}"
    
    def generate_assist_message(
        self,
        llm: Any,
        scenario: Dict[str, Any],
        history: List[Dict[str, Any]]
    ) -> str:
        """アシストメッセージを生成"""
        # 最新の会話内容を取得
        recent_context = self._get_recent_context(history, 3)
        
        # ヒントポイントを取得
        hint_points = scenario.get('hint_points', [])
        hint_text = "\n".join([f"- {hint}" for hint in hint_points])
        
        prompt = f"""あなたはコミュニケーションコーチです。
以下のシナリオで練習中の人にアドバイスを提供してください。

シナリオ: {scenario.get('title', '')}
状況: {scenario.get('situation', '')}

最近の会話:
{recent_context}

ヒントポイント:
{hint_text}

現在の状況を踏まえて、次にどのような対応をすると良いか、
具体的で実践的なアドバイスを2-3つ提供してください。
アドバイスは簡潔で、すぐに実行できるものにしてください。"""
        
        messages = [SystemMessage(content=prompt)]
        
        try:
            from services.llm_service import LLMService
            llm_service = LLMService()
            response = llm_service.create_and_get_response(llm, messages)
            return response
        except Exception as e:
            return "申し訳ありません。アシストメッセージの生成中にエラーが発生しました。"
    
    def update_feedback_with_strength_analysis(
        self,
        feedback_response: str,
        strength_analysis: Dict[str, Any]
    ) -> str:
        """強み分析結果をフィードバックに統合"""
        if not strength_analysis or "error" in strength_analysis:
            return feedback_response
        
        # 強み分析のサマリーを作成
        strengths_summary = self._format_strength_summary(strength_analysis)
        
        # フィードバックに強み分析を追加
        enhanced_feedback = f"""{feedback_response}

【コミュニケーション強度分析】
{strengths_summary}"""
        
        return enhanced_feedback
    
    def _format_scenario_conversation(self, history: List[Dict[str, Any]]) -> str:
        """シナリオ会話履歴をフォーマット"""
        formatted_lines = []
        
        for i, entry in enumerate(history):
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            
            if role == "user":
                formatted_lines.append(f"[{i+1}] あなた: {content}")
            elif role == "assistant":
                formatted_lines.append(f"[{i+1}] 相手: {content}")
        
        return "\n".join(formatted_lines)
    
    def _get_recent_context(self, history: List[Dict[str, Any]], count: int = 3) -> str:
        """最近の会話コンテキストを取得"""
        recent_history = history[-count*2:] if len(history) > count*2 else history
        return self._format_scenario_conversation(recent_history)
    
    def _format_strength_summary(self, strength_analysis: Dict[str, Any]) -> str:
        """強み分析のサマリーをフォーマット"""
        summary_lines = []
        
        # トップ強み
        if "top_strengths" in strength_analysis:
            summary_lines.append("◆ あなたの強み:")
            for strength in strength_analysis["top_strengths"]:
                summary_lines.append(f"  • {strength['name']}: {strength['score']}/10")
                summary_lines.append(f"    {strength.get('description', '')}")
        
        # 改善エリア
        if "improvement_areas" in strength_analysis:
            summary_lines.append("\n◆ 成長の機会:")
            for area in strength_analysis["improvement_areas"]:
                summary_lines.append(f"  • {area['name']}: {area['score']}/10")
                summary_lines.append(f"    {area.get('suggestion', '')}")
        
        # 全体スコア
        if "overall_score" in strength_analysis:
            summary_lines.append(f"\n◆ 総合スコア: {strength_analysis['overall_score']}/100")
        
        return "\n".join(summary_lines)