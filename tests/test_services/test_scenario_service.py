"""
ScenarioServiceのユニットテスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestScenarioService:
    """ScenarioServiceのテストクラス"""

    @pytest.fixture
    def mock_scenarios(self):
        """テスト用のシナリオデータ"""
        return {
            "scenario1": {
                "id": "scenario1",
                "title": "テストシナリオ1",
                "description": "テスト用のシナリオです",
                "difficulty": "初級",
                "tags": ["テスト", "開発"],
                "role_info": "AIは上司役、ユーザーは部下役",
                "character_setting": {
                    "personality": "協力的で前向き",
                    "speaking_style": "丁寧で親しみやすい",
                    "situation": "チーム会議での状況",
                    "initial_approach": "フレンドリーに",
                },
                "system_prompt": "あなたは上司です。",
                "initial_context": "プロジェクトの進捗報告の場面です。",
            },
            "harassment_scenario1": {
                "id": "harassment_scenario1",
                "title": "ハラスメント防止シナリオ",
                "description": "ハラスメント防止のためのシナリオ",
                "difficulty": "中級",
                "tags": ["ハラスメント", "防止"],
                "role_info": "AIは同僚役、ユーザーは管理職役",
            },
        }

    @pytest.fixture
    def scenario_service(self, mock_scenarios):
        """モック済みのScenarioService"""
        with patch("services.scenario_service.load_scenarios", return_value=mock_scenarios):
            from services.scenario_service import ScenarioService

            service = ScenarioService()
            return service

    def test_initialization(self, scenario_service, mock_scenarios):
        """サービスの初期化テスト"""
        assert scenario_service._scenarios is not None
        assert len(scenario_service._scenarios) == 2

    def test_get_all_scenarios(self, scenario_service, mock_scenarios):
        """全シナリオ取得テスト"""
        scenarios = scenario_service.get_all_scenarios()

        assert isinstance(scenarios, dict)
        assert len(scenarios) == 2
        assert "scenario1" in scenarios
        assert "harassment_scenario1" in scenarios

    def test_get_all_scenarios_returns_copy(self, scenario_service):
        """get_all_scenariosがコピーを返すことを確認"""
        scenarios1 = scenario_service.get_all_scenarios()
        scenarios2 = scenario_service.get_all_scenarios()

        # 異なるオブジェクトであることを確認
        assert scenarios1 is not scenarios2

        # 内容は同じ
        assert scenarios1 == scenarios2

    def test_get_scenario_by_id_existing(self, scenario_service):
        """存在するシナリオIDでの取得テスト"""
        scenario = scenario_service.get_scenario_by_id("scenario1")

        assert scenario is not None
        assert scenario["id"] == "scenario1"
        assert scenario["title"] == "テストシナリオ1"

    def test_get_scenario_by_id_not_found(self, scenario_service):
        """存在しないシナリオIDでの取得テスト"""
        scenario = scenario_service.get_scenario_by_id("nonexistent")

        assert scenario is None

    def test_get_scenario_by_id_empty_scenarios(self):
        """シナリオが空の場合のテスト"""
        with patch("services.scenario_service.load_scenarios", return_value={}):
            from services.scenario_service import ScenarioService

            service = ScenarioService()

            scenario = service.get_scenario_by_id("any_id")
            assert scenario is None

    def test_build_system_prompt_normal_role(self, scenario_service, mock_scenarios):
        """通常ロールでのシステムプロンプト生成テスト"""
        scenario_data = mock_scenarios["scenario1"]
        prompt = scenario_service.build_system_prompt(scenario_data, is_reverse_role=False)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "ロールプレイの基本設定" in prompt
        assert "協力的で前向き" in prompt  # personality
        assert "丁寧で親しみやすい" in prompt  # speaking_style

    def test_build_system_prompt_reverse_role(self, scenario_service, mock_scenarios):
        """リバースロールでのシステムプロンプト生成テスト"""
        scenario_data = mock_scenarios["scenario1"]
        prompt = scenario_service.build_system_prompt(scenario_data, is_reverse_role=True)

        assert prompt == "あなたは上司です。"

    def test_build_system_prompt_missing_character_setting(self, scenario_service):
        """character_settingが欠けている場合のテスト"""
        scenario_data = {"description": "テスト", "role_info": "AI,ユーザー"}

        prompt = scenario_service.build_system_prompt(scenario_data, is_reverse_role=False)

        assert isinstance(prompt, str)
        assert "未設定" in prompt  # デフォルト値が使用される

    def test_get_initial_message_normal_role(self, scenario_service, mock_scenarios):
        """通常ロールでの初期メッセージ取得テスト"""
        scenario_data = mock_scenarios["scenario1"]
        message = scenario_service.get_initial_message(scenario_data, is_reverse_role=False)

        assert message is not None
        assert "フレンドリーに" in message

    def test_get_initial_message_reverse_role(self, scenario_service, mock_scenarios):
        """リバースロールでの初期メッセージ取得テスト"""
        scenario_data = mock_scenarios["scenario1"]
        message = scenario_service.get_initial_message(scenario_data, is_reverse_role=True)

        assert message is not None
        assert "プロジェクトの進捗報告" in message
        assert "上司として" in message

    def test_get_initial_message_reverse_role_no_context(self, scenario_service):
        """initial_contextがない場合のリバースロール"""
        scenario_data = {"title": "Test"}
        message = scenario_service.get_initial_message(scenario_data, is_reverse_role=True)

        assert message is None

    def test_get_user_role_normal(self, scenario_service, mock_scenarios):
        """通常ロールでのユーザー役割取得テスト"""
        scenario_data = mock_scenarios["scenario1"]
        role = scenario_service.get_user_role(scenario_data, is_reverse_role=False)

        # "AIは上司役、ユーザーは部下役" から "ユーザーは部下役" を取得
        assert "部下" in role or role == "不明"  # 実装依存

    def test_get_user_role_reverse(self, scenario_service, mock_scenarios):
        """リバースロールでのユーザー役割取得テスト"""
        scenario_data = {"user_role": "上司"}
        role = scenario_service.get_user_role(scenario_data, is_reverse_role=True)

        assert role == "上司"

    def test_get_user_role_missing_data(self, scenario_service):
        """role_infoがない場合のテスト"""
        scenario_data = {}
        role = scenario_service.get_user_role(scenario_data, is_reverse_role=False)

        assert role == "不明"

    def test_build_reverse_role_prompt(self, scenario_service, mock_scenarios):
        """リバースロールプロンプト生成テスト"""
        scenario_data = mock_scenarios["scenario1"]
        prompt = scenario_service.build_reverse_role_prompt(scenario_data)

        assert prompt == "あなたは上司です。"

    def test_build_reverse_role_prompt_missing(self, scenario_service):
        """system_promptがない場合のテスト"""
        scenario_data = {}
        prompt = scenario_service.build_reverse_role_prompt(scenario_data)

        assert prompt == ""


class TestScenarioServiceCategoryMethods:
    """カテゴリ関連メソッドのテスト"""

    @pytest.fixture
    def scenario_service(self):
        """モック済みのScenarioService"""
        with patch("services.scenario_service.load_scenarios", return_value={}):
            from services.scenario_service import ScenarioService

            return ScenarioService()

    @patch("services.scenario_service.get_categorized_scenarios_func")
    def test_get_categorized_scenarios(self, mock_categorize, scenario_service):
        """カテゴリ別シナリオ取得テスト"""
        mock_categorize.return_value = ({"normal": {}}, {"harassment": {}})

        result = scenario_service.get_categorized_scenarios()

        mock_categorize.assert_called_once()
        assert isinstance(result, tuple)
        assert len(result) == 2

    @patch("services.scenario_service.is_harassment_scenario")
    def test_is_harassment_scenario_true(self, mock_is_harassment, scenario_service):
        """ハラスメントシナリオ判定テスト（True）"""
        mock_is_harassment.return_value = True

        result = scenario_service.is_harassment_scenario("harassment_01")

        assert result is True
        mock_is_harassment.assert_called_once_with("harassment_01")

    @patch("services.scenario_service.is_harassment_scenario")
    def test_is_harassment_scenario_false(self, mock_is_harassment, scenario_service):
        """ハラスメントシナリオ判定テスト（False）"""
        mock_is_harassment.return_value = False

        result = scenario_service.is_harassment_scenario("normal_scenario")

        assert result is False

    @patch("services.scenario_service.get_scenario_category_summary")
    def test_get_scenario_category_summary(self, mock_summary, scenario_service):
        """カテゴリサマリー取得テスト"""
        mock_summary.return_value = {"total": 10, "categories": {}}

        result = scenario_service.get_scenario_category_summary()

        mock_summary.assert_called_once()
        assert "total" in result


class TestGetScenarioService:
    """get_scenario_service関数のテスト"""

    def test_singleton_pattern(self):
        """シングルトンパターンのテスト"""
        with patch("services.scenario_service.load_scenarios", return_value={}):
            # グローバル変数をリセット
            import services.scenario_service as module

            module._scenario_service = None

            from services.scenario_service import get_scenario_service

            service1 = get_scenario_service()
            service2 = get_scenario_service()

            assert service1 is service2


class TestScenarioServiceErrorHandling:
    """エラーハンドリングのテスト"""

    def test_load_scenarios_error(self):
        """シナリオロードエラー時のテスト"""
        with patch("services.scenario_service.load_scenarios", side_effect=Exception("Load error")):
            from services.scenario_service import ScenarioService

            # エラーが発生してもサービスは初期化される
            service = ScenarioService()

            # シナリオは空の辞書になる
            assert service._scenarios == {}
            assert service.get_all_scenarios() == {}
