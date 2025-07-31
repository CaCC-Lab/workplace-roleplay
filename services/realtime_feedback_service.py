"""
リアルタイムフィードバック生成サービス

ペルソナシステムと統合して、会話中にリアルタイムでフィードバックを生成
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from models import AIPersona, PersonaIndustry, PersonaRole

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """フィードバックの種類"""
    SUGGESTION = "suggestion"
    PRAISE = "praise"
    GUIDANCE = "guidance"
    WARNING = "warning"


class ConversationFlow(str, Enum):
    """会話の流れの状態"""
    ACTIVE_DISCUSSION = "active_discussion"
    QUESTION_ASKED = "question_asked"
    UNKNOWN = "unknown"


@dataclass
class FeedbackConfig:
    """フィードバック生成の設定"""
    # 関連度の閾値設定
    MIN_RELEVANCE_THRESHOLD: float = 0.2
    EXPERTISE_EXACT_MATCH_SCORE: float = 0.3
    EXPERTISE_PARTIAL_MATCH_SCORE: float = 0.2
    INDUSTRY_KEYWORD_SCORE: float = 0.2
    ROLE_KEYWORD_SCORE: float = 0.2
    
    # 確信度調整
    CONFIDENCE_BOOST: float = 0.2
    
    # 会話履歴の最小長
    MIN_CONVERSATION_HISTORY_LENGTH: int = 2
    
    # 単語の最小長（部分一致検索用）
    MIN_WORD_LENGTH_FOR_MATCH: int = 2
    
    # 優先度調整の閾値
    HIGH_RELEVANCE_THRESHOLD: float = 0.8
    LOW_RELEVANCE_THRESHOLD: float = 0.4
    
    # フィードバックタイプ別の基本優先度
    FEEDBACK_TYPE_PRIORITIES: Dict[str, int] = None
    
    def __post_init__(self):
        if self.FEEDBACK_TYPE_PRIORITIES is None:
            self.FEEDBACK_TYPE_PRIORITIES = {
                FeedbackType.WARNING: 5,
                FeedbackType.GUIDANCE: 4,
                FeedbackType.SUGGESTION: 3,
                FeedbackType.PRAISE: 2
            }


@dataclass
class KeywordMaps:
    """業界・役職別キーワードマップ"""
    INDUSTRY_KEYWORDS: Dict[PersonaIndustry, List[str]] = None
    ROLE_KEYWORDS: Dict[PersonaRole, List[str]] = None
    
    def __post_init__(self):
        if self.INDUSTRY_KEYWORDS is None:
            self.INDUSTRY_KEYWORDS = {
                PersonaIndustry.IT: ['システム', 'プロジェクト', '開発', 'アプリ', 'データベース', 'セキュリティ'],
                PersonaIndustry.SALES: ['営業', '販売', '顧客', 'クライアント', '売上', '契約'],
                PersonaIndustry.HEALTHCARE: ['患者', '医療', '看護', '治療', '診断', 'ケア'],
                PersonaIndustry.MANUFACTURING: ['製造', '生産', '品質', '工場', '安全', '効率'],
                PersonaIndustry.FINANCE: ['財務', '予算', '会計', '投資', 'コスト', '収益']
            }
        
        if self.ROLE_KEYWORDS is None:
            self.ROLE_KEYWORDS = {
                PersonaRole.MANAGER: ['管理', '判断', '決定', '責任', 'リーダー'],
                PersonaRole.SENIOR: ['経験', 'アドバイス', '指導', 'ノウハウ'],
                PersonaRole.JUNIOR: ['学習', '質問', 'サポート', '成長'],
                PersonaRole.TEAM_LEAD: ['チーム', 'メンバー', '連携', '調整'],
                PersonaRole.MENTOR: ['指導', '教育', '成長', 'スキル']
            }


@dataclass
class FeedbackResult:
    """フィードバック結果のデータクラス"""
    content: str
    feedback_type: str  # suggestion, praise, guidance, warning
    confidence_score: float  # 0.0-1.0
    timing_priority: int  # 1-5 (5が最高優先度)
    persona_specialty_relevance: float  # 0.0-1.0


class RealtimeFeedbackService:
    """リアルタイムフィードバック生成の中核サービス"""
    
    def __init__(self, config: Optional[FeedbackConfig] = None, 
                 keyword_maps: Optional[KeywordMaps] = None):
        """
        サービスの初期化
        
        Args:
            config: フィードバック生成の設定
            keyword_maps: 業界・役職別キーワードマップ
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or FeedbackConfig()
        self.keyword_maps = keyword_maps or KeywordMaps()
        
    def generate_feedback(self, persona: AIPersona, conversation_context: Dict[str, Any]) -> Optional[FeedbackResult]:
        """
        ペルソナの専門性に基づいてフィードバックを生成
        
        Args:
            persona: AIペルソナオブジェクト
            conversation_context: 会話コンテキスト
            
        Returns:
            FeedbackResult: 生成されたフィードバック、または None
            
        Raises:
            ValueError: ペルソナまたはコンテキストが無効な場合
        """
        # 入力検証
        if not self._validate_inputs(persona, conversation_context):
            return None
            
        user_message = conversation_context.get('user_message', '').strip()
        if not user_message:
            return None
        
        try:
            # フィードバック生成の各段階を実行
            relevance = self._calculate_specialty_relevance(persona, user_message)
            
            if not self._meets_relevance_threshold(relevance):
                return None
            
            if not self._is_appropriate_timing(conversation_context):
                return None
            
            return self._create_feedback_result(persona, conversation_context, relevance)
            
        except Exception as e:
            self.logger.error(f"フィードバック生成中にエラーが発生: {str(e)}")
            return None
    
    def _validate_inputs(self, persona: AIPersona, conversation_context: Dict[str, Any]) -> bool:
        """入力パラメータの妥当性を検証"""
        if not persona:
            self.logger.warning("ペルソナが提供されていません")
            return False
        
        if not conversation_context:
            self.logger.warning("会話コンテキストが提供されていません")
            return False
        
        return True
    
    def _meets_relevance_threshold(self, relevance: float) -> bool:
        """関連度が閾値を満たすかチェック"""
        return relevance >= self.config.MIN_RELEVANCE_THRESHOLD
    
    def _create_feedback_result(self, persona: AIPersona, conversation_context: Dict[str, Any], 
                              relevance: float) -> Optional[FeedbackResult]:
        """フィードバック結果を作成"""
        user_message = conversation_context.get('user_message', '')
        
        feedback_content = self._generate_feedback_content(persona, conversation_context, relevance)
        if not feedback_content:
            return None
            
        feedback_type = self._determine_feedback_type(user_message, persona)
        confidence = self._calculate_confidence_score(relevance)
        priority = self._calculate_priority(feedback_type, relevance)
        
        return FeedbackResult(
            content=feedback_content,
            feedback_type=feedback_type,
            confidence_score=confidence,
            timing_priority=priority,
            persona_specialty_relevance=relevance
        )
    
    def _calculate_confidence_score(self, relevance: float) -> float:
        """確信度スコアを計算"""
        return min(relevance + self.config.CONFIDENCE_BOOST, 1.0)
    
    def _calculate_specialty_relevance(self, persona: AIPersona, user_message: str) -> float:
        """ペルソナの専門性とユーザーメッセージの関連度を計算"""
        relevance_score = 0.0
        message_lower = user_message.lower()
        
        # 専門分野キーワードとの一致をチェック
        relevance_score += self._calculate_expertise_relevance(persona.expertise_areas, message_lower)
        
        # 業界固有のキーワードをチェック
        relevance_score += self._calculate_keyword_relevance(
            self.keyword_maps.INDUSTRY_KEYWORDS.get(persona.industry, []), 
            message_lower, 
            self.config.INDUSTRY_KEYWORD_SCORE
        )
        
        # 役職に関連するキーワードをチェック
        relevance_score += self._calculate_keyword_relevance(
            self.keyword_maps.ROLE_KEYWORDS.get(persona.role, []), 
            message_lower, 
            self.config.ROLE_KEYWORD_SCORE
        )
        
        return min(relevance_score, 1.0)
    
    def _calculate_expertise_relevance(self, expertise_areas: Optional[List[str]], message_lower: str) -> float:
        """専門分野の関連度を計算"""
        if not expertise_areas:
            return 0.0
            
        relevance_score = 0.0
        
        for expertise in expertise_areas:
            expertise_lower = expertise.lower()
            
            # 完全一致
            if expertise_lower in message_lower:
                relevance_score += self.config.EXPERTISE_EXACT_MATCH_SCORE
            else:
                # 部分一致（キーワードを分割して検索）
                expertise_words = expertise_lower.split()
                for word in expertise_words:
                    if len(word) > self.config.MIN_WORD_LENGTH_FOR_MATCH and word in message_lower:
                        relevance_score += self.config.EXPERTISE_PARTIAL_MATCH_SCORE
                        break
        
        return relevance_score
    
    def _calculate_keyword_relevance(self, keywords: List[str], message_lower: str, score_per_match: float) -> float:
        """キーワードリストの関連度を計算"""
        relevance_score = 0.0
        
        for keyword in keywords:
            if keyword.lower() in message_lower:
                relevance_score += score_per_match
        
        return relevance_score
    
    
    def _is_appropriate_timing(self, conversation_context: Dict[str, Any]) -> bool:
        """フィードバックのタイミングが適切かを判定"""
        conversation_flow = conversation_context.get('conversation_flow', ConversationFlow.UNKNOWN)
        
        # 会話の流れに基づく判定
        if conversation_flow == ConversationFlow.ACTIVE_DISCUSSION:
            return False
        
        if conversation_flow == ConversationFlow.QUESTION_ASKED:
            return True
        
        # 会話履歴の長さをチェック
        history = conversation_context.get('conversation_history', [])
        return len(history) >= self.config.MIN_CONVERSATION_HISTORY_LENGTH
    
    def _generate_feedback_content(self, persona: AIPersona, conversation_context: Dict[str, Any], 
                                 relevance: float) -> str:
        """フィードバック内容を生成"""
        user_message = conversation_context.get('user_message', '')
        
        # ペルソナのコミュニケーションスタイルを取得
        communication_style = self._extract_communication_style(persona)
        
        # メッセージのパターンに基づいてフィードバックを生成
        for pattern_generator in self._get_feedback_generators():
            feedback = pattern_generator(persona, user_message, communication_style)
            if feedback:
                return feedback
        
        # デフォルトのフィードバック
        return self._generate_default_feedback(communication_style)
    
    def _extract_communication_style(self, persona: AIPersona) -> Dict[str, float]:
        """ペルソナのコミュニケーションスタイルを抽出"""
        if not persona.communication_style:
            return {'formal': 0.5, 'empathetic': 0.5, 'technical': 0.5}
        
        return {
            'formal': persona.communication_style.get('formal', 0.5),
            'empathetic': persona.communication_style.get('empathetic', 0.5),
            'technical': persona.communication_style.get('technical', 0.5)
        }
    
    def _get_feedback_generators(self) -> List[callable]:
        """フィードバック生成関数のリストを取得"""
        return [
            self._generate_project_feedback,
            self._generate_question_feedback,
            self._generate_problem_feedback
        ]
    
    def _generate_project_feedback(self, persona: AIPersona, user_message: str, 
                                 communication_style: Dict[str, float]) -> Optional[str]:
        """プロジェクト関連のフィードバックを生成"""
        if 'プロジェクト' not in user_message or persona.industry != PersonaIndustry.IT:
            return None
        
        base_feedback = "プロジェクト管理の観点から、"
        
        if communication_style['formal'] > 0.7:
            return f"{base_feedback}段階的なアプローチを検討されることをお勧めします。"
        else:
            return f"{base_feedback}ステップバイステップで進めてみてはいかがでしょうか。"
    
    def _generate_question_feedback(self, persona: AIPersona, user_message: str, 
                                  communication_style: Dict[str, float]) -> Optional[str]:
        """質問関連のフィードバックを生成"""
        if not any(keyword in user_message for keyword in ['質問', '教えて']):
            return None
        
        if communication_style['empathetic'] > 0.7:
            return "とても良い質問ですね。まずは基本的な考え方から整理してみましょう。"
        else:
            return "この点について、まず基本的な原則を確認することが重要です。"
    
    def _generate_problem_feedback(self, persona: AIPersona, user_message: str, 
                                 communication_style: Dict[str, float]) -> Optional[str]:
        """問題関連のフィードバックを生成"""
        if not any(keyword in user_message for keyword in ['問題', '困って']):
            return None
        
        if persona.role in [PersonaRole.MANAGER, PersonaRole.TEAM_LEAD]:
            return "問題解決には、まず現状の整理と原因分析から始めることが効果的です。"
        else:
            return "そのような状況では、経験豊富な方に相談することも有効な手段です。"
    
    def _generate_default_feedback(self, communication_style: Dict[str, float]) -> str:
        """デフォルトのフィードバックを生成"""
        if communication_style['formal'] > 0.7:
            return "会話の整理と次のステップの明確化をお勧めいたします。"
        else:
            return "会話の流れを整理して、次のステップを明確にしてみましょう。"
    
    def _determine_feedback_type(self, user_message: str, persona: AIPersona) -> str:
        """フィードバックタイプを決定"""
        message_lower = user_message.lower()
        
        # キーワードパターンに基づく判定
        feedback_patterns = {
            FeedbackType.GUIDANCE: ['質問', '教えて', '？'],
            FeedbackType.SUGGESTION: ['問題', '困って', 'エラー'],
            FeedbackType.PRAISE: ['良い', '成功', '完了'],
            FeedbackType.WARNING: ['危険', '注意']
        }
        
        for feedback_type, patterns in feedback_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                return feedback_type.value
        
        return FeedbackType.SUGGESTION.value
    
    def _calculate_priority(self, feedback_type: str, relevance: float) -> int:
        """フィードバックの優先度を計算"""
        base_priority = self.config.FEEDBACK_TYPE_PRIORITIES.get(feedback_type, 3)
        
        # 関連度に基づいて調整
        if relevance > self.config.HIGH_RELEVANCE_THRESHOLD:
            return min(base_priority + 1, 5)
        elif relevance < self.config.LOW_RELEVANCE_THRESHOLD:
            return max(base_priority - 1, 1)
        
        return base_priority


# サービスインスタンス（デフォルト設定で初期化）
realtime_feedback_service = RealtimeFeedbackService()