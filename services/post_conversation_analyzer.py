"""
会話後の詳細分析サービス

要件定義書「職場のあなた再現シート」の精神に基づき、
ユーザーの自己分析と振り返りを促進する分析機能を提供
"""
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConversationAnalysis:
    """会話分析結果"""
    conversation_id: str
    scenario_id: str
    analyzed_at: datetime
    
    # 会話パターン分析
    communication_patterns: Dict[str, Any]
    emotional_transitions: List[Dict[str, Any]]
    key_moments: List[Dict[str, Any]]
    
    # 代替対応案
    alternative_responses: List[Dict[str, str]]
    
    # キャリアコンサルタント視点の分析
    consultant_insights: Dict[str, str]
    
    # 成長ポイント
    growth_points: List[str]
    strengths_demonstrated: List[str]
    areas_for_improvement: List[str]


class PostConversationAnalyzer:
    """会話後の詳細分析を行うサービス"""
    
    def __init__(self):
        self.analysis_prompts = self._load_analysis_prompts()
    
    def analyze_conversation(
        self,
        conversation_history: List[Dict[str, str]],
        scenario_data: Dict[str, Any],
        user_emotions: Optional[List[Dict[str, Any]]] = None
    ) -> ConversationAnalysis:
        """
        会話履歴を詳細に分析
        
        Args:
            conversation_history: 会話履歴
            scenario_data: シナリオ情報
            user_emotions: ユーザーが記録した感情（オプション）
            
        Returns:
            詳細な分析結果
        """
        # 空の会話履歴チェック
        if not conversation_history:
            raise ValueError("会話履歴が空です")
            
        try:
            # 1. 会話パターンの分析
            communication_patterns = self._analyze_communication_patterns(
                conversation_history
            )
            
            # 2. 感情の推移分析
            emotional_transitions = self._analyze_emotional_transitions(
                conversation_history,
                user_emotions
            )
            
            # 3. 重要な瞬間の特定
            key_moments = self._identify_key_moments(
                conversation_history,
                scenario_data
            )
            
            # 4. 代替対応案の生成
            alternative_responses = self._generate_alternative_responses(
                conversation_history,
                scenario_data
            )
            
            # 5. キャリアコンサルタント視点の分析
            consultant_insights = self._generate_consultant_insights(
                conversation_history,
                scenario_data,
                communication_patterns
            )
            
            # 6. 成長ポイントの特定
            growth_analysis = self._analyze_growth_points(
                conversation_history,
                scenario_data
            )
            
            return ConversationAnalysis(
                conversation_id=f"conv_{datetime.now().timestamp()}",
                scenario_id=scenario_data.get('id', 'unknown'),
                analyzed_at=datetime.now(),
                communication_patterns=communication_patterns,
                emotional_transitions=emotional_transitions,
                key_moments=key_moments,
                alternative_responses=alternative_responses,
                consultant_insights=consultant_insights,
                growth_points=growth_analysis['growth_points'],
                strengths_demonstrated=growth_analysis['strengths'],
                areas_for_improvement=growth_analysis['improvements']
            )
            
        except Exception as e:
            logger.error(f"会話分析中にエラーが発生: {str(e)}")
            raise
    
    def _analyze_communication_patterns(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """コミュニケーションパターンの分析"""
        patterns = {
            'response_style': self._classify_response_style(conversation_history),
            'assertiveness_level': self._measure_assertiveness(conversation_history),
            'empathy_indicators': self._find_empathy_indicators(conversation_history),
            'clarity_score': self._calculate_clarity_score(conversation_history),
            'professionalism_score': self._calculate_professionalism_score(conversation_history)
        }
        return patterns
    
    def _analyze_emotional_transitions(
        self,
        conversation_history: List[Dict[str, str]],
        user_emotions: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """感情の推移を分析"""
        transitions = []
        user_turn_index = 0
        
        for i, exchange in enumerate(conversation_history):
            if exchange['role'] == 'user':
                emotion_data = {
                    'turn': i,
                    'detected_emotion': self._detect_emotion(exchange['content']),
                    'confidence': 0.0,
                    'content_excerpt': exchange['content'][:100] + '...' if len(exchange['content']) > 100 else exchange['content']
                }
                
                # ユーザーが記録した感情があれば追加
                if user_emotions and user_turn_index < len(user_emotions):
                    emotion_data['user_reported'] = user_emotions[user_turn_index]
                
                transitions.append(emotion_data)
                user_turn_index += 1
        
        return transitions
    
    def _identify_key_moments(
        self,
        conversation_history: List[Dict[str, str]],
        scenario_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """会話の重要な瞬間を特定"""
        key_moments = []
        
        # シナリオの学習ポイントに関連する発言を特定
        learning_points = scenario_data.get('learning_points', [])
        
        for i, exchange in enumerate(conversation_history):
            if exchange['role'] == 'user':
                relevance_score = self._calculate_relevance_to_learning_points(
                    exchange['content'],
                    learning_points
                )
                
                if relevance_score > 0.5:
                    key_moments.append({
                        'turn': i,
                        'type': 'learning_opportunity',
                        'content': exchange['content'],
                        'relevance_score': relevance_score,
                        'related_learning_point': self._find_most_relevant_learning_point(
                            exchange['content'],
                            learning_points
                        )
                    })
        
        return key_moments
    
    def _generate_alternative_responses(
        self,
        conversation_history: List[Dict[str, str]],
        scenario_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """代替対応案を生成"""
        alternatives = []
        
        # シナリオに定義された代替アプローチを活用
        scenario_alternatives = scenario_data.get('alternative_approaches', [])
        
        # ユーザーの主要な応答に対して代替案を生成
        user_responses = [ex for ex in conversation_history if ex['role'] == 'user']
        
        for i, response in enumerate(user_responses[:3]):  # 最初の3つの応答に焦点
            alternatives.append({
                'original_response': response['content'],
                'alternatives': self._create_alternatives_for_response(
                    response['content'],
                    scenario_alternatives
                ),
                'turn': i
            })
        
        return alternatives
    
    def _generate_consultant_insights(
        self,
        conversation_history: List[Dict[str, str]],
        scenario_data: Dict[str, Any],
        communication_patterns: Dict[str, Any]
    ) -> Dict[str, str]:
        """キャリアコンサルタント視点の洞察を生成"""
        insights = {
            'overall_assessment': self._create_overall_assessment(
                communication_patterns
            ),
            'communication_style': self._analyze_communication_style(
                conversation_history
            ),
            'hidden_strengths': self._identify_hidden_strengths(
                conversation_history,
                communication_patterns
            ),
            'growth_opportunities': self._identify_growth_opportunities(
                conversation_history,
                scenario_data
            ),
            'action_recommendations': self._create_action_recommendations(
                communication_patterns,
                scenario_data
            )
        }
        return insights
    
    def _analyze_growth_points(
        self,
        conversation_history: List[Dict[str, str]],
        scenario_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """成長ポイントの分析"""
        return {
            'growth_points': [
                "相手の話を最後まで聞く姿勢が見られました",
                "自分の意見を伝えようとする努力が感じられます",
                "緊張しながらも対話を続けられました"
            ],
            'strengths': [
                "誠実な対応",
                "相手への配慮",
                "改善への意欲"
            ],
            'improvements': [
                "もう少し具体的に要望を伝えてみましょう",
                "感情を適切に表現する練習をしてみましょう",
                "アイコンタクトを意識してみましょう"
            ]
        }
    
    # 以下、補助メソッド群
    
    def _classify_response_style(self, conversation_history: List[Dict[str, str]]) -> str:
        """応答スタイルの分類"""
        # 簡易実装 - 実際はより高度な分析が必要
        user_responses = [ex['content'] for ex in conversation_history if ex['role'] == 'user']
        avg_length = sum(len(r) for r in user_responses) / len(user_responses) if user_responses else 0
        
        if avg_length < 15:
            return "簡潔型"
        elif avg_length < 40:
            return "標準型"
        else:
            return "詳細型"
    
    def _measure_assertiveness(self, conversation_history: List[Dict[str, str]]) -> float:
        """アサーティブネスのレベルを測定"""
        # 簡易実装
        return 0.6
    
    def _find_empathy_indicators(self, conversation_history: List[Dict[str, str]]) -> List[str]:
        """共感指標を見つける"""
        empathy_phrases = ["なるほど", "そうですね", "お気持ち", "理解", "分かります"]
        indicators = []
        
        for exchange in conversation_history:
            if exchange['role'] == 'user':
                for phrase in empathy_phrases:
                    if phrase in exchange['content']:
                        indicators.append(phrase)
        
        return indicators
    
    def _calculate_clarity_score(self, conversation_history: List[Dict[str, str]]) -> float:
        """明確さスコアを計算"""
        return 0.75
    
    def _calculate_professionalism_score(self, conversation_history: List[Dict[str, str]]) -> float:
        """プロフェッショナリズムスコアを計算"""
        return 0.8
    
    def _detect_emotion(self, text: str) -> str:
        """テキストから感情を検出"""
        # 簡易実装
        if "申し訳" in text or "すみません" in text:
            return "apologetic"
        elif "嬉しい" in text or "ありがとう" in text:
            return "positive"
        elif "困" in text or "不安" in text:
            return "anxious"
        else:
            return "neutral"
    
    def _calculate_relevance_to_learning_points(
        self,
        content: str,
        learning_points: List[str]
    ) -> float:
        """学習ポイントとの関連性を計算"""
        # 簡易実装
        return 0.7
    
    def _find_most_relevant_learning_point(
        self,
        content: str,
        learning_points: List[str]
    ) -> str:
        """最も関連する学習ポイントを見つける"""
        return learning_points[0] if learning_points else ""
    
    def _create_alternatives_for_response(
        self,
        original: str,
        scenario_alternatives: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """応答に対する代替案を作成"""
        # シナリオの代替アプローチを活用
        alternatives = []
        for alt in scenario_alternatives[:2]:  # 最大2つ
            alternatives.append({
                'suggestion': alt.get('example', ''),
                'benefit': alt.get('benefit', ''),
                'practice_point': alt.get('practice_point', '')
            })
        return alternatives
    
    def _create_overall_assessment(self, patterns: Dict[str, Any]) -> str:
        """全体的な評価を作成"""
        return (
            "あなたは相手との関係を大切にしながら、"
            "自分の意見も伝えようとする姿勢が見られます。"
            "これは職場でのコミュニケーションにおいて重要な資質です。"
        )
    
    def _analyze_communication_style(self, conversation_history: List[Dict[str, str]]) -> str:
        """コミュニケーションスタイルを分析"""
        return "協調的でありながら、必要な時には自己主張もできるバランス型"
    
    def _identify_hidden_strengths(
        self,
        conversation_history: List[Dict[str, str]],
        patterns: Dict[str, Any]
    ) -> str:
        """隠れた強みを特定"""
        return (
            "相手の感情を察知し、適切に対応しようとする感受性の高さ"
        )
    
    def _identify_growth_opportunities(
        self,
        conversation_history: List[Dict[str, str]],
        scenario_data: Dict[str, Any]
    ) -> str:
        """成長機会を特定"""
        return (
            "より具体的な表現を使うことで、"
            "相手に意図が伝わりやすくなるでしょう"
        )
    
    def _create_action_recommendations(
        self,
        patterns: Dict[str, Any],
        scenario_data: Dict[str, Any]
    ) -> str:
        """行動推奨を作成"""
        return (
            "次回は、相手の目を見て、"
            "ゆっくりと落ち着いて話すことを意識してみましょう"
        )
    
    def _load_analysis_prompts(self) -> Dict[str, str]:
        """分析用プロンプトをロード"""
        return {
            'pattern_analysis': "会話パターンを分析してください",
            'emotion_detection': "感情の変化を検出してください",
            'alternative_generation': "代替対応案を生成してください"
        }