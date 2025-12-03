"""
Category manager tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestScenarioCategoryManager:
    """ScenarioCategoryManagerクラスのテスト"""

    def test_初期化(self):
        """初期化のテスト"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()

        assert manager._regular_scenarios is None
        assert manager._harassment_scenarios is None

    def test_シナリオ分類(self):
        """シナリオ分類のテスト"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        regular, harassment = manager.categorize_scenarios()

        assert isinstance(regular, dict)
        assert isinstance(harassment, dict)

    def test_通常シナリオ取得(self):
        """通常シナリオの取得"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        regular = manager.get_regular_scenarios()

        assert isinstance(regular, dict)

    def test_ハラスメントシナリオ取得(self):
        """ハラスメントシナリオの取得"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        harassment = manager.get_harassment_scenarios()

        assert isinstance(harassment, dict)

    def test_ハラスメント判定_シナリオ番号(self):
        """シナリオ番号によるハラスメント判定"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        manager.categorize_scenarios()  # 初期化

        # scenario31-43はハラスメント関連
        assert manager._is_harassment_scenario("scenario31") is True
        assert manager._is_harassment_scenario("scenario40") is True
        assert manager._is_harassment_scenario("scenario43") is True

        # 通常シナリオ
        assert manager._is_harassment_scenario("scenario1") is False
        assert manager._is_harassment_scenario("scenario10") is False

    def test_ハラスメント判定_キーワード(self):
        """キーワードによるハラスメント判定"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        manager.categorize_scenarios()

        assert manager._is_harassment_scenario("harassment_example") is True
        assert manager._is_harassment_scenario("test_harassment_scenario") is True

    def test_ハラスメント判定_カテゴリフィールド(self):
        """カテゴリフィールドによるハラスメント判定"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        manager.all_scenarios = {"test_scenario": {"category": "harassment"}}

        assert manager._is_harassment_scenario("test_scenario") is True

    def test_シナリオサマリー取得_存在するシナリオ(self):
        """存在するシナリオのサマリー取得"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        manager.categorize_scenarios()

        # 通常シナリオがあれば取得
        regular, _ = manager.categorize_scenarios()
        if regular:
            first_id = list(regular.keys())[0]
            summary = manager.get_scenario_summary(first_id)

            assert summary is not None
            assert "id" in summary
            assert "category" in summary

    def test_シナリオサマリー取得_存在しないシナリオ(self):
        """存在しないシナリオのサマリー取得"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        manager.categorize_scenarios()

        summary = manager.get_scenario_summary("nonexistent_scenario_xyz")

        assert summary is None

    def test_カテゴリ別サマリー取得(self):
        """カテゴリ別サマリーの取得"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        summaries = manager.get_categorized_summary()

        assert "regular_communication" in summaries
        assert "harassment_prevention" in summaries
        assert isinstance(summaries["regular_communication"], list)
        assert isinstance(summaries["harassment_prevention"], list)

    def test_キャッシュクリア(self):
        """キャッシュクリアのテスト"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        manager.categorize_scenarios()

        # キャッシュされている
        assert manager._regular_scenarios is not None

        # クリア
        manager.clear_cache()

        assert manager._regular_scenarios is None
        assert manager._harassment_scenarios is None
        assert manager.all_scenarios is None

    def test_通常シナリオ処理(self):
        """通常シナリオの処理"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()

        test_data = {"title": "テスト", "description": "説明"}
        processed = manager._process_regular_scenario(test_data)

        assert processed["category"] == "regular_communication"
        assert processed["requires_consent"] is False

    def test_ハラスメントシナリオ処理(self):
        """ハラスメントシナリオの処理"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()

        test_data = {"title": "テスト", "description": "説明"}
        processed = manager._process_harassment_scenario(test_data)

        assert processed["category"] == "harassment_prevention"
        assert processed["requires_consent"] is True
        assert "warning_message" in processed

    def test_警告メッセージ生成(self):
        """警告メッセージの生成"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()

        test_data = {"title": "テスト"}
        message = manager._get_warning_message(test_data)

        assert isinstance(message, str)
        assert len(message) > 0


class TestConvenienceFunctions:
    """便利関数のテスト"""

    def test_get_categorized_scenarios(self):
        """get_categorized_scenarios関数"""
        from scenarios.category_manager import get_categorized_scenarios

        regular, harassment = get_categorized_scenarios()

        assert isinstance(regular, dict)
        assert isinstance(harassment, dict)

    def test_get_scenario_category_summary(self):
        """get_scenario_category_summary関数"""
        from scenarios.category_manager import get_scenario_category_summary

        summaries = get_scenario_category_summary()

        assert isinstance(summaries, dict)
        assert "regular_communication" in summaries
        assert "harassment_prevention" in summaries

    def test_is_harassment_scenario(self):
        """is_harassment_scenario関数"""
        from scenarios.category_manager import is_harassment_scenario

        # ハラスメントシナリオ
        assert is_harassment_scenario("scenario35") is True

        # 通常シナリオ
        assert is_harassment_scenario("scenario1") is False


class TestGlobalInstance:
    """グローバルインスタンスのテスト"""

    def test_グローバルインスタンスが存在(self):
        """グローバルインスタンスが存在"""
        from scenarios.category_manager import _category_manager

        assert _category_manager is not None


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_all_scenarios_None時のハラスメント判定(self):
        """all_scenariosがNoneの場合のハラスメント判定"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()
        # all_scenariosをNoneに設定
        manager.all_scenarios = None

        # scenario31はハラスメント関連（番号ベース）
        result = manager._is_harassment_scenario("scenario31")

        # 内部で_categorize_internalが呼ばれる
        assert result is True

    def test_空のシナリオデータ処理(self):
        """空のシナリオデータの処理"""
        from scenarios.category_manager import ScenarioCategoryManager

        manager = ScenarioCategoryManager()

        empty_data = {}
        processed = manager._process_regular_scenario(empty_data)

        assert processed["category"] == "regular_communication"
        assert processed["requires_consent"] is False
