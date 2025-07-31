"""
ペルソナとシナリオの統合サービス

シナリオプレイ時にペルソナを適用し、
より現実的な対話体験を提供する
"""
import logging
import random
from typing import Dict, List, Optional, Any
from datetime import datetime

from models import (
    db, AIPersona, PersonaScenarioConfig, UserPersonaInteraction,
    PracticeSession, PersonaMemory, Scenario,
    PersonaIndustry, PersonaRole, EmotionalState
)
from services.persona_service import PersonaService

logger = logging.getLogger(__name__)


class PersonaScenarioIntegrationService:
    """ペルソナとシナリオの統合管理サービス"""
    
    def __init__(self):
        self.persona_service = PersonaService()
    
    def get_suitable_personas_for_scenario(
        self, 
        scenario_id: str,
        user_id: Optional[int] = None
    ) -> List[AIPersona]:
        """
        シナリオに適したペルソナのリストを取得
        
        Args:
            scenario_id: シナリオID
            user_id: ユーザーID（オプション - 過去の対話履歴を考慮）
            
        Returns:
            適切なペルソナのリスト（推奨順）
        """
        # シナリオ情報を取得
        from scenarios import get_scenario_by_id
        scenario_data = get_scenario_by_id(scenario_id)
        
        if not scenario_data:
            logger.warning(f"シナリオが見つかりません: {scenario_id}")
            return []
        
        # 全ペルソナを取得
        all_personas = AIPersona.query.filter_by(is_active=True).all()
        
        # スコアリングしてソート
        scored_personas = []
        for persona in all_personas:
            score = self._calculate_persona_scenario_fit(
                persona, scenario_data, user_id
            )
            scored_personas.append((persona, score))
        
        # スコアの高い順にソート
        scored_personas.sort(key=lambda x: x[1], reverse=True)
        
        # ペルソナのリストを返す
        return [persona for persona, _ in scored_personas]
    
    def select_persona_for_scenario(
        self,
        scenario_id: str,
        user_id: Optional[int] = None,
        persona_code: Optional[str] = None
    ) -> AIPersona:
        """
        シナリオ用のペルソナを選択
        
        Args:
            scenario_id: シナリオID
            user_id: ユーザーID
            persona_code: 指定されたペルソナコード（オプション）
            
        Returns:
            選択されたペルソナ
        """
        # ペルソナコードが指定されている場合
        if persona_code:
            persona = AIPersona.query.filter_by(
                persona_code=persona_code,
                is_active=True
            ).first()
            
            if persona:
                return persona
            else:
                logger.warning(f"指定されたペルソナが見つかりません: {persona_code}")
        
        # 適切なペルソナを取得
        suitable_personas = self.get_suitable_personas_for_scenario(
            scenario_id, user_id
        )
        
        if not suitable_personas:
            # デフォルトペルソナを返す
            return self._get_default_persona()
        
        # ユーザーの過去の対話を考慮して選択
        if user_id:
            return self._select_with_variety(suitable_personas[:3], user_id)
        else:
            # 上位3つからランダムに選択
            return random.choice(suitable_personas[:3])
    
    def create_scenario_prompt(
        self,
        scenario_id: str,
        persona: AIPersona,
        user_message: str,
        conversation_history: List[Dict],
        user_id: Optional[int] = None
    ) -> str:
        """
        シナリオ用のペルソナプロンプトを生成
        
        Args:
            scenario_id: シナリオID
            persona: 使用するペルソナ
            user_message: ユーザーのメッセージ
            conversation_history: 会話履歴
            user_id: ユーザーID
            
        Returns:
            生成されたプロンプト
        """
        # シナリオ情報を取得
        from scenarios import get_scenario_by_id
        scenario_data = get_scenario_by_id(scenario_id)
        
        if not scenario_data:
            raise ValueError(f"シナリオが見つかりません: {scenario_id}")
        
        # シナリオ固有の設定を取得
        scenario_config = PersonaScenarioConfig.query.filter_by(
            persona_id=persona.id,
            scenario_id=scenario_id
        ).first()
        
        # シナリオコンテキストを構築
        scenario_context = {
            'title': scenario_data.get('title', ''),
            'description': scenario_data.get('description', ''),
            'situation': scenario_data.get('situation', ''),
            'your_role': scenario_data.get('your_role', ''),
            'conversation_partner': scenario_data.get('conversation_partner', ''),
            'difficulty': scenario_data.get('difficulty', 'medium')
        }
        
        # ペルソナメモリを取得
        memories = []
        if user_id:
            memories = self.persona_service._get_relevant_memories(
                persona.id, user_id, scenario_context.get('title', '')
            )
        
        # プロンプトを生成
        prompt = self.persona_service.create_persona_prompt(
            persona=persona,
            scenario_context=scenario_context,
            user_message=user_message,
            conversation_history=conversation_history,
            emotional_state=self._determine_emotional_state(
                persona, conversation_history
            ),
            memories=memories,
            scenario_config=scenario_config
        )
        
        return prompt
    
    def record_scenario_interaction(
        self,
        user_id: int,
        persona_id: int,
        session_id: int,
        scenario_id: str,
        interaction_data: Dict[str, Any]
    ) -> UserPersonaInteraction:
        """
        シナリオでの対話を記録
        
        Args:
            user_id: ユーザーID
            persona_id: ペルソナID
            session_id: セッションID
            scenario_id: シナリオID
            interaction_data: 対話データ
            
        Returns:
            作成された対話記録
        """
        # 既存の対話記録を検索または作成
        interaction = UserPersonaInteraction.query.filter_by(
            user_id=user_id,
            persona_id=persona_id,
            session_id=session_id
        ).first()
        
        if not interaction:
            interaction = UserPersonaInteraction(
                user_id=user_id,
                persona_id=persona_id,
                session_id=session_id,
                scenario_id=scenario_id
            )
            db.session.add(interaction)
        
        # 対話データを更新
        interaction.interaction_count += 1
        interaction.last_interaction = datetime.utcnow()
        interaction.total_exchanges = interaction_data.get('total_exchanges', 0)
        interaction.user_word_count = interaction_data.get('user_word_count', 0)
        interaction.persona_word_count = interaction_data.get('persona_word_count', 0)
        
        # 感情状態の更新
        if 'emotional_response' in interaction_data:
            interaction.emotional_state = interaction_data['emotional_response']
        
        # スキル実証の記録
        if 'skills_demonstrated' in interaction_data:
            interaction.skills_demonstrated = interaction_data['skills_demonstrated']
        
        # ラポールレベルの更新
        interaction.rapport_level = self._calculate_rapport_level(
            interaction.interaction_count,
            interaction_data.get('positive_interactions', 0)
        )
        
        db.session.commit()
        
        return interaction
    
    def get_persona_scenario_stats(
        self,
        persona_id: int,
        scenario_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ペルソナのシナリオ別統計を取得
        
        Args:
            persona_id: ペルソナID
            scenario_id: シナリオID（オプション）
            
        Returns:
            統計情報
        """
        query = UserPersonaInteraction.query.filter_by(persona_id=persona_id)
        
        if scenario_id:
            query = query.filter_by(scenario_id=scenario_id)
        
        interactions = query.all()
        
        if not interactions:
            return {
                'total_interactions': 0,
                'unique_users': 0,
                'average_rapport': 0,
                'scenarios_played': []
            }
        
        # 統計を集計
        unique_users = set(i.user_id for i in interactions)
        total_exchanges = sum(i.total_exchanges for i in interactions)
        avg_rapport = sum(i.rapport_level for i in interactions) / len(interactions)
        
        # シナリオ別の集計
        scenario_stats = {}
        for interaction in interactions:
            if interaction.scenario_id:
                if interaction.scenario_id not in scenario_stats:
                    scenario_stats[interaction.scenario_id] = {
                        'count': 0,
                        'avg_rapport': 0,
                        'total_rapport': 0
                    }
                
                stats = scenario_stats[interaction.scenario_id]
                stats['count'] += 1
                stats['total_rapport'] += interaction.rapport_level
                stats['avg_rapport'] = stats['total_rapport'] / stats['count']
        
        return {
            'total_interactions': len(interactions),
            'unique_users': len(unique_users),
            'total_exchanges': total_exchanges,
            'average_rapport': round(avg_rapport, 2),
            'scenario_breakdown': scenario_stats
        }
    
    # プライベートメソッド
    
    def _calculate_persona_scenario_fit(
        self,
        persona: AIPersona,
        scenario_data: Dict,
        user_id: Optional[int]
    ) -> float:
        """ペルソナとシナリオの適合度を計算"""
        score = 0.0
        
        # カテゴリマッチング
        scenario_category = scenario_data.get('category', '').lower()
        if scenario_category:
            # 業界マッチング
            industry_match = {
                'ビジネス': [PersonaIndustry.IT, PersonaIndustry.SALES, PersonaIndustry.FINANCE],
                'チーム': [PersonaIndustry.MANUFACTURING, PersonaIndustry.IT],
                '顧客対応': [PersonaIndustry.SALES, PersonaIndustry.HEALTHCARE],
                'マネジメント': [PersonaIndustry.IT, PersonaIndustry.MANUFACTURING]
            }
            
            for keyword, industries in industry_match.items():
                if keyword in scenario_category and persona.industry in industries:
                    score += 20
                    break
        
        # 難易度とペルソナ経験年数のマッチング
        difficulty = scenario_data.get('difficulty', 'medium')
        if difficulty == 'beginner' and persona.years_experience < 5:
            score += 15
        elif difficulty == 'intermediate' and 5 <= persona.years_experience <= 10:
            score += 15
        elif difficulty == 'advanced' and persona.years_experience > 10:
            score += 15
        
        # 役職の適合性
        partner_role = scenario_data.get('conversation_partner', '').lower()
        if partner_role:
            if '上司' in partner_role and persona.role == PersonaRole.MANAGER:
                score += 25
            elif '同僚' in partner_role and persona.role == PersonaRole.SENIOR:
                score += 20
            elif '部下' in partner_role and persona.role == PersonaRole.JUNIOR:
                score += 25
            elif 'メンター' in partner_role and persona.role == PersonaRole.MENTOR:
                score += 30
        
        # ユーザーの過去の対話履歴を考慮
        if user_id:
            past_interactions = UserPersonaInteraction.query.filter_by(
                user_id=user_id,
                persona_id=persona.id
            ).count()
            
            # 適度な新鮮さを保つ（使いすぎていないペルソナを優先）
            if past_interactions == 0:
                score += 10  # 新しいペルソナボーナス
            elif past_interactions < 3:
                score += 5   # まだ新鮮
            elif past_interactions > 10:
                score -= 10  # 使いすぎペナルティ
        
        # ランダム要素を追加（多様性のため）
        score += random.uniform(-5, 5)
        
        return max(0, score)
    
    def _get_default_persona(self) -> AIPersona:
        """デフォルトのペルソナを取得"""
        # 最も汎用的なペルソナを選択
        default_persona = AIPersona.query.filter_by(
            role=PersonaRole.SENIOR,
            is_active=True
        ).first()
        
        if not default_persona:
            # 任意のアクティブなペルソナを返す
            default_persona = AIPersona.query.filter_by(is_active=True).first()
        
        return default_persona
    
    def _select_with_variety(
        self,
        personas: List[AIPersona],
        user_id: int
    ) -> AIPersona:
        """過去の対話を考慮して多様性を保ちながら選択"""
        # 最近使用したペルソナを取得
        recent_interactions = UserPersonaInteraction.query.filter_by(
            user_id=user_id
        ).order_by(
            UserPersonaInteraction.last_interaction.desc()
        ).limit(3).all()
        
        recent_persona_ids = [i.persona_id for i in recent_interactions]
        
        # 最近使用していないペルソナを優先
        for persona in personas:
            if persona.id not in recent_persona_ids:
                return persona
        
        # すべて最近使用している場合は、最初のものを返す
        return personas[0]
    
    def _determine_emotional_state(
        self,
        persona: AIPersona,
        conversation_history: List[Dict]
    ) -> EmotionalState:
        """会話履歴から感情状態を判定"""
        if not conversation_history:
            return EmotionalState.NEUTRAL
        
        # 最後の数ターンの会話を分析
        recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
        
        # 簡単な感情分析（実際はより高度な分析が必要）
        positive_keywords = ['ありがとう', '素晴らしい', '良い', 'はい', '理解']
        negative_keywords = ['申し訳', '問題', '困った', '難しい', 'いいえ']
        stress_keywords = ['急いで', '期限', 'プレッシャー', '大変']
        
        positive_count = 0
        negative_count = 0
        stress_count = 0
        
        for msg in recent_messages:
            content = msg.get('content', '').lower()
            positive_count += sum(1 for kw in positive_keywords if kw in content)
            negative_count += sum(1 for kw in negative_keywords if kw in content)
            stress_count += sum(1 for kw in stress_keywords if kw in content)
        
        # 感情状態を決定
        if stress_count > 2:
            return EmotionalState.STRESSED
        elif positive_count > negative_count + 2:
            return EmotionalState.HAPPY
        elif negative_count > positive_count + 2:
            return EmotionalState.FRUSTRATED
        elif positive_count > 0:
            return EmotionalState.CONFIDENT
        else:
            return EmotionalState.NEUTRAL
    
    def _calculate_rapport_level(
        self,
        interaction_count: int,
        positive_interactions: int
    ) -> float:
        """ラポールレベルを計算"""
        if interaction_count == 0:
            return 0.5
        
        # 基本的な計算
        positive_ratio = positive_interactions / interaction_count
        
        # 対話回数による調整
        interaction_bonus = min(interaction_count * 0.05, 0.3)
        
        # 最終的なラポールレベル（0.0〜1.0）
        rapport = positive_ratio * 0.7 + interaction_bonus
        
        return min(1.0, max(0.0, rapport))