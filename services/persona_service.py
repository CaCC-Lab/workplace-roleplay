"""
AIペルソナ管理サービス

ペルソナの読み込み、メモリ管理、会話生成を担当
"""
import os
import yaml
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import and_, or_, desc
import redis
from flask import current_app

from models import (
    db, AIPersona, PersonaMemory, PersonaScenarioConfig, 
    UserPersonaInteraction, PersonaIndustry, PersonaRole,
    PersonaPersonality, EmotionalState
)

logger = logging.getLogger(__name__)


class PersonaService:
    """ペルソナ管理の中核サービス"""
    
    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.cache_ttl = 3600  # 1時間
        
    def _get_redis_client(self):
        """Redis接続を取得"""
        try:
            from config.config import get_config
            config = get_config()
            return redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Redis接続エラー: {e}")
            return None
    
    def load_personas_from_yaml(self):
        """YAMLファイルからペルソナを読み込み、データベースに同期"""
        persona_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 'personas'
        )
        
        if not os.path.exists(persona_dir):
            logger.warning(f"ペルソナディレクトリが見つかりません: {persona_dir}")
            return
        
        loaded_count = 0
        updated_count = 0
        
        for filename in os.listdir(persona_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                if filename == 'README.md':
                    continue
                    
                filepath = os.path.join(persona_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    
                    # 既存のペルソナを確認
                    persona = AIPersona.query.filter_by(
                        persona_code=data['persona_code']
                    ).first()
                    
                    if persona:
                        # 更新
                        self._update_persona(persona, data)
                        updated_count += 1
                    else:
                        # 新規作成
                        persona = self._create_persona(data)
                        db.session.add(persona)
                        loaded_count += 1
                        
                except Exception as e:
                    logger.error(f"ペルソナ読み込みエラー {filename}: {e}")
                    continue
        
        if loaded_count > 0 or updated_count > 0:
            db.session.commit()
            logger.info(
                f"ペルソナ同期完了 - 新規: {loaded_count}, 更新: {updated_count}"
            )
    
    def _create_persona(self, data: Dict) -> AIPersona:
        """YAMLデータからペルソナインスタンスを作成"""
        # Enumの変換
        industry = PersonaIndustry[data['industry']]
        role = PersonaRole[data['role']]
        personality = PersonaPersonality[data['personality_type']]
        
        persona = AIPersona(
            persona_code=data['persona_code'],
            name=data['name'],
            name_reading=data.get('name_reading'),
            age=data.get('age'),
            gender=data.get('gender'),
            industry=industry,
            role=role,
            years_experience=data.get('years_experience', 5),
            company_size=data.get('company_size'),
            personality_type=personality,
            communication_style=data.get('communication_style', {}),
            stress_triggers=data.get('stress_triggers', []),
            motivation_factors=data.get('motivation_factors', []),
            background_story=data.get('background_story'),
            current_challenges=data.get('current_challenges', {}),
            goals=data.get('goals', {}),
            expertise_areas=data.get('expertise_areas', []),
            technical_skills=data.get('technical_skills', {}),
            soft_skills=data.get('soft_skills', {}),
            speech_patterns=data.get('speech_patterns', []),
            vocabulary_level=data.get('vocabulary_level', 'professional'),
            response_speed=data.get('response_speed', 'moderate'),
            humor_level=data.get('humor_level', 0.3)
        )
        
        return persona
    
    def _update_persona(self, persona: AIPersona, data: Dict):
        """既存のペルソナを更新"""
        # 基本情報の更新
        persona.name = data['name']
        persona.name_reading = data.get('name_reading')
        persona.age = data.get('age')
        persona.gender = data.get('gender')
        
        # その他の属性も同様に更新
        persona.communication_style = data.get('communication_style', {})
        persona.stress_triggers = data.get('stress_triggers', [])
        persona.motivation_factors = data.get('motivation_factors', [])
        persona.background_story = data.get('background_story')
        persona.current_challenges = data.get('current_challenges', {})
        persona.goals = data.get('goals', {})
        persona.expertise_areas = data.get('expertise_areas', [])
        persona.technical_skills = data.get('technical_skills', {})
        persona.soft_skills = data.get('soft_skills', {})
        persona.speech_patterns = data.get('speech_patterns', [])
        persona.vocabulary_level = data.get('vocabulary_level', 'professional')
        persona.response_speed = data.get('response_speed', 'moderate')
        persona.humor_level = data.get('humor_level', 0.3)
    
    def get_persona_for_scenario(self, scenario_id: int, 
                               difficulty_preference: str = 'auto') -> Optional[AIPersona]:
        """シナリオに適したペルソナを選択"""
        # まずシナリオ専用の設定があるか確認
        config = PersonaScenarioConfig.query.filter_by(
            scenario_id=scenario_id
        ).first()
        
        if config:
            return config.persona
        
        # なければシナリオの内容に基づいて適切なペルソナを選択
        from models import Scenario
        scenario = Scenario.query.get(scenario_id)
        if not scenario:
            return None
        
        # シナリオのカテゴリと難易度に基づいて選択
        suitable_personas = self._find_suitable_personas(
            scenario.category,
            scenario.difficulty,
            difficulty_preference
        )
        
        if suitable_personas:
            # ランダムに選択（将来的にはより高度なマッチングロジック）
            import random
            return random.choice(suitable_personas)
        
        # デフォルトペルソナを返す
        return self._get_default_persona()
    
    def _find_suitable_personas(self, category: str, 
                              difficulty: Any, 
                              preference: str) -> List[AIPersona]:
        """カテゴリと難易度に基づいて適切なペルソナを検索"""
        query = AIPersona.query.filter_by(is_active=True)
        
        # カテゴリに基づくフィルタリング
        if 'プロジェクト' in category or 'チーム' in category:
            query = query.filter(AIPersona.role.in_([
                PersonaRole.MANAGER, PersonaRole.TEAM_LEAD
            ]))
        elif '顧客' in category or '営業' in category:
            query = query.filter(AIPersona.industry == PersonaIndustry.SALES)
        elif '新人' in category or '指導' in category:
            query = query.filter(AIPersona.role.in_([
                PersonaRole.JUNIOR, PersonaRole.MENTOR
            ]))
        
        return query.all()
    
    def _get_default_persona(self) -> Optional[AIPersona]:
        """デフォルトのペルソナを取得"""
        return AIPersona.query.filter_by(
            persona_code='IT_MANAGER_ANALYTICAL'
        ).first()
    
    def create_persona_prompt(self, persona: AIPersona, 
                            scenario_context: Dict,
                            user_message: str,
                            conversation_history: List[Dict]) -> str:
        """ペルソナに基づいた応答生成プロンプトを作成"""
        # ペルソナの現在の感情状態を推定
        emotional_state = self._estimate_emotional_state(
            persona, conversation_history, user_message
        )
        
        # 関連する記憶を取得
        relevant_memories = self._retrieve_relevant_memories(
            persona.id, scenario_context.get('user_id'), user_message
        )
        
        prompt = f"""あなたは{persona.name}（{persona.name_reading}）として振る舞ってください。

【基本情報】
- 年齢: {persona.age}歳
- 業界: {persona.industry.value}
- 役職: {persona.role.value}
- 経験年数: {persona.years_experience}年
- 性格: {persona.personality_type.value}

【背景】
{persona.background_story}

【現在の課題】
{self._format_list(persona.current_challenges)}

【コミュニケーションスタイル】
- フォーマル度: {persona.communication_style.get('formal', 0.5) * 100}%
- 技術的な話し方: {persona.communication_style.get('technical', 0.5) * 100}%
- 共感的な態度: {persona.communication_style.get('empathetic', 0.5) * 100}%

【現在の感情状態】
{emotional_state.value}

【よく使う表現】
{self._format_list(persona.speech_patterns[:3])}

【関連する記憶】
{self._format_memories(relevant_memories)}

【シナリオコンテキスト】
{scenario_context.get('description', '')}

【会話履歴】
{self._format_conversation_history(conversation_history[-5:])}

【ユーザーの発言】
{user_message}

上記の人物設定に基づいて、自然で一貫性のある応答を生成してください。
感情状態と性格を反映し、適切な口調で話してください。"""
        
        return prompt
    
    def save_interaction_memory(self, persona_id: int, user_id: int,
                              session_id: int, message: str,
                              memory_type: str = 'interaction'):
        """インタラクションの記憶を保存"""
        memory = PersonaMemory(
            persona_id=persona_id,
            user_id=user_id,
            session_id=session_id,
            memory_type=memory_type,
            content=message,
            importance_score=self._calculate_importance(message),
            context_tags=self._extract_context_tags(message),
            occurred_at=datetime.utcnow()
        )
        
        db.session.add(memory)
        db.session.commit()
        
        # キャッシュをクリア
        if self.redis_client:
            cache_key = f"persona_memories:{persona_id}:{user_id}"
            self.redis_client.delete(cache_key)
    
    def update_interaction_stats(self, user_id: int, persona_id: int,
                               session_id: int, interaction_data: Dict):
        """インタラクション統計を更新"""
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
                rapport_level=0.5
            )
            db.session.add(interaction)
        
        # 統計情報の更新
        interaction.total_exchanges = interaction_data.get('total_exchanges', 0)
        interaction.user_word_count = interaction_data.get('user_word_count', 0)
        interaction.persona_word_count = interaction_data.get('persona_word_count', 0)
        interaction.interaction_quality = self._calculate_interaction_quality(
            interaction_data
        )
        
        # ラポールレベルの更新（簡易版）
        if interaction_data.get('positive_interaction'):
            interaction.rapport_level = min(1.0, interaction.rapport_level + 0.05)
        elif interaction_data.get('negative_interaction'):
            interaction.rapport_level = max(0.0, interaction.rapport_level - 0.05)
        
        db.session.commit()
    
    def _estimate_emotional_state(self, persona: AIPersona,
                                history: List[Dict],
                                current_message: str) -> EmotionalState:
        """会話履歴と現在のメッセージから感情状態を推定"""
        # ストレストリガーのチェック
        if persona.stress_triggers:
            for trigger in persona.stress_triggers:
                if trigger.lower() in current_message.lower():
                    return EmotionalState.STRESSED
        
        # ポジティブなキーワードのチェック
        positive_keywords = ['ありがとう', '素晴らしい', '良い', '成功']
        if any(keyword in current_message for keyword in positive_keywords):
            return EmotionalState.HAPPY
        
        # デフォルトは中立
        return EmotionalState.NEUTRAL
    
    def _retrieve_relevant_memories(self, persona_id: int,
                                  user_id: int,
                                  current_message: str) -> List[PersonaMemory]:
        """関連する記憶を取得"""
        # キャッシュチェック
        if self.redis_client:
            cache_key = f"persona_memories:{persona_id}:{user_id}"
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                memories_data = json.loads(cached_data)
                return [PersonaMemory(**m) for m in memories_data]
        
        # データベースから取得
        memories = PersonaMemory.query.filter(
            and_(
                PersonaMemory.persona_id == persona_id,
                PersonaMemory.user_id == user_id,
                or_(
                    PersonaMemory.expires_at.is_(None),
                    PersonaMemory.expires_at > datetime.utcnow()
                )
            )
        ).order_by(
            desc(PersonaMemory.importance_score),
            desc(PersonaMemory.occurred_at)
        ).limit(5).all()
        
        # キャッシュに保存
        if self.redis_client and memories:
            memories_data = [
                {
                    'content': m.content,
                    'memory_type': m.memory_type,
                    'importance_score': m.importance_score
                }
                for m in memories
            ]
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(memories_data, ensure_ascii=False)
            )
        
        return memories
    
    def _calculate_importance(self, message: str) -> float:
        """メッセージの重要度を計算（0.0-1.0）"""
        # 簡易的な実装
        importance = 0.5
        
        # 重要なキーワード
        important_keywords = [
            'プロジェクト', '締切', '問題', '重要', '緊急',
            '決定', '承認', '予算', 'ミス', 'エラー'
        ]
        
        for keyword in important_keywords:
            if keyword in message:
                importance += 0.1
        
        return min(1.0, importance)
    
    def _extract_context_tags(self, message: str) -> List[str]:
        """メッセージからコンテキストタグを抽出"""
        tags = []
        
        # タグ候補
        tag_keywords = {
            'project': ['プロジェクト', '案件', 'PJ'],
            'deadline': ['締切', '期限', 'デッドライン'],
            'meeting': ['会議', 'ミーティング', '打ち合わせ'],
            'problem': ['問題', '課題', 'トラブル'],
            'success': ['成功', '完了', '達成']
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in message for keyword in keywords):
                tags.append(tag)
        
        return tags
    
    def _calculate_interaction_quality(self, interaction_data: Dict) -> float:
        """インタラクションの質を計算"""
        quality_score = 0.5
        
        # メッセージの長さバランス
        user_words = interaction_data.get('user_word_count', 0)
        persona_words = interaction_data.get('persona_word_count', 0)
        
        if user_words > 0 and persona_words > 0:
            balance = min(user_words, persona_words) / max(user_words, persona_words)
            quality_score += balance * 0.2
        
        # やり取りの回数
        exchanges = interaction_data.get('total_exchanges', 0)
        if exchanges >= 10:
            quality_score += 0.2
        elif exchanges >= 5:
            quality_score += 0.1
        
        return min(1.0, quality_score)
    
    def _format_list(self, items: Any) -> str:
        """リストを読みやすい形式にフォーマット"""
        if isinstance(items, list):
            return '\n'.join(f"- {item}" for item in items)
        elif isinstance(items, dict):
            return '\n'.join(f"- {k}: {v}" for k, v in items.items())
        return str(items)
    
    def _format_memories(self, memories: List[PersonaMemory]) -> str:
        """記憶を読みやすい形式にフォーマット"""
        if not memories:
            return "（関連する記憶なし）"
        
        formatted = []
        for memory in memories:
            formatted.append(f"- [{memory.memory_type}] {memory.content}")
        
        return '\n'.join(formatted)
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """会話履歴をフォーマット"""
        if not history:
            return "（会話履歴なし）"
        
        formatted = []
        for entry in history:
            role = "ユーザー" if entry.get('role') == 'user' else "自分"
            formatted.append(f"{role}: {entry.get('content', '')}")
        
        return '\n'.join(formatted)


# サービスインスタンス
persona_service = PersonaService()