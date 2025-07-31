"""
最小限のヒントサービス

要件定義書の精神に基づき、ユーザーが本当に困った時だけ
使える控えめなヒント機能を提供
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MinimalHintService:
    """最小限のヒントを提供するサービス"""
    
    def __init__(self):
        self.hint_templates = self._load_hint_templates()
    
    def generate_hint(
        self,
        scenario_id: str,
        scenario_data: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
        hint_number: int
    ) -> Dict[str, Any]:
        """
        状況に応じた最小限のヒントを生成
        
        Args:
            scenario_id: シナリオID
            scenario_data: シナリオ情報
            conversation_history: 会話履歴
            hint_number: 何回目のヒントか（1-3）
            
        Returns:
            ヒント情報
        """
        try:
            # 会話の進行状況を分析
            conversation_state = self._analyze_conversation_state(
                conversation_history,
                scenario_data
            )
            
            # ヒントのレベルを決定（回数が増えるごとに具体的に）
            hint_level = self._determine_hint_level(hint_number)
            
            # 適切なヒントを生成
            hint = self._create_hint(
                conversation_state,
                scenario_data,
                hint_level
            )
            
            return hint
            
        except Exception as e:
            logger.error(f"ヒント生成エラー: {str(e)}")
            return self._create_fallback_hint()
    
    def _analyze_conversation_state(
        self,
        conversation_history: List[Dict[str, str]],
        scenario_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """会話の進行状況を分析"""
        user_messages = [
            msg for msg in conversation_history 
            if msg['role'] == 'user'
        ]
        
        # 会話の段階を判定
        if len(user_messages) == 0:
            stage = 'initial'
        elif len(user_messages) == 1:
            stage = 'early'
        elif len(user_messages) < 3:
            stage = 'middle'
        else:
            stage = 'late'
        
        # 最後のAIメッセージから文脈を理解
        last_ai_message = None
        for msg in reversed(conversation_history):
            if msg['role'] == 'assistant':
                last_ai_message = msg['content']
                break
        
        # ユーザーの困っているポイントを推測
        difficulty_point = self._infer_difficulty_point(
            user_messages,
            last_ai_message,
            scenario_data
        )
        
        return {
            'stage': stage,
            'user_message_count': len(user_messages),
            'last_ai_message': last_ai_message,
            'difficulty_point': difficulty_point
        }
    
    def _infer_difficulty_point(
        self,
        user_messages: List[Dict[str, str]],
        last_ai_message: Optional[str],
        scenario_data: Dict[str, Any]
    ) -> str:
        """ユーザーが困っているポイントを推測"""
        # シンプルな推測ロジック
        if not user_messages:
            return 'starting_conversation'
        
        last_user_message = user_messages[-1]['content'] if user_messages else ""
        
        # 謝罪が多い = 自信がない（最初にチェック）
        if last_user_message.count('すみません') >= 1 or last_user_message.count('申し訳') >= 1:
            return 'over_apologizing'
        
        # 質問で返している = 話の進め方が分からない（短い返答より先にチェック）
        if last_user_message.endswith('？') or last_user_message.endswith('?'):
            return 'questioning_back'
        
        # 短い返答 = 何を言えばいいか分からない
        if len(last_user_message) < 20:
            return 'finding_words'
        
        return 'general'
    
    def _determine_hint_level(self, hint_number: int) -> str:
        """ヒントのレベルを決定"""
        if hint_number == 1:
            return 'gentle'  # 優しく方向性を示す
        elif hint_number == 2:
            return 'moderate'  # もう少し具体的に
        else:
            return 'specific'  # かなり具体的に
    
    def _create_hint(
        self,
        conversation_state: Dict[str, Any],
        scenario_data: Dict[str, Any],
        hint_level: str
    ) -> Dict[str, Any]:
        """状況に応じたヒントを作成"""
        difficulty = conversation_state['difficulty_point']
        stage = conversation_state['stage']
        
        # シナリオの学習ポイントを参照
        learning_points = scenario_data.get('learning_points', [])
        
        hint = {
            'type': 'direction',
            'message': '',
            'example': None,
            'considerationPoints': []
        }
        
        # 困っているポイントに応じたヒント
        if difficulty == 'starting_conversation':
            if hint_level == 'gentle':
                hint['message'] = "相手の言葉をよく聞いて、まずは共感を示してみましょう。"
                hint['considerationPoints'] = ["相手の気持ちを想像する", "急いで解決しようとしない"]
            elif hint_level == 'moderate':
                hint['message'] = "「なるほど」「そうですね」など、相手の話を受け止める言葉から始めてみましょう。"
                hint['example'] = "なるほど、それは大変でしたね..."
            else:
                hint['message'] = "相手の状況を理解していることを示してから、あなたの考えを伝えてみましょう。"
                hint['example'] = "お話を聞いて、〇〇な状況だということが分かりました。私からは..."
        
        elif difficulty == 'finding_words':
            if hint_level == 'gentle':
                hint['message'] = "短くても大丈夫です。相手に関心を持っていることを伝えましょう。"
            elif hint_level == 'moderate':
                hint['message'] = "相手の話の中で気になった点について、もう少し詳しく聞いてみるのも良いでしょう。"
                hint['considerationPoints'] = ["具体的に聞く", "yes/noで答えられない質問をする"]
            else:
                hint['message'] = "5W1H（いつ、どこで、誰が、何を、なぜ、どのように）を意識して質問してみましょう。"
                hint['example'] = "それは具体的にどのような状況でしたか？"
                hint['considerationPoints'] = ["具体的な状況を聞く", "相手の話を深掘りする", "理解を示しながら質問する"]
        
        elif difficulty == 'over_apologizing':
            if hint_level == 'gentle':
                hint['message'] = "謝りすぎる必要はありません。前向きな提案をしてみましょう。"
            elif hint_level == 'moderate':
                hint['message'] = "「申し訳ございません」より「ありがとうございます」に言い換えてみましょう。"
                hint['example'] = "ご指摘ありがとうございます。今後は〇〇するようにします。"
            else:
                hint['message'] = "謝罪の代わりに、具体的な改善策や次のアクションを提案してみましょう。"
                hint['considerationPoints'] = ["建設的な提案をする", "自信を持って話す"]
        
        elif difficulty == 'questioning_back':
            if hint_level == 'gentle':
                hint['message'] = "質問で返すのも良いですが、まずはあなたの考えも少し伝えてみましょう。"
            elif hint_level == 'moderate':
                hint['message'] = "「私はこう思うのですが、〇〇についてはどうお考えですか？」という形で、意見と質問を組み合わせてみましょう。"
            else:
                hint['message'] = "自分の意見を述べてから、相手の意見を求める形にしてみましょう。"
                hint['example'] = "私の理解では〇〇だと思います。△△さんのご意見もお聞かせください。"
        
        else:  # general
            if hint_level == 'gentle':
                hint['message'] = "このシナリオのポイントを思い出してみましょう。"
                hint['considerationPoints'] = learning_points[:2]
            elif hint_level == 'moderate':
                hint['message'] = "相手の立場に立って、何を求めているか考えてみましょう。"
                hint['considerationPoints'] = learning_points
            else:
                hint['message'] = "シナリオの目的に沿った対応を心がけましょう。"
                hint['type'] = 'approach'
                points = self._get_scenario_specific_points(scenario_data)
                hint['considerationPoints'] = points if points else ["相手の立場を考える", "建設的な対話を心がける", "具体的に伝える"]
        
        return hint
    
    def _get_scenario_specific_points(self, scenario_data: Dict[str, Any]) -> List[str]:
        """シナリオ固有のポイントを取得"""
        points = []
        
        # シナリオの代替アプローチから抽出
        alternative_approaches = scenario_data.get('alternative_approaches', [])
        for approach in alternative_approaches[:2]:
            if 'practice_point' in approach:
                points.append(approach['practice_point'])
        
        # フィードバックポイントから抽出
        feedback_points = scenario_data.get('feedback_points', {})
        if 'good_points' in feedback_points:
            points.extend(feedback_points['good_points'][:2])
        
        return points[:3]  # 最大3つまで
    
    def _create_fallback_hint(self) -> Dict[str, Any]:
        """フォールバック用の汎用ヒント"""
        return {
            'type': 'general',
            'message': "落ち着いて、相手の話をよく聞いてから返答しましょう。",
            'considerationPoints': [
                "相手の気持ちを考える",
                "自分の意見も伝える",
                "建設的な対話を心がける"
            ]
        }
    
    def _load_hint_templates(self) -> Dict[str, Any]:
        """ヒントテンプレートをロード"""
        return {
            'general_tips': [
                "相手の話を最後まで聞く",
                "共感を示してから意見を述べる",
                "具体的な例を挙げて説明する",
                "質問で理解を深める"
            ],
            'communication_patterns': {
                'assertive': "自分の意見をはっきりと、でも相手を尊重しながら伝える",
                'empathetic': "相手の気持ちに寄り添いながら対話する",
                'solution_focused': "問題解決に向けた建設的な提案をする"
            }
        }