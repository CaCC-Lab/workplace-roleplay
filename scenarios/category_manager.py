"""
シナリオカテゴリ管理・組織化システム

5AI協調開発による高度な情報アーキテクチャ実装
- Claude 4: 情報構造設計
- Gemini 2.5: ベストプラクティス調査
- Qwen3-Coder: コア実装
- Codex: 論理的分類システム
- Cursor: UX最適化
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import yaml
import os
from collections import defaultdict

class DifficultyLevel(Enum):
    BEGINNER = "初級"
    INTERMEDIATE = "中級" 
    ADVANCED = "上級"

class CategoryType(Enum):
    BASIC_COMMUNICATION = "basic_comm"
    LEADERSHIP = "leadership"
    HARASSMENT_PREVENTION = "harassment"
    SPECIAL_SITUATIONS = "special"

@dataclass
class ScenarioMetadata:
    """シナリオメタデータの構造化"""
    id: str
    title: str
    description: str
    difficulty: DifficultyLevel
    tags: List[str]
    estimated_duration: int  # 分単位
    category: CategoryType
    prerequisites: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)

@dataclass
class CategoryInfo:
    """カテゴリ情報の定義"""
    key: str
    name: str
    description: str
    icon: str
    color_theme: str
    difficulty_range: List[DifficultyLevel]
    scenario_count: int = 0

class ScenarioOrganizer:
    """
    5AI協調による高度シナリオ組織化システム
    
    Features:
    - 多次元分類システム
    - インテリジェント推奨
    - 学習パス生成
    - フィルタリング・検索
    """
    
    def __init__(self):
        self.categories = self._initialize_categories()
        self.scenarios: Dict[str, ScenarioMetadata] = {}
        self.user_preferences = defaultdict(dict)
        
    def _initialize_categories(self) -> Dict[str, CategoryInfo]:
        """カテゴリシステムの初期化"""
        return {
            'basic_comm': CategoryInfo(
                key='basic_comm',
                name='基本コミュニケーション',
                description='職場での基礎的な対話スキルを身につける',
                icon='🏢',
                color_theme='blue',
                difficulty_range=[DifficultyLevel.BEGINNER]
            ),
            'leadership': CategoryInfo(
                key='leadership', 
                name='チームワーク・リーダーシップ',
                description='チーム運営と指導力を向上させる',
                icon='💼',
                color_theme='green',
                difficulty_range=[DifficultyLevel.INTERMEDIATE, DifficultyLevel.ADVANCED]
            ),
            'harassment': CategoryInfo(
                key='harassment',
                name='ハラスメント・グレーゾーン',
                description='適切な職場環境維持のための高度な対応',
                icon='⚖️', 
                color_theme='red',
                difficulty_range=[DifficultyLevel.INTERMEDIATE, DifficultyLevel.ADVANCED]
            ),
            'special': CategoryInfo(
                key='special',
                name='特殊シチュエーション',
                description='複雑で特殊な職場状況への対応',
                icon='🎭',
                color_theme='purple',
                difficulty_range=[DifficultyLevel.ADVANCED]
            )
        }
    
    def categorize_scenario(self, scenario_data: dict) -> CategoryType:
        """
        AI駆動シナリオ自動分類
        
        Args:
            scenario_data: YAMLから読み込んだシナリオデータ
            
        Returns:
            CategoryType: 分類されたカテゴリ
        """
        tags = scenario_data.get('tags', [])
        difficulty = scenario_data.get('difficulty', '初級')
        title = scenario_data.get('title', '').lower()
        description = scenario_data.get('description', '').lower()
        
        # ハラスメント関連の検出
        harassment_keywords = ['ハラスメント', 'パワハラ', 'セクハラ', 'グレーゾーン', '境界線']
        if any(keyword in title or keyword in description or keyword in str(tags) 
               for keyword in harassment_keywords):
            return CategoryType.HARASSMENT_PREVENTION
            
        # リーダーシップ関連の検出
        leadership_keywords = ['指導', 'リーダー', 'チーム', 'マネジメント', '管理職']
        if any(keyword in title or keyword in description or keyword in str(tags)
               for keyword in leadership_keywords):
            return CategoryType.LEADERSHIP
            
        # 特殊シチュエーションの検出
        if difficulty == '上級' and 'special' in str(tags):
            return CategoryType.SPECIAL_SITUATIONS
            
        # デフォルトは基本コミュニケーション
        return CategoryType.BASIC_COMMUNICATION
    
    def filter_scenarios(self, 
                        category: Optional[CategoryType] = None,
                        difficulty: Optional[DifficultyLevel] = None,
                        tags: Optional[List[str]] = None,
                        max_duration: Optional[int] = None) -> List[ScenarioMetadata]:
        """
        多次元フィルタリングシステム
        
        Args:
            category: カテゴリフィルター
            difficulty: 難易度フィルター  
            tags: タグフィルター
            max_duration: 最大所要時間（分）
            
        Returns:
            List[ScenarioMetadata]: フィルター済みシナリオリスト
        """
        filtered = list(self.scenarios.values())
        
        if category:
            filtered = [s for s in filtered if s.category == category]
            
        if difficulty:
            filtered = [s for s in filtered if s.difficulty == difficulty]
            
        if tags:
            filtered = [s for s in filtered if any(tag in s.tags for tag in tags)]
            
        if max_duration:
            filtered = [s for s in filtered if s.estimated_duration <= max_duration]
            
        return filtered
    
    def get_smart_recommendations(self, 
                                user_id: str, 
                                limit: int = 5) -> List[ScenarioMetadata]:
        """
        AI駆動個人化推奨システム
        
        Args:
            user_id: ユーザーID
            limit: 推奨シナリオ数
            
        Returns:
            List[ScenarioMetadata]: 推奨シナリオリスト
        """
        # ユーザーの学習履歴と選好を分析
        user_pref = self.user_preferences.get(user_id, {})
        completed_scenarios = user_pref.get('completed', [])
        preferred_categories = user_pref.get('categories', [])
        
        # 推奨ロジック（シンプル版）
        recommendations = []
        for scenario in self.scenarios.values():
            if scenario.id not in completed_scenarios:
                score = self._calculate_recommendation_score(scenario, user_pref)
                recommendations.append((score, scenario))
        
        # スコア順でソートして上位を返す
        recommendations.sort(key=lambda x: x[0], reverse=True)
        return [scenario for _, scenario in recommendations[:limit]]
    
    def _calculate_recommendation_score(self, 
                                      scenario: ScenarioMetadata,
                                      user_pref: dict) -> float:
        """推奨スコアの計算"""
        score = 0.0
        
        # カテゴリの選好
        preferred_categories = user_pref.get('categories', [])
        if scenario.category.value in preferred_categories:
            score += 2.0
            
        # 難易度の適合性
        user_level = user_pref.get('level', DifficultyLevel.BEGINNER)
        if scenario.difficulty == user_level:
            score += 1.5
        elif abs(list(DifficultyLevel).index(scenario.difficulty) - 
                list(DifficultyLevel).index(user_level)) == 1:
            score += 1.0
            
        # タグの一致度
        user_interests = user_pref.get('interests', [])
        matching_tags = set(scenario.tags) & set(user_interests)
        score += len(matching_tags) * 0.5
        
        return score
    
    def generate_learning_path(self, 
                             user_level: DifficultyLevel,
                             focus_area: Optional[CategoryType] = None) -> List[ScenarioMetadata]:
        """
        個人化学習パス生成
        
        Args:
            user_level: ユーザーの現在レベル
            focus_area: 重点分野（オプション）
            
        Returns:
            List[ScenarioMetadata]: 最適化された学習パス
        """
        # レベルに応じた基礎シナリオの選定
        base_scenarios = self.filter_scenarios(
            category=CategoryType.BASIC_COMMUNICATION,
            difficulty=DifficultyLevel.BEGINNER
        )
        
        learning_path = base_scenarios[:3]  # 基礎3シナリオ
        
        if user_level in [DifficultyLevel.INTERMEDIATE, DifficultyLevel.ADVANCED]:
            # 中級者以上向けの追加
            if focus_area:
                focus_scenarios = self.filter_scenarios(
                    category=focus_area,
                    difficulty=DifficultyLevel.INTERMEDIATE
                )
                learning_path.extend(focus_scenarios[:2])
            
        if user_level == DifficultyLevel.ADVANCED:
            # 上級者向けの特殊シナリオ
            advanced_scenarios = self.filter_scenarios(
                difficulty=DifficultyLevel.ADVANCED
            )
            learning_path.extend(advanced_scenarios[:2])
            
        return learning_path
    
    def get_category_statistics(self) -> Dict[str, Dict]:
        """カテゴリ別統計情報の取得"""
        stats = {}
        
        for cat_key, category in self.categories.items():
            cat_scenarios = [s for s in self.scenarios.values() 
                           if s.category.value == cat_key]
            
            stats[cat_key] = {
                'name': category.name,
                'count': len(cat_scenarios),
                'difficulties': list(set(s.difficulty.value for s in cat_scenarios)),
                'avg_duration': sum(s.estimated_duration for s in cat_scenarios) / len(cat_scenarios) if cat_scenarios else 0,
                'popular_tags': self._get_popular_tags(cat_scenarios)
            }
            
        return stats
    
    def _get_popular_tags(self, scenarios: List[ScenarioMetadata]) -> List[str]:
        """人気タグの抽出"""
        tag_counts = defaultdict(int)
        for scenario in scenarios:
            for tag in scenario.tags:
                tag_counts[tag] += 1
        
        # 上位5タグを返す
        return [tag for tag, _ in sorted(tag_counts.items(), 
                                       key=lambda x: x[1], reverse=True)[:5]]

# グローバルインスタンス
scenario_organizer = ScenarioOrganizer()