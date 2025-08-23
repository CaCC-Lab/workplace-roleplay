"""
シナリオカテゴリ管理モジュール

職場コミュニケーション練習アプリのシナリオを
「通常のコミュニケーション」と「ハラスメント防止」の
2つのカテゴリに分類・管理する機能を提供する。
"""

import re
from typing import Dict, Any, Tuple, List
from . import get_all_scenarios


class ScenarioCategoryManager:
    """シナリオカテゴリ管理クラス"""
    
    def __init__(self):
        self._regular_scenarios = None
        self._harassment_scenarios = None
        self.all_scenarios = None  # 5AI CONSENSUS: Initialize all_scenarios attribute
    
    def categorize_scenarios(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        全シナリオを2つのカテゴリに分類する
        
        Returns:
            Tuple[Dict[str, Any], Dict[str, Any]]: 
            (通常シナリオ, ハラスメント防止シナリオ)
        """
        if self._regular_scenarios is None or self._harassment_scenarios is None:
            self._categorize_internal()
        
        return self._regular_scenarios, self._harassment_scenarios
    
    def _categorize_internal(self):
        """内部的なシナリオ分類処理"""
        all_scenarios = get_all_scenarios()
        self.all_scenarios = all_scenarios  # 5AI CONSENSUS: Store all_scenarios as instance attribute
        
        regular_scenarios = {}
        harassment_scenarios = {}
        
        for scenario_id, scenario_data in all_scenarios.items():
            if self._is_harassment_scenario(scenario_id):
                harassment_scenarios[scenario_id] = self._process_harassment_scenario(scenario_data)
            else:
                regular_scenarios[scenario_id] = self._process_regular_scenario(scenario_data)
        
        self._regular_scenarios = regular_scenarios
        self._harassment_scenarios = harassment_scenarios
    
    def _is_harassment_scenario(self, scenario_id: str) -> bool:
        """
        シナリオIDがハラスメント関連かを判定する
        
        判定基準:
        - YAMLファイルのcategoryフィールドが'harassment'または'harassment_prevention'
        - scenario31-43: パワハラ・セクハラ関連シナリオ（31-33を追加）
        - harassment_gray_zones: グレーゾーン事例集
        - 'harassment'を含むID
        """
        # 5AI CONSENSUS: Ensure all_scenarios is loaded before access
        if self.all_scenarios is None:
            # Force loading if not yet loaded
            self._categorize_internal()
        
        # YAMLファイルのcategoryフィールドを最優先で確認
        if self.all_scenarios:
            scenario_data = self.all_scenarios.get(scenario_id)
            if scenario_data and isinstance(scenario_data, dict):
                category = scenario_data.get('category', '').lower()
                if category in ['harassment', 'harassment_prevention']:
                    return True
        
        # scenario31-43の範囲チェック（31-33追加、後方互換性のため）
        if scenario_id.startswith('scenario'):
            match = re.search(r'scenario(\d+)', scenario_id)
            if match:
                scenario_num = int(match.group(1))
                if 31 <= scenario_num <= 43:  # 5AI CONSENSUS: Include scenarios 31-33
                    return True
        
        # ハラスメント関連キーワードチェック
        if 'harassment' in scenario_id.lower():
            return True
        
        return False
    
    def _process_regular_scenario(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """通常シナリオのデータ処理"""
        # 基本的にはそのまま返すが、必要に応じてフィルタリング等を追加
        processed_data = scenario_data.copy()
        
        # カテゴリ情報を追加
        processed_data['category'] = 'regular_communication'
        processed_data['requires_consent'] = False
        
        return processed_data
    
    def _process_harassment_scenario(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """ハラスメント防止シナリオのデータ処理"""
        processed_data = scenario_data.copy()
        
        # カテゴリ情報を追加
        processed_data['category'] = 'harassment_prevention'
        processed_data['requires_consent'] = True
        
        # 警告メッセージを追加
        processed_data['warning_message'] = self._get_warning_message(scenario_data)
        
        return processed_data
    
    def _get_warning_message(self, scenario_data: Dict[str, Any]) -> str:
        """ハラスメント防止シナリオ用の警告メッセージを生成"""
        return (
            "このシナリオは職場のハラスメント防止を目的とした研修コンテンツです。"
            "デリケートな内容を含む場合がありますので、ご自身の判断で学習を進めてください。"
        )
    
    def get_regular_scenarios(self) -> Dict[str, Any]:
        """通常のコミュニケーションシナリオを取得"""
        regular, _ = self.categorize_scenarios()
        return regular
    
    def get_harassment_scenarios(self) -> Dict[str, Any]:
        """ハラスメント防止シナリオを取得"""
        _, harassment = self.categorize_scenarios()
        return harassment
    
    def get_scenario_summary(self, scenario_id: str) -> Dict[str, Any]:
        """指定シナリオのサマリー情報を取得"""
        regular, harassment = self.categorize_scenarios()
        
        if scenario_id in regular:
            scenario_data = regular[scenario_id]
        elif scenario_id in harassment:
            scenario_data = harassment[scenario_id]
        else:
            return None
        
        return {
            'id': scenario_id,
            'title': scenario_data.get('title', scenario_id),
            'description': scenario_data.get('description', ''),
            'difficulty': scenario_data.get('difficulty', 'intermediate'),
            'category': scenario_data.get('category'),
            'requires_consent': scenario_data.get('requires_consent', False),
            'tags': scenario_data.get('tags', [])
        }
    
    def get_categorized_summary(self) -> Dict[str, List[Dict[str, Any]]]:
        """カテゴリ分けされたシナリオサマリーを取得"""
        regular, harassment = self.categorize_scenarios()
        
        regular_summaries = []
        for scenario_id in regular.keys():
            summary = self.get_scenario_summary(scenario_id)
            if summary:
                regular_summaries.append(summary)
        
        harassment_summaries = []
        for scenario_id in harassment.keys():
            summary = self.get_scenario_summary(scenario_id)
            if summary:
                harassment_summaries.append(summary)
        
        return {
            'regular_communication': regular_summaries,
            'harassment_prevention': harassment_summaries
        }
    
    def clear_cache(self):
        """キャッシュをクリア（開発・テスト用）"""
        self._regular_scenarios = None
        self._harassment_scenarios = None
        self.all_scenarios = None  # 5AI CONSENSUS: Clear all_scenarios cache


# グローバルインスタンス
_category_manager = ScenarioCategoryManager()


def get_categorized_scenarios() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    カテゴリ分けされたシナリオを取得する便利関数
    
    Returns:
        Tuple[Dict[str, Any], Dict[str, Any]]: (通常シナリオ, ハラスメント防止シナリオ)
    """
    return _category_manager.categorize_scenarios()


def get_scenario_category_summary() -> Dict[str, List[Dict[str, Any]]]:
    """
    カテゴリ別シナリオサマリーを取得する便利関数
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: カテゴリ別シナリオリスト
    """
    return _category_manager.get_categorized_summary()


def is_harassment_scenario(scenario_id: str) -> bool:
    """
    指定シナリオがハラスメント関連かを判定する便利関数
    
    Args:
        scenario_id (str): シナリオID
        
    Returns:
        bool: ハラスメント関連の場合True
    """
    return _category_manager._is_harassment_scenario(scenario_id)


if __name__ == "__main__":
    # テスト実行
    manager = ScenarioCategoryManager()
    regular, harassment = manager.categorize_scenarios()
    
    print(f"通常シナリオ数: {len(regular)}")
    print(f"ハラスメント防止シナリオ数: {len(harassment)}")
    
    print("\n=== 通常シナリオ一覧 ===")
    for scenario_id in regular.keys():
        print(f"- {scenario_id}")
    
    print("\n=== ハラスメント防止シナリオ一覧 ===")
    for scenario_id in harassment.keys():
        print(f"- {scenario_id}")