"""シナリオサービス"""
import os
import yaml
from typing import Dict, Any, Optional

from flask import current_app

from .llm_service import LLMService
from .session_service import SessionService


class ScenarioService:
    """シナリオ管理サービス"""
    
    def __init__(self):
        self.llm_service = LLMService()
        self.session_service = SessionService()
        self._scenarios: Dict[str, Any] = {}
        self._load_scenarios()
    
    def _load_scenarios(self) -> None:
        """シナリオデータを読み込む"""
        # シナリオディレクトリのパス
        scenarios_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "scenarios",
            "data"
        )
        
        if not os.path.exists(scenarios_dir):
            current_app.logger.warning(f"Scenarios directory not found: {scenarios_dir}")
            return
        
        # YAMLファイルを読み込む
        for filename in os.listdir(scenarios_dir):
            if filename.endswith((".yaml", ".yml")):
                scenario_id = filename.rsplit(".", 1)[0]
                filepath = os.path.join(scenarios_dir, filename)
                
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._scenarios[scenario_id] = yaml.safe_load(f)
                except Exception as e:
                    current_app.logger.error(f"Failed to load scenario {filename}: {e}")
        
        current_app.logger.info(f"Loaded {len(self._scenarios)} scenarios")
    
    def get_all_scenarios(self) -> Dict[str, Any]:
        """全シナリオを取得
        
        Returns:
            シナリオ辞書
        """
        return self._scenarios.copy()
    
    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """特定のシナリオを取得
        
        Args:
            scenario_id: シナリオID
            
        Returns:
            シナリオデータ
        """
        return self._scenarios.get(scenario_id)
    
    def exists(self, scenario_id: str) -> bool:
        """シナリオが存在するか確認
        
        Args:
            scenario_id: シナリオID
            
        Returns:
            存在する場合True
        """
        return scenario_id in self._scenarios
    
    def process_message(
        self,
        scenario_id: str,
        message: str,
        model_name: Optional[str] = None
    ) -> str:
        """シナリオメッセージを処理
        
        Args:
            scenario_id: シナリオID
            message: ユーザーメッセージ
            model_name: 使用するモデル名
            
        Returns:
            生成された応答
        """
        scenario = self.get_scenario(scenario_id)
        if scenario is None:
            return "シナリオが見つかりません。"
        
        # セッションIDを取得
        session_id = self.session_service.get_or_create_session()
        
        # メッセージを履歴に追加
        self.session_service.add_message(
            session_id=session_id,
            role="user",
            content=message,
            metadata={"scenario_id": scenario_id}
        )
        
        # プロンプトの構築
        prompt = self._build_scenario_prompt(scenario, message)
        
        # 応答を生成
        response = self.llm_service.generate_response(
            prompt=prompt,
            model_name=model_name
        )
        
        # 応答を履歴に追加
        self.session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=response,
            metadata={"scenario_id": scenario_id}
        )
        
        return response
    
    def _build_scenario_prompt(
        self,
        scenario: Dict[str, Any],
        message: str
    ) -> str:
        """シナリオプロンプトを構築
        
        Args:
            scenario: シナリオデータ
            message: ユーザーメッセージ
            
        Returns:
            プロンプト文字列
        """
        # シナリオ情報の取得
        title = scenario.get("title", "")
        description = scenario.get("description", "")
        your_role = scenario.get("your_role", "")
        partner_role = scenario.get("partner_role", "")
        situation = scenario.get("situation", "")
        
        # プロンプトの構築
        prompt = f"""# シナリオ: {title}

## 状況説明
{description}

## 役割設定
- あなたの役割: {partner_role}
- 相手の役割: {your_role}

## 詳細な状況
{situation}

## 会話
相手: {message}

あなた（{partner_role}として応答してください）:"""
        
        return prompt
    
    def generate_feedback(self, scenario_id: str) -> str:
        """シナリオのフィードバックを生成
        
        Args:
            scenario_id: シナリオID
            
        Returns:
            フィードバックテキスト
        """
        scenario = self.get_scenario(scenario_id)
        if scenario is None:
            return "シナリオが見つかりません。"
        
        # セッションIDを取得
        session_id = self.session_service.get_or_create_session()
        
        # 会話履歴を取得
        messages = self.session_service.get_messages(session_id)
        
        # シナリオに関連するメッセージのみ抽出
        scenario_messages = [
            msg for msg in messages
            if msg.get("metadata", {}).get("scenario_id") == scenario_id
        ]
        
        if not scenario_messages:
            return "まだ会話が行われていません。"
        
        # フィードバックプロンプトの構築
        prompt = self._build_feedback_prompt(scenario, scenario_messages)
        
        # フィードバックを生成
        feedback = self.llm_service.generate_response(prompt=prompt)
        
        return feedback
    
    def _build_feedback_prompt(
        self,
        scenario: Dict[str, Any],
        messages: list
    ) -> str:
        """フィードバックプロンプトを構築
        
        Args:
            scenario: シナリオデータ
            messages: メッセージ履歴
            
        Returns:
            プロンプト文字列
        """
        # 会話履歴を整形
        conversation = []
        for msg in messages:
            role = "ユーザー" if msg["role"] == "user" else "相手"
            conversation.append(f"{role}: {msg['content']}")
        
        conversation_text = "\n".join(conversation)
        
        # フィードバックポイントの取得
        feedback_points = scenario.get("feedback_points", [])
        points_text = "\n".join([f"- {point}" for point in feedback_points])
        
        prompt = f"""以下のシナリオでの会話について、建設的なフィードバックを提供してください。

## シナリオ: {scenario.get('title', '')}
{scenario.get('description', '')}

## 会話内容
{conversation_text}

## フィードバックポイント
{points_text}

上記のポイントを踏まえて、ユーザーのコミュニケーションについて具体的で建設的なフィードバックを提供してください。
良かった点と改善できる点の両方を含めてください。"""
        
        return prompt