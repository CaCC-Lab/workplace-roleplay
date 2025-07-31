"""フィードバックサービス - ユーザー体験向上のための強化版"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from flask import session

from ..utils.error_handler import ValidationError

logger = logging.getLogger(__name__)


class FeedbackService:
    """強化されたフィードバックサービス"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
        self.feedback_templates = self._load_feedback_templates()
    
    def _load_feedback_templates(self) -> Dict[str, str]:
        """フィードバックテンプレートを読み込み"""
        return {
            "positive": {
                "greeting": "素晴らしい挨拶でした！😊",
                "listening": "相手の話をよく聞いていますね！",
                "empathy": "共感を示す姿勢が良いです！",
                "clarity": "とても分かりやすい説明でした！",
                "professionalism": "プロフェッショナルな対応です！"
            },
            "improvement": {
                "greeting": "もう少し温かみのある挨拶を心がけましょう",
                "listening": "相手の話により注意を向けてみましょう",
                "empathy": "相手の感情により寄り添ってみましょう",
                "clarity": "もう少し具体的に説明してみましょう",
                "professionalism": "より丁寧な言葉遣いを心がけましょう"
            },
            "suggestion": {
                "greeting": "例：「おはようございます！今日もよろしくお願いします」",
                "listening": "例：「なるほど、〜ということですね」と確認してみる",
                "empathy": "例：「それは大変でしたね」と共感を示す",
                "clarity": "例：箇条書きで要点をまとめる",
                "professionalism": "例：「〜していただけますでしょうか」"
            }
        }
    
    def analyze_conversation(self, conversation_history: List[Dict[str, str]], 
                           scenario_context: Optional[Dict] = None) -> Dict[str, Any]:
        """会話を分析して詳細なフィードバックを生成"""
        if not conversation_history:
            raise ValidationError("会話履歴が空です", field="conversation_history")
        
        # 会話の特徴を抽出
        features = self._extract_conversation_features(conversation_history)
        
        # スコアリング
        scores = self._calculate_scores(features)
        
        # 強みと改善点を特定
        strengths = self._identify_strengths(scores)
        improvements = self._identify_improvements(scores)
        
        # 具体的な提案を生成
        suggestions = self._generate_suggestions(improvements, scenario_context)
        
        # 総合評価
        overall_score = sum(scores.values()) / len(scores) * 20  # 100点満点に変換
        
        return {
            "overall_score": round(overall_score, 1),
            "scores": scores,
            "strengths": strengths,
            "improvements": improvements,
            "suggestions": suggestions,
            "detailed_feedback": self._generate_detailed_feedback(scores, strengths, improvements),
            "next_steps": self._recommend_next_steps(scores, scenario_context)
        }
    
    def _extract_conversation_features(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """会話から特徴を抽出"""
        features = {
            "message_count": len([m for m in conversation_history if m["role"] == "user"]),
            "avg_message_length": 0,
            "question_count": 0,
            "empathy_expressions": 0,
            "professional_terms": 0,
            "positive_expressions": 0
        }
        
        user_messages = [m["content"] for m in conversation_history if m["role"] == "user"]
        
        if user_messages:
            # 平均メッセージ長
            features["avg_message_length"] = sum(len(m) for m in user_messages) / len(user_messages)
            
            # 特徴的な表現をカウント
            for message in user_messages:
                # 質問
                if "？" in message or "ですか" in message or "でしょうか" in message:
                    features["question_count"] += 1
                
                # 共感表現
                empathy_words = ["そうですね", "なるほど", "おっしゃる通り", "確かに", "分かります"]
                features["empathy_expressions"] += sum(1 for word in empathy_words if word in message)
                
                # 丁寧な表現
                professional_words = ["いただく", "させていただく", "申し訳", "恐れ入ります", "お願い"]
                features["professional_terms"] += sum(1 for word in professional_words if word in message)
                
                # ポジティブな表現
                positive_words = ["ありがとう", "素晴らしい", "良い", "嬉しい", "楽しい"]
                features["positive_expressions"] += sum(1 for word in positive_words if word in message)
        
        return features
    
    def _calculate_scores(self, features: Dict[str, Any]) -> Dict[str, float]:
        """特徴からスコアを計算（5点満点）"""
        scores = {}
        
        # エンゲージメント（参加度）
        message_score = min(features["message_count"] / 5, 1.0)  # 5メッセージ以上で満点
        length_score = min(features["avg_message_length"] / 50, 1.0)  # 50文字以上で満点
        scores["engagement"] = (message_score + length_score) * 2.5
        
        # 傾聴力
        question_score = min(features["question_count"] / 3, 1.0)  # 3つ以上の質問で満点
        scores["listening"] = question_score * 5.0
        
        # 共感力
        empathy_score = min(features["empathy_expressions"] / 3, 1.0)  # 3つ以上で満点
        scores["empathy"] = empathy_score * 5.0
        
        # プロフェッショナリズム
        professional_score = min(features["professional_terms"] / 4, 1.0)  # 4つ以上で満点
        scores["professionalism"] = professional_score * 5.0
        
        # ポジティブさ
        positive_score = min(features["positive_expressions"] / 2, 1.0)  # 2つ以上で満点
        scores["positivity"] = positive_score * 5.0
        
        return {k: round(v, 1) for k, v in scores.items()}
    
    def _identify_strengths(self, scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """強みを特定"""
        strengths = []
        skill_names = {
            "engagement": "積極的な参加",
            "listening": "傾聴力",
            "empathy": "共感力",
            "professionalism": "プロフェッショナリズム",
            "positivity": "前向きな姿勢"
        }
        
        for skill, score in scores.items():
            if score >= 3.5:  # 3.5以上を強みとする
                strengths.append({
                    "skill": skill_names.get(skill, skill),
                    "score": score,
                    "message": self.feedback_templates["positive"].get(skill, "素晴らしいです！")
                })
        
        return sorted(strengths, key=lambda x: x["score"], reverse=True)
    
    def _identify_improvements(self, scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """改善点を特定"""
        improvements = []
        skill_names = {
            "engagement": "積極的な参加",
            "listening": "傾聴力",
            "empathy": "共感力",
            "professionalism": "プロフェッショナリズム",
            "positivity": "前向きな姿勢"
        }
        
        for skill, score in scores.items():
            if score < 3.0:  # 3.0未満を改善点とする
                improvements.append({
                    "skill": skill_names.get(skill, skill),
                    "score": score,
                    "message": self.feedback_templates["improvement"].get(skill, "改善の余地があります")
                })
        
        return sorted(improvements, key=lambda x: x["score"])
    
    def _generate_suggestions(self, improvements: List[Dict[str, Any]], 
                            scenario_context: Optional[Dict] = None) -> List[str]:
        """具体的な提案を生成"""
        suggestions = []
        
        for improvement in improvements[:3]:  # 上位3つの改善点に焦点を当てる
            skill = improvement["skill"]
            if skill in self.feedback_templates["suggestion"]:
                suggestions.append(self.feedback_templates["suggestion"][skill])
        
        # シナリオ固有の提案を追加
        if scenario_context:
            scenario_type = scenario_context.get("type", "general")
            if scenario_type == "negotiation":
                suggestions.append("相手の立場を理解した上で、Win-Winの解決策を提案してみましょう")
            elif scenario_type == "conflict":
                suggestions.append("感情的にならず、事実に基づいて話し合いましょう")
        
        return suggestions
    
    def _generate_detailed_feedback(self, scores: Dict[str, float], 
                                  strengths: List[Dict[str, Any]], 
                                  improvements: List[Dict[str, Any]]) -> str:
        """詳細なフィードバックメッセージを生成"""
        overall_avg = sum(scores.values()) / len(scores)
        
        feedback_parts = []
        
        # 総合評価
        if overall_avg >= 4.0:
            feedback_parts.append("素晴らしいコミュニケーションスキルを発揮されています！")
        elif overall_avg >= 3.0:
            feedback_parts.append("良いコミュニケーションができています。")
        else:
            feedback_parts.append("コミュニケーションスキルを向上させる余地があります。")
        
        # 強みについて
        if strengths:
            strength_names = [s["skill"] for s in strengths[:2]]
            feedback_parts.append(f"特に{', '.join(strength_names)}が優れています。")
        
        # 改善点について
        if improvements:
            improvement_names = [i["skill"] for i in improvements[:2]]
            feedback_parts.append(f"{', '.join(improvement_names)}をさらに意識すると、より良いコミュニケーションになるでしょう。")
        
        return " ".join(feedback_parts)
    
    def _recommend_next_steps(self, scores: Dict[str, float], 
                            scenario_context: Optional[Dict] = None) -> List[str]:
        """次のステップを推奨"""
        recommendations = []
        overall_avg = sum(scores.values()) / len(scores)
        
        if overall_avg >= 4.0:
            recommendations.append("より難しいシナリオに挑戦してみましょう")
            recommendations.append("他の人にコミュニケーションのコツを教えてみましょう")
        elif overall_avg >= 3.0:
            recommendations.append("同じシナリオでもう一度練習してみましょう")
            recommendations.append("フィードバックを意識して実践してみましょう")
        else:
            recommendations.append("基礎的なシナリオから始めてみましょう")
            recommendations.append("一つずつスキルを改善していきましょう")
        
        return recommendations
    
    def save_feedback(self, feedback_data: Dict[str, Any], user_id: Optional[str] = None) -> None:
        """フィードバックをセッションに保存"""
        if "feedback_history" not in session:
            session["feedback_history"] = []
        
        feedback_record = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "feedback": feedback_data
        }
        
        session["feedback_history"].append(feedback_record)
        
        # 最新の10件のみ保持
        session["feedback_history"] = session["feedback_history"][-10:]
        
        logger.info(f"Feedback saved for user: {user_id}")
    
    def get_feedback_history(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """フィードバック履歴を取得"""
        history = session.get("feedback_history", [])
        
        if user_id:
            history = [h for h in history if h.get("user_id") == user_id]
        
        return history