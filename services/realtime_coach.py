"""
リアルタイムコーチングシステム

会話中にリアルタイムでヒントと改善提案を提供
"""
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio
from collections import defaultdict

from models import db, StrengthAnalysisResult
from scenarios import load_scenarios


class RealTimeCoach:
    """リアルタイムコーチングエンジン"""
    
    def __init__(self):
        self.coaching_rules = {
            'empathy': {
                'weak_patterns': [
                    r'わかりました[。、]?$',
                    r'理解しました[。、]?$',
                    r'そうですね[。、]?$',
                    r'はい[。、]?$'
                ],
                'good_patterns': [
                    r'.*と感じていらっしゃる',
                    r'.*お気持ち.*',
                    r'.*大変.*思います',
                    r'.*辛い.*でしょう'
                ],
                'improvement_hints': [
                    '相手の気持ちを言葉にして返してみましょう',
                    '「〜と感じていらっしゃるんですね」と共感を示しましょう',
                    '相手の立場に立った表現を加えてみましょう'
                ],
                'examples': [
                    '「大変お疲れさまでした。プレッシャーを感じていらっしゃるんですね」',
                    '「お忙しい中、不安に思われているのではないでしょうか」'
                ]
            },
            'clarity': {
                'weak_patterns': [
                    r'えーと',
                    r'あのー?',
                    r'なんか',
                    r'〜的な',
                    r'みたいな',
                    r'という感じ'
                ],
                'good_patterns': [
                    r'^(まず|次に|最後に)',
                    r'具体的には',
                    r'つまり',
                    r'要するに'
                ],
                'improvement_hints': [
                    '結論から話すようにしましょう',
                    '具体例を1つ加えると分かりやすくなります',
                    '「まず」「次に」「最後に」で構造化しましょう'
                ],
                'examples': [
                    '「まず現状を整理すると、〜です。次に解決策として〜を提案します」',
                    '「具体的には、〜という方法があります」'
                ]
            },
            'active_listening': {
                'weak_patterns': [
                    r'^はい[。、]?$',
                    r'^そうですね[。、]?$'
                ],
                'good_patterns': [
                    r'.*ということは',
                    r'.*つまり.*ということですね',
                    r'.*について.*詳しく',
                    r'どのような.*でしょうか'
                ],
                'improvement_hints': [
                    '相手の話を要約して確認してみましょう',
                    '「つまり〜ということですね？」と理解を確認しましょう',
                    '詳細を聞く質問を加えてみましょう'
                ],
                'examples': [
                    '「つまり、締切に間に合わないかもしれないということですね？」',
                    '「どのような点で困難を感じていらっしゃいますか？」'
                ]
            },
            'adaptability': {
                'weak_patterns': [
                    r'いつも通り',
                    r'通常通り',
                    r'普段と同じ'
                ],
                'good_patterns': [
                    r'状況に応じて',
                    r'この場合は',
                    r'柔軟に',
                    r'代替案として'
                ],
                'improvement_hints': [
                    '状況に応じた対応を提案してみましょう',
                    '相手の立場を考慮した表現を使いましょう',
                    '複数の選択肢を提示してみましょう'
                ],
                'examples': [
                    '「状況に応じて、AプランとBプランをご用意しました」',
                    '「この場合は、いつもとは異なるアプローチが必要かもしれません」'
                ]
            },
            'positivity': {
                'weak_patterns': [
                    r'難しい',
                    r'無理',
                    r'できません',
                    r'問題',
                    r'困った'
                ],
                'good_patterns': [
                    r'頑張って',
                    r'できる',
                    r'解決',
                    r'改善',
                    r'前向きに',
                    r'チャンス'
                ],
                'improvement_hints': [
                    '前向きな表現に言い換えてみましょう',
                    '解決策や改善案を提示してみましょう',
                    '励ましの言葉を加えてみましょう'
                ],
                'examples': [
                    '「チャレンジングですが、きっと解決できると思います」',
                    '「この経験が今後の成長につながりますね」'
                ]
            },
            'professionalism': {
                'weak_patterns': [
                    r'やばい',
                    r'マジで',
                    r'超',
                    r'めっちゃ'
                ],
                'good_patterns': [
                    r'申し上げます',
                    r'いたします',
                    r'させていただ',
                    r'恐れ入りますが'
                ],
                'improvement_hints': [
                    'より丁寧な敬語を使いましょう',
                    'ビジネスにふさわしい表現に変えましょう',
                    '相手への敬意を示す言葉を加えましょう'
                ],
                'examples': [
                    '「恐れ入りますが、確認させていただけますでしょうか」',
                    '「申し上げにくいのですが、〜という状況でございます」'
                ]
            }
        }
        
        self.scenarios = load_scenarios()
    
    async def analyze_message_realtime(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        メッセージをリアルタイム分析してコーチングヒントを生成
        
        Args:
            message: ユーザーの入力メッセージ
            context: 会話のコンテキスト（シナリオ、過去の会話など）
            
        Returns:
            コーチングヒント
        """
        analysis = {
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'suggestions': [],
            'scores': {},
            'overall_rating': 'good'  # good, fair, needs_improvement
        }
        
        # 各スキルについて分析
        for skill, rules in self.coaching_rules.items():
            score, suggestions = self._analyze_skill(message, skill, rules, context)
            analysis['scores'][skill] = score
            analysis['suggestions'].extend(suggestions)
        
        # 全体評価の決定
        avg_score = sum(analysis['scores'].values()) / len(analysis['scores'])
        if avg_score >= 80:
            analysis['overall_rating'] = 'excellent'
        elif avg_score >= 65:
            analysis['overall_rating'] = 'good'
        elif avg_score >= 50:
            analysis['overall_rating'] = 'fair'
        else:
            analysis['overall_rating'] = 'needs_improvement'
        
        return analysis
    
    def _analyze_skill(self, message: str, skill: str, rules: Dict, context: Dict) -> Tuple[float, List[Dict]]:
        """
        特定スキルの分析
        
        Returns:
            (score, suggestions)
        """
        suggestions = []
        base_score = 70  # ベーススコア
        
        # 弱いパターンの検出
        weak_matches = 0
        for pattern in rules.get('weak_patterns', []):
            if re.search(pattern, message, re.IGNORECASE):
                weak_matches += 1
        
        # 良いパターンの検出
        good_matches = 0
        for pattern in rules.get('good_patterns', []):
            if re.search(pattern, message, re.IGNORECASE):
                good_matches += 1
        
        # スコア計算
        score = base_score - (weak_matches * 15) + (good_matches * 10)
        score = max(0, min(100, score))  # 0-100の範囲に制限
        
        # 改善提案の生成
        if weak_matches > 0 or score < 60:
            hint = self._select_random_hint(rules.get('improvement_hints', []))
            example = self._select_random_hint(rules.get('examples', []))
            
            suggestions.append({
                'skill': skill,
                'type': 'improvement',
                'hint': hint,
                'example': example,
                'priority': 'high' if score < 50 else 'medium',
                'confidence': 0.8
            })
        
        return score, suggestions
    
    def _select_random_hint(self, hints: List[str]) -> str:
        """ランダムにヒントを選択"""
        import random
        return random.choice(hints) if hints else ""
    
    async def get_typing_hints(self, partial_message: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        入力中のリアルタイムヒント生成
        
        Args:
            partial_message: 入力途中のメッセージ
            context: 会話コンテキスト
            
        Returns:
            入力ヒントのリスト
        """
        hints = []
        
        # 最小長度チェック
        if len(partial_message.strip()) < 10:
            return hints
        
        # 明らかな問題パターンを検出
        for skill, rules in self.coaching_rules.items():
            for pattern in rules.get('weak_patterns', []):
                if re.search(pattern, partial_message, re.IGNORECASE):
                    hints.append({
                        'type': 'warning',
                        'skill': skill,
                        'message': f'{self._get_skill_name(skill)}を向上させるヒント',
                        'suggestion': self._select_random_hint(rules.get('improvement_hints', [])),
                        'confidence': 0.7
                    })
        
        # 長さによるヒント
        if len(partial_message) > 200:
            hints.append({
                'type': 'info',
                'skill': 'clarity',
                'message': '簡潔性のヒント',
                'suggestion': 'メッセージが長くなっています。要点を絞って話すとより伝わりやすくなります',
                'confidence': 0.6
            })
        
        return hints[:2]  # 最大2つのヒントに制限
    
    def _get_skill_name(self, skill: str) -> str:
        """スキル名の日本語変換"""
        names = {
            'empathy': '共感力',
            'clarity': '明確性',
            'active_listening': '傾聴力',
            'adaptability': '適応力',
            'positivity': '前向きさ',
            'professionalism': 'プロフェッショナリズム'
        }
        return names.get(skill, skill)
    
    def get_scenario_specific_hints(self, scenario_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        シナリオ固有のヒント生成
        
        Args:
            scenario_id: シナリオID
            context: 会話コンテキスト
            
        Returns:
            シナリオ固有のヒント
        """
        scenario = self.scenarios.get(scenario_id)
        if not scenario:
            return []
        
        hints = []
        
        # シナリオの学習ポイントに基づくヒント
        learning_points = scenario.get('learning_points', [])
        for point in learning_points:
            if 'empathy' in point.lower():
                hints.append({
                    'type': 'scenario_tip',
                    'message': 'シナリオのポイント',
                    'suggestion': '相手の立場や感情を理解することが重要です',
                    'confidence': 0.9
                })
            elif 'communication' in point.lower():
                hints.append({
                    'type': 'scenario_tip',
                    'message': 'コミュニケーションのコツ',
                    'suggestion': '相手にとって分かりやすい表現を心がけましょう',
                    'confidence': 0.9
                })
        
        return hints[:1]  # シナリオヒントは1つに制限
    
    def calculate_score_impact(self, analysis: Dict[str, Any], user_history: List[StrengthAnalysisResult]) -> Dict[str, float]:
        """
        今回の分析が過去のスコアに与える影響を計算
        
        Args:
            analysis: 今回の分析結果
            user_history: ユーザーの過去の分析履歴
            
        Returns:
            スキル別の予想スコア変化
        """
        impact = {}
        
        for skill, current_score in analysis['scores'].items():
            # 過去のスコア平均を計算
            historical_scores = []
            for result in user_history[-5:]:  # 直近5回
                if result.analysis_result and 'scores' in result.analysis_result:
                    score = result.analysis_result['scores'].get(skill)
                    if score is not None:
                        historical_scores.append(score)
            
            if historical_scores:
                avg_historical = sum(historical_scores) / len(historical_scores)
                # 重み付き平均で新しいスコアを計算
                predicted_new_avg = (avg_historical * 0.8) + (current_score * 0.2)
                impact[skill] = predicted_new_avg - avg_historical
            else:
                impact[skill] = 0
        
        return impact