"""
パワーハラスメント検出とセーフガード機能
Codexによる設計: エッジケース対応と適切な境界設定
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class HarassmentSeverity(Enum):
    """ハラスメントの重要度レベル"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class HarassmentAlert:
    """ハラスメント検出結果"""
    severity: HarassmentSeverity
    category: str
    detected_text: str
    explanation: str
    suggested_alternative: str
    legal_note: Optional[str] = None

class HarassmentDetector:
    """
    パワーハラスメント検出エンジン
    日本の労働施策総合推進法に基づく検出ルール実装
    """
    
    def __init__(self):
        self.patterns = self._load_detection_patterns()
        self.context_memory = []  # 文脈記憶（エスカレーション検出用）
        
    def _load_detection_patterns(self) -> Dict:
        """検出パターンの定義"""
        return {
            # 1. 身体的攻撃（暴力・威嚇）
            "physical_threat": {
                "patterns": [
                    r"殴る|叩く|蹴る",
                    r"投げつけ|ぶん投げ", 
                    r"暴力|暴行",
                    r"物理的|身体的.*攻撃"
                ],
                "severity": HarassmentSeverity.CRITICAL,
                "legal_note": "身体的攻撃は刑事事件に発展する可能性があります"
            },
            
            # 2. 精神的攻撃（人格否定・侮辱）
            "personal_attack": {
                "patterns": [
                    r"馬鹿|バカ|阿呆|あほ",
                    r"無能|役立たず|使えない",
                    r"死ね|消え|いらない",
                    r"クズ|ゴミ|カス",
                    r"頭.*悪い|頭.*おかしい",
                    r"人間.*失格|社会人.*失格"
                ],
                "severity": HarassmentSeverity.HIGH,
                "legal_note": "人格を否定する発言は精神的な損害を与える可能性があります"
            },
            
            # 3. 威圧・脅迫
            "intimidation": {
                "patterns": [
                    r"クビ|首|解雇|やめろ|辞め",
                    r"評価.*下げ|給料.*下げ|降格",
                    r"覚えて.*お|後で.*覚悟",
                    r"わかってる.*な|わかってる.*だろ",
                    r"今度.*許さ|次.*ない"
                ],
                "severity": HarassmentSeverity.HIGH,
                "legal_note": "脅迫的な発言は労働環境を悪化させます"
            },
            
            # 4. 過大要求
            "excessive_demands": {
                "patterns": [
                    r"今日.*中|今すぐ.*やれ|すぐ.*やれ",
                    r"休み.*なし|休憩.*なし|徹夜",
                    r"不可能.*でも|無理.*でも.*やれ",
                    r"何.*が.*でも|どんな.*でも.*やれ"
                ],
                "severity": HarassmentSeverity.MEDIUM,
                "legal_note": "過度な業務要求は労働基準法違反の可能性があります"
            },
            
            # 5. プライバシー侵害
            "privacy_invasion": {
                "patterns": [
                    r"彼女|彼氏|恋人|結婚|離婚",
                    r"家族.*こと|実家.*こと|親.*こと",
                    r"お金.*こと|借金|ローン",
                    r"病気.*こと|薬.*こと|通院",
                    r"宗教|政治.*考え|支持.*政党"
                ],
                "severity": HarassmentSeverity.MEDIUM,
                "legal_note": "個人のプライバシーに関する質問は控えるべきです"
            }
        }
    
    def detect_harassment(self, user_message: str) -> List[HarassmentAlert]:
        """
        ユーザーメッセージからハラスメント要素を検出
        
        Args:
            user_message: ユーザー（上司役）の発言
            
        Returns:
            検出されたハラスメント要素のリスト
        """
        alerts = []
        
        # 文脈記憶に追加（エスカレーション検出用）
        self.context_memory.append(user_message)
        if len(self.context_memory) > 10:  # 最新10発言のみ保持
            self.context_memory.pop(0)
        
        # パターンマッチング検出
        for category, config in self.patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, user_message, re.IGNORECASE):
                    alert = HarassmentAlert(
                        severity=config["severity"],
                        category=category,
                        detected_text=user_message,
                        explanation=self._get_explanation(category),
                        suggested_alternative=self._get_alternative(category, user_message),
                        legal_note=config.get("legal_note")
                    )
                    alerts.append(alert)
        
        # エスカレーション検出
        escalation_alert = self._detect_escalation()
        if escalation_alert:
            alerts.append(escalation_alert)
            
        return alerts
    
    def _detect_escalation(self) -> Optional[HarassmentAlert]:
        """
        会話のエスカレーション（段階的悪化）を検出
        """
        if len(self.context_memory) < 3:
            return None
            
        # 最近の発言で威圧的な語調が増加しているかチェック
        aggressive_patterns = [r"！+", r"[？?]+", r"[。.]{2,}", r"[ー〜～]{2,}"]
        recent_aggression = 0
        
        for message in self.context_memory[-3:]:
            for pattern in aggressive_patterns:
                if re.search(pattern, message):
                    recent_aggression += 1
        
        if recent_aggression >= 2:
            return HarassmentAlert(
                severity=HarassmentSeverity.MEDIUM,
                category="escalation",
                detected_text="最近の発言パターン",
                explanation="会話が感情的になっています",
                suggested_alternative="一度冷静になって、建設的な表現を心がけましょう",
                legal_note="継続的な威圧的態度はパワハラに該当する場合があります"
            )
        
        return None
    
    def _get_explanation(self, category: str) -> str:
        """カテゴリ別の説明文生成"""
        explanations = {
            "physical_threat": "身体的な暴力や威嚇は深刻なパワーハラスメントです",
            "personal_attack": "人格を否定する発言は相手の尊厳を傷つけます",
            "intimidation": "威圧的・脅迫的な発言は職場環境を悪化させます",
            "excessive_demands": "現実的でない過度な要求は部下を追い詰めます",
            "privacy_invasion": "業務に関係のない個人的な事柄への言及は不適切です"
        }
        return explanations.get(category, "不適切な表現が検出されました")
    
    def _get_alternative(self, category: str, original: str) -> str:
        """改善案の生成"""
        alternatives = {
            "physical_threat": "怒りを感じても、冷静に言葉で伝えましょう",
            "personal_attack": "行動や成果について具体的にフィードバックしましょう",
            "intimidation": "相手の立場に配慮した建設的な表現を使いましょう",
            "excessive_demands": "現実的な期限と方法を一緒に検討しましょう",
            "privacy_invasion": "業務に関連する内容に焦点を絞りましょう"
        }
        return alternatives.get(category, "より建設的で適切な表現を心がけましょう")

class ConversationSafeguard:
    """会話の安全性を保つためのセーフガード機能"""
    
    def __init__(self):
        self.detector = HarassmentDetector()
        self.warning_count = 0
        self.max_warnings = 3
        
    def evaluate_user_message(self, message: str) -> Dict:
        """
        ユーザーメッセージを評価し、必要に応じて介入
        
        Returns:
            評価結果と対応アクション
        """
        alerts = self.detector.detect_harassment(message)
        
        if not alerts:
            return {"status": "ok", "alerts": []}
        
        # 重要度別の対応
        critical_alerts = [a for a in alerts if a.severity == HarassmentSeverity.CRITICAL]
        high_alerts = [a for a in alerts if a.severity == HarassmentSeverity.HIGH]
        
        if critical_alerts:
            return {
                "status": "terminate",
                "reason": "重大なハラスメント行為が検出されました",
                "alerts": alerts,
                "action": "immediate_termination"
            }
        
        if high_alerts:
            self.warning_count += 1
            if self.warning_count >= self.max_warnings:
                return {
                    "status": "terminate",
                    "reason": f"ハラスメント警告が{self.max_warnings}回に達しました",
                    "alerts": alerts,
                    "action": "warning_limit_exceeded"
                }
        
        return {
            "status": "warning", 
            "alerts": alerts,
            "warning_count": self.warning_count,
            "action": "continue_with_feedback"
        }

# 使用例とテストケース
def test_harassment_detection():
    """テストケース"""
    detector = HarassmentDetector()
    
    test_cases = [
        "馬鹿なのか？そんなこともできないなんて",  # 人格攻撃
        "今日中に絶対やれ、休憩なしでも構わない",   # 過大要求  
        "クビにするぞ、覚えておけよ",               # 威圧
        "君の恋人のことだけど...",                  # プライバシー侵害
        "お疲れ様です。この資料の件で相談があります", # 正常
    ]
    
    for case in test_cases:
        alerts = detector.detect_harassment(case)
        print(f"入力: {case}")
        print(f"検出: {len(alerts)}件のアラート")
        for alert in alerts:
            print(f"  - {alert.category}: {alert.explanation}")
        print()

if __name__ == "__main__":
    test_harassment_detection()