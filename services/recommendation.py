"""
パーソナライズ学習パス推薦システム

ユーザーのスキル分析結果に基づいて最適なシナリオを推薦
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from scenarios import load_scenarios
from tasks.strength_analysis import get_latest_analysis_result

logger = logging.getLogger(__name__)


@dataclass
class RecommendationItem:
    """推薦アイテム"""
    scenario_id: str
    title: str
    description: str
    target_strengths: List[str]
    difficulty: int
    recommendation_score: float
    reason: str


class PersonalizedRecommendationEngine:
    """
    パーソナライズ推薦エンジン
    
    ユーザーの弱点スキルに基づいてシナリオを推薦する
    """
    
    def __init__(self):
        self.skill_weights = {
            'empathy': 1.0,
            'clarity': 1.0,
            'active_listening': 1.0,
            'adaptability': 1.0,
            'positivity': 1.0,
            'professionalism': 1.0
        }
        self.scenarios = load_scenarios()
    
    def get_user_recommendations(self, user_id: int, 
                               limit: int = 3,
                               difficulty_preference: Optional[int] = None) -> List[RecommendationItem]:
        """
        ユーザーに対する推薦シナリオを取得
        
        Args:
            user_id: ユーザーID
            limit: 推薦件数
            difficulty_preference: 希望難易度（1-5、Noneで自動調整）
            
        Returns:
            推薦シナリオリスト
        """
        try:
            # ユーザーの最新スキル分析結果を取得
            user_analysis = self._get_user_analysis(user_id)
            if not user_analysis:
                # 分析結果がない場合は初心者向けシナリオを推薦
                return self._get_beginner_recommendations(limit)
            
            # 弱点スキルを特定
            weak_skills = self._identify_weak_skills(user_analysis)
            
            # 各シナリオの推薦スコアを計算
            scenario_scores = []
            for scenario_id, scenario in self.scenarios.items():
                score = self._calculate_recommendation_score(
                    scenario, weak_skills, user_analysis, difficulty_preference
                )
                if score > 0:
                    recommendation = self._create_recommendation_item(
                        scenario_id, scenario, score, weak_skills
                    )
                    scenario_scores.append(recommendation)
            
            # スコア順にソートして上位を返す
            scenario_scores.sort(key=lambda x: x.recommendation_score, reverse=True)
            return scenario_scores[:limit]
            
        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {str(e)}")
            return self._get_fallback_recommendations(limit)
    
    def _get_user_analysis(self, user_id: int) -> Optional[Dict[str, Any]]:
        """ユーザーの最新分析結果を取得"""
        try:
            analysis_result = get_latest_analysis_result(user_id)
            if analysis_result and 'strengths_analysis' in analysis_result:
                return analysis_result['strengths_analysis']
            return None
        except Exception as e:
            logger.warning(f"Could not get analysis for user {user_id}: {str(e)}")
            return None
    
    def _identify_weak_skills(self, analysis: Dict[str, Any]) -> List[Tuple[str, float]]:
        """
        弱点スキルを特定
        
        Args:
            analysis: 分析結果
            
        Returns:
            [(skill_name, score), ...] 弱点順
        """
        if 'skill_scores' not in analysis:
            return []
        
        skill_scores = analysis['skill_scores']
        weak_skills = []
        
        for skill, score in skill_scores.items():
            if skill in self.skill_weights and score < 3.5:  # 3.5未満を弱点とみなす
                weak_skills.append((skill, score))
        
        # スコア順（低い順）でソート
        weak_skills.sort(key=lambda x: x[1])
        return weak_skills
    
    def _calculate_recommendation_score(self, scenario: Dict[str, Any], 
                                     weak_skills: List[Tuple[str, float]],
                                     user_analysis: Dict[str, Any],
                                     difficulty_preference: Optional[int] = None) -> float:
        """
        シナリオの推薦スコアを計算
        
        Args:
            scenario: シナリオ情報
            weak_skills: 弱点スキルリスト
            user_analysis: ユーザー分析結果
            difficulty_preference: 希望難易度
            
        Returns:
            推薦スコア
        """
        if 'metadata' not in scenario:
            return 0.0
        
        metadata = scenario['metadata']
        target_strengths = metadata.get('target_strengths', [])
        difficulty = metadata.get('difficulty', 3)
        
        score = 0.0
        
        # 弱点スキルとの関連度をスコアに反映
        for skill_name, skill_score in weak_skills:
            if skill_name in target_strengths:
                # 弱点度合い（1 - skill_score/5）をスコアに加算
                weakness_factor = max(0, (5.0 - skill_score) / 5.0)
                score += weakness_factor * self.skill_weights.get(skill_name, 1.0)
        
        # 難易度調整
        if difficulty_preference:
            # 希望難易度からの乖離を減点
            difficulty_penalty = abs(difficulty - difficulty_preference) * 0.1
            score = max(0, score - difficulty_penalty)
        else:
            # 自動調整：ユーザーの平均スキルレベルに応じた難易度
            avg_skill = self._calculate_average_skill(user_analysis)
            ideal_difficulty = min(5, max(1, int(avg_skill) + 1))
            if abs(difficulty - ideal_difficulty) > 1:
                score *= 0.7  # 難易度が合わない場合は減点
        
        return score
    
    def _calculate_average_skill(self, analysis: Dict[str, Any]) -> float:
        """ユーザーの平均スキルレベルを計算"""
        if 'skill_scores' not in analysis:
            return 2.5
        
        scores = list(analysis['skill_scores'].values())
        return sum(scores) / len(scores) if scores else 2.5
    
    def _create_recommendation_item(self, scenario_id: str, scenario: Dict[str, Any],
                                  score: float, weak_skills: List[Tuple[str, float]]) -> RecommendationItem:
        """推薦アイテムを作成"""
        metadata = scenario.get('metadata', {})
        target_strengths = metadata.get('target_strengths', [])
        
        # 推薦理由を生成
        weak_skill_names = [skill for skill, _ in weak_skills]
        matched_skills = [skill for skill in target_strengths if skill in weak_skill_names]
        
        if matched_skills:
            skill_names = self._translate_skill_names(matched_skills)
            reason = f"{', '.join(skill_names)}のスキル向上に効果的です"
        else:
            reason = "バランスの良いスキル向上に役立ちます"
        
        return RecommendationItem(
            scenario_id=scenario_id,
            title=scenario.get('title', 'シナリオ'),
            description=scenario.get('description', ''),
            target_strengths=target_strengths,
            difficulty=metadata.get('difficulty', 3),
            recommendation_score=score,
            reason=reason
        )
    
    def _translate_skill_names(self, skills: List[str]) -> List[str]:
        """スキル名を日本語に翻訳"""
        translations = {
            'empathy': '共感力',
            'clarity': '明確性',
            'active_listening': '傾聴力',
            'adaptability': '適応力',
            'positivity': '前向きさ',
            'professionalism': 'プロフェッショナリズム'
        }
        return [translations.get(skill, skill) for skill in skills]
    
    def _get_beginner_recommendations(self, limit: int) -> List[RecommendationItem]:
        """初心者向け推薦シナリオ"""
        beginner_scenarios = []
        
        for scenario_id, scenario in self.scenarios.items():
            metadata = scenario.get('metadata', {})
            if metadata.get('difficulty', 3) <= 2:
                item = RecommendationItem(
                    scenario_id=scenario_id,
                    title=scenario.get('title', 'シナリオ'),
                    description=scenario.get('description', ''),
                    target_strengths=metadata.get('target_strengths', []),
                    difficulty=metadata.get('difficulty', 2),
                    recommendation_score=3.0,
                    reason="初心者の方におすすめの基本的なシナリオです"
                )
                beginner_scenarios.append(item)
        
        return beginner_scenarios[:limit]
    
    def _get_fallback_recommendations(self, limit: int) -> List[RecommendationItem]:
        """フォールバック推薦（エラー時など）"""
        fallback_scenarios = []
        
        # 人気シナリオや基本的なシナリオを推薦
        basic_scenario_ids = ['business_meeting', 'lunch_conversation', 'project_discussion']
        
        for scenario_id in basic_scenario_ids:
            if scenario_id in self.scenarios:
                scenario = self.scenarios[scenario_id]
                item = RecommendationItem(
                    scenario_id=scenario_id,
                    title=scenario.get('title', 'シナリオ'),
                    description=scenario.get('description', ''),
                    target_strengths=[],
                    difficulty=3,
                    recommendation_score=2.5,
                    reason="人気のシナリオです"
                )
                fallback_scenarios.append(item)
        
        return fallback_scenarios[:limit]
    
    def get_explanation(self, user_id: int) -> Dict[str, Any]:
        """
        推薦根拠の詳細説明を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            推薦根拠の詳細
        """
        try:
            user_analysis = self._get_user_analysis(user_id)
            if not user_analysis:
                return {
                    'status': 'no_analysis',
                    'message': 'まだ分析データが不足しています。いくつかのシナリオを試してから再度確認してください。'
                }
            
            weak_skills = self._identify_weak_skills(user_analysis)
            skill_scores = user_analysis.get('skill_scores', {})
            
            return {
                'status': 'success',
                'weak_skills': weak_skills,
                'skill_scores': skill_scores,
                'average_skill': self._calculate_average_skill(user_analysis),
                'recommendation_logic': '弱点スキルに関連するシナリオを優先的に推薦しています'
            }
            
        except Exception as e:
            logger.error(f"Error getting explanation for user {user_id}: {str(e)}")
            return {
                'status': 'error',
                'message': '推薦根拠の取得中にエラーが発生しました'
            }


# グローバルインスタンス
recommendation_engine = PersonalizedRecommendationEngine()


def get_recommendations_for_user(user_id: int, limit: int = 3,
                               difficulty_preference: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    ユーザー向け推薦シナリオを取得（外部API用）
    
    Args:
        user_id: ユーザーID
        limit: 推薦件数
        difficulty_preference: 希望難易度
        
    Returns:
        推薦シナリオのJSON形式リスト
    """
    recommendations = recommendation_engine.get_user_recommendations(
        user_id, limit, difficulty_preference
    )
    
    return [
        {
            'scenario_id': rec.scenario_id,
            'title': rec.title,
            'description': rec.description,
            'target_strengths': rec.target_strengths,
            'difficulty': rec.difficulty,
            'recommendation_score': round(rec.recommendation_score, 2),
            'reason': rec.reason
        }
        for rec in recommendations
    ]


def get_recommendation_explanation(user_id: int) -> Dict[str, Any]:
    """推薦根拠の説明を取得（外部API用）"""
    return recommendation_engine.get_explanation(user_id)