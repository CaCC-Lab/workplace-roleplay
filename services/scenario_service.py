"""
Scenario service for the workplace-roleplay application.
Handles scenario-related business logic.
"""

from typing import Any, Dict, Optional, Tuple

from scenarios import load_scenarios
from scenarios.category_manager import (
    get_categorized_scenarios as get_categorized_scenarios_func,
)
from scenarios.category_manager import (
    get_scenario_category_summary,
    is_harassment_scenario,
)


class ScenarioService:
    """シナリオ関連のビジネスロジックを処理するサービス"""

    def __init__(self):
        """サービスを初期化"""
        self._scenarios = None
        self._load_scenarios()

    def _load_scenarios(self):
        """シナリオをロード"""
        try:
            self._scenarios = load_scenarios()
            print(f"✅ ScenarioService: シナリオロード成功: {len(self._scenarios)}個")
        except Exception as e:
            print(f"❌ ScenarioService: シナリオロードエラー: {e}")
            self._scenarios = {}

    def get_all_scenarios(self) -> Dict[str, Any]:
        """
        すべてのシナリオを取得

        Returns:
            Dict[str, Any]: シナリオIDをキーとするシナリオデータの辞書
        """
        return self._scenarios.copy() if self._scenarios else {}

    def get_scenario_by_id(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """
        指定されたIDのシナリオを取得

        Args:
            scenario_id: シナリオID

        Returns:
            Optional[Dict[str, Any]]: シナリオデータ、存在しない場合はNone
        """
        if not self._scenarios:
            return None
        return self._scenarios.get(scenario_id)

    def get_categorized_scenarios(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        シナリオをカテゴリ別に分類

        Returns:
            Tuple[Dict[str, Any], Dict[str, Any]]:
            (通常シナリオ, ハラスメント防止シナリオ)
        """
        return get_categorized_scenarios_func()

    def is_harassment_scenario(self, scenario_id: str) -> bool:
        """
        指定されたシナリオがハラスメント防止シナリオかどうかを判定

        Args:
            scenario_id: シナリオID

        Returns:
            bool: ハラスメント防止シナリオの場合True
        """
        return is_harassment_scenario(scenario_id)

    def get_scenario_category_summary(self) -> Dict[str, Any]:
        """
        シナリオカテゴリのサマリーを取得

        Returns:
            Dict[str, Any]: カテゴリ別のシナリオ情報
        """
        return get_scenario_category_summary()

    def build_system_prompt(self, scenario_data: Dict[str, Any], is_reverse_role: bool = False) -> str:
        """
        シナリオ用のシステムプロンプトを構築

        Args:
            scenario_data: シナリオデータ
            is_reverse_role: リバースロール（上司役）の場合True

        Returns:
            str: システムプロンプト
        """
        if is_reverse_role:
            return scenario_data.get("system_prompt", "")

        character_setting = scenario_data.get("character_setting", {})
        personality = character_setting.get("personality", "未設定")
        speaking_style = character_setting.get("speaking_style", "未設定")
        situation = character_setting.get("situation", "未設定")

        role_info = scenario_data.get("role_info", "AI,不明")
        role_name = role_info.split("、")[0].replace("AIは", "")

        system_prompt = f"""
# ロールプレイの基本設定
あなたは{role_name}として振る舞います。

## キャラクター詳細
- 性格: {personality}
- 話し方: {speaking_style}
- 現在の状況: {situation}

## 演技の指針
1. 一貫性：設定された役柄を終始一貫して演じ続けること
2. 自然さ：指定された話し方を守りながら、不自然にならないよう注意
3. 反応の適切さ：相手の発言内容に対する適切な理解と反応
4. 会話の自然な展開：一方的な会話を避け、適度な質問や確認を含める

## 出力形式（重要）
- セリフのみを出力してください
- 動作描写やト書き（例：「（うつむきながら）」「*ため息をつく*」「【沈黙】」など）は一切含めないでください
- 括弧書きの感情表現や状況説明は禁止です
- 純粋な会話文のみを返してください

## 会話の制約
1. 返答の長さ：1回の発言は3行程度まで
2. 話題の一貫性：急な話題転換を避ける
3. 職場らしさ：敬語と略語を適切に使い分ける

## 現在の文脈
{scenario_data.get("description", "説明なし")}

## 特記事項
- ユーザーの成長を促す反応を心がける
- 極端な否定は避け、建設的な対話を維持
"""
        return system_prompt

    def build_reverse_role_prompt(self, scenario_data: Dict[str, Any]) -> str:
        """
        リバースロール（上司役）用のシステムプロンプトを構築

        Args:
            scenario_data: シナリオデータ

        Returns:
            str: システムプロンプト
        """
        return scenario_data.get("system_prompt", "")

    def get_initial_message(self, scenario_data: Dict[str, Any], is_reverse_role: bool = False) -> Optional[str]:
        """
        シナリオ開始時の初期メッセージを取得

        Args:
            scenario_data: シナリオデータ
            is_reverse_role: リバースロールの場合True

        Returns:
            Optional[str]: 初期メッセージ、不要な場合はNone
        """
        if is_reverse_role:
            initial_context = scenario_data.get("initial_context", "")
            if initial_context:
                return f"【状況】\n{initial_context}\n\n（部下があなたの指示を待っています。上司として最初の声かけをしてください）"
        else:
            initial_approach = scenario_data.get("character_setting", {}).get("initial_approach", "自然に")
            return f"""
最初の声掛けとして、{initial_approach}という設定で話しかけてください。
感情や表情も自然に含めて表現してください。
"""
        return None

    def get_user_role(self, scenario_data: Dict[str, Any], is_reverse_role: bool = False) -> str:
        """
        ユーザーの役割を取得

        Args:
            scenario_data: シナリオデータ
            is_reverse_role: リバースロールの場合True

        Returns:
            str: ユーザーの役割
        """
        if is_reverse_role:
            return scenario_data.get("user_role", "上司")
        else:
            role_info_str = scenario_data.get("role_info", "")
            if not isinstance(role_info_str, str):
                return "不明"
            parts = role_info_str.split("、")
            return parts[1] if len(parts) > 1 else "不明"


# グローバルインスタンス
_scenario_service: Optional[ScenarioService] = None


def get_scenario_service() -> ScenarioService:
    """ScenarioServiceのシングルトンインスタンスを取得"""
    global _scenario_service
    if _scenario_service is None:
        _scenario_service = ScenarioService()
    return _scenario_service
