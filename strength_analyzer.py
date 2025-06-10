"""
ユーザーの強み分析機能
コミュニケーションスキルの強みを分析し、成長を可視化する
"""

import json
import random
from datetime import datetime
from typing import Dict, List, Any, Tuple


# コミュニケーションスキルの強み項目定義
STRENGTH_CATEGORIES = {
    "empathy": {
        "name": "共感力",
        "description": "相手の気持ちを理解し、適切に反応する力",
        "indicators": [
            "相手の感情に配慮した返答",
            "相手の立場を理解する発言",
            "励ましや慰めの言葉"
        ]
    },
    "clarity": {
        "name": "明確な伝達力",
        "description": "分かりやすく論理的に説明する力",
        "indicators": [
            "構造化された説明",
            "具体例の使用",
            "要点の明確化"
        ]
    },
    "active_listening": {
        "name": "傾聴力",
        "description": "相手の話を真摯に聞き、理解を示す力",
        "indicators": [
            "相手の発言への適切な反応",
            "質問による理解の深化",
            "話の要約や確認"
        ]
    },
    "adaptability": {
        "name": "適応力",
        "description": "相手や状況に応じて対応を調整する力",
        "indicators": [
            "相手に合わせた言葉遣い",
            "状況に応じた話題選択",
            "柔軟な対応"
        ]
    },
    "positivity": {
        "name": "前向きさ",
        "description": "建設的で前向きな雰囲気を作る力",
        "indicators": [
            "ポジティブな表現",
            "解決志向の発言",
            "励ましや感謝の言葉"
        ]
    },
    "professionalism": {
        "name": "プロフェッショナリズム",
        "description": "職場での適切な振る舞いと判断力",
        "indicators": [
            "適切な敬語使用",
            "ビジネスマナーの実践",
            "責任感のある対応"
        ]
    }
}


# 励ましメッセージパターンの定義
ENCOURAGEMENT_PATTERNS = {
    "significant_growth": {
        "condition": "score_improvement",
        "threshold": 10,
        "messages": [
            "素晴らしい成長です！{skill}が{diff}ポイントも向上しました！",
            "{skill}の向上が目覚ましいですね！この調子で続けましょう！",
            "わずかな期間で{skill}がこんなに上達するなんて、素晴らしい努力です！"
        ]
    },
    "consistent_practice": {
        "condition": "practice_count",
        "threshold": 5,
        "messages": [
            "{count}回の練習を達成！継続は力なりです！",
            "コンスタントな練習が実を結んでいます。{top_skill}が特に光っています！",
            "毎日の積み重ねが確実な成長につながっています！"
        ]
    },
    "strength_discovery": {
        "condition": "high_score",
        "threshold": 80,
        "messages": [
            "{skill}はあなたの強みです！自信を持って活用しましょう！",
            "{skill}で高得点！この才能を職場でも発揮してください！",
            "素晴らしい{skill}をお持ちです。さらに磨きをかけていきましょう！"
        ]
    },
    "balanced_growth": {
        "condition": "balanced_scores",
        "threshold": 60,
        "messages": [
            "バランスの取れた成長です！全体的なスキルアップが見られます！",
            "すべてのスキルが着実に向上しています。理想的な成長パターンです！",
            "総合力が高まっています！どんな場面でも対応できる力がついてきました！"
        ]
    }
}


def create_strength_analysis_prompt(conversation_history: List[Dict[str, str]]) -> str:
    """
    会話履歴から強み分析用のプロンプトを作成
    """
    # 強み項目の説明を整形
    categories_description = []
    for key, category in STRENGTH_CATEGORIES.items():
        indicators = "\n    - ".join(category["indicators"])
        categories_description.append(
            f'{key}: {category["name"]} - {category["description"]}\n    - {indicators}'
        )
    
    prompt = f"""以下の会話履歴から、ユーザーのコミュニケーションスキルの強みを分析してください。

会話履歴:
{conversation_history}

評価項目:
{chr(10).join(categories_description)}

以下のJSON形式で、各項目を0-100点で評価し、具体的な根拠を示してください：
{{
    "scores": {{
        "empathy": {{"score": 0-100の数値, "evidence": "具体的な発言例"}},
        "clarity": {{"score": 0-100の数値, "evidence": "具体的な発言例"}},
        "active_listening": {{"score": 0-100の数値, "evidence": "具体的な発言例"}},
        "adaptability": {{"score": 0-100の数値, "evidence": "具体的な発言例"}},
        "positivity": {{"score": 0-100の数値, "evidence": "具体的な発言例"}},
        "professionalism": {{"score": 0-100の数値, "evidence": "具体的な発言例"}}
    }},
    "overall_impression": "全体的な印象と特筆すべき強み",
    "growth_areas": "さらに伸ばせる可能性のある分野"
}}

注意：
- ユーザーの発言のみを評価対象とする
- 具体的な発言を根拠として示す
- ポジティブな面に焦点を当てる
- 成長の可能性を前向きに示す"""
    
    return prompt


def parse_strength_analysis(analysis_response: str) -> Dict[str, Any]:
    """
    AI分析結果をパースして構造化データに変換
    """
    try:
        # JSONとして解析を試みる
        result = json.loads(analysis_response)
        
        # スコアのみ抽出（シンプルな形式に変換）
        scores = {}
        for key, data in result.get("scores", {}).items():
            if isinstance(data, dict):
                scores[key] = data.get("score", 0)
            else:
                scores[key] = data
        
        return {
            "scores": scores,
            "overall_impression": result.get("overall_impression", ""),
            "growth_areas": result.get("growth_areas", "")
        }
    except json.JSONDecodeError:
        # JSON解析に失敗した場合、デフォルト値を返す
        return {
            "scores": {key: 50 for key in STRENGTH_CATEGORIES.keys()},
            "overall_impression": "分析中にエラーが発生しました",
            "growth_areas": ""
        }


def get_top_strengths(scores: Dict[str, float], top_n: int = 3) -> List[Dict[str, Any]]:
    """
    トップNの強みを取得
    """
    sorted_strengths = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_strengths = []
    
    for key, score in sorted_strengths[:top_n]:
        if key in STRENGTH_CATEGORIES:
            top_strengths.append({
                "key": key,
                "name": STRENGTH_CATEGORIES[key]["name"],
                "description": STRENGTH_CATEGORIES[key]["description"],
                "score": score
            })
    
    return top_strengths


def calculate_score_improvement(current_scores: Dict[str, float], 
                               history: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    前回からのスコアの改善を計算
    """
    if not history:
        return {}
    
    previous_scores = history[-1].get("scores", {})
    improvements = {}
    
    for key in current_scores:
        if key in previous_scores:
            improvements[key] = current_scores[key] - previous_scores[key]
    
    return improvements


def generate_encouragement_messages(scores: Dict[str, float], 
                                  history: List[Dict[str, Any]]) -> List[str]:
    """
    成長データに基づいて励ましメッセージを生成
    """
    messages = []
    
    # 練習回数のチェック
    practice_count = len(history) + 1
    if practice_count >= ENCOURAGEMENT_PATTERNS["consistent_practice"]["threshold"]:
        top_skill = get_top_strengths(scores, 1)[0] if scores else None
        if top_skill:
            message = random.choice(ENCOURAGEMENT_PATTERNS["consistent_practice"]["messages"])
            messages.append(message.format(
                count=practice_count, 
                top_skill=top_skill["name"]
            ))
    
    # 高得点スキルのチェック
    for key, score in scores.items():
        if score >= ENCOURAGEMENT_PATTERNS["strength_discovery"]["threshold"]:
            if key in STRENGTH_CATEGORIES:
                message = random.choice(ENCOURAGEMENT_PATTERNS["strength_discovery"]["messages"])
                messages.append(message.format(skill=STRENGTH_CATEGORIES[key]["name"]))
                break  # 1つのメッセージに留める
    
    # バランスの取れた成長のチェック
    if scores and min(scores.values()) >= ENCOURAGEMENT_PATTERNS["balanced_growth"]["threshold"]:
        message = random.choice(ENCOURAGEMENT_PATTERNS["balanced_growth"]["messages"])
        messages.append(message)
    
    # スコアの改善をチェック
    if history:
        improvements = calculate_score_improvement(scores, history)
        for key, diff in improvements.items():
            if diff >= ENCOURAGEMENT_PATTERNS["significant_growth"]["threshold"]:
                if key in STRENGTH_CATEGORIES:
                    message = random.choice(ENCOURAGEMENT_PATTERNS["significant_growth"]["messages"])
                    messages.append(message.format(
                        skill=STRENGTH_CATEGORIES[key]["name"],
                        diff=int(diff)
                    ))
                    break  # 1つのメッセージに留める
    
    # メッセージがない場合は汎用的な励ましを追加
    if not messages:
        messages.append("着実に成長しています！この調子で練習を続けましょう！")
    
    return messages


def analyze_user_strengths(conversation_history: str) -> Dict[str, float]:
    """
    会話履歴からユーザーの強みを分析（シンプルバージョン）
    会話履歴が空の場合はデフォルト値を返す
    
    Returns:
        スコア辞書
    """
    # 会話履歴が空の場合はデフォルト値を返す
    if not conversation_history or conversation_history.strip() == "":
        return {
            "empathy": 50,
            "clarity": 50,
            "active_listening": 50,
            "adaptability": 50,
            "positivity": 50,
            "professionalism": 50
        }
    
    # 会話履歴の長さに基づいて基本スコアを設定
    base_score = min(60 + len(conversation_history.split('\n')) * 2, 85)
    
    # 各カテゴリにランダムな変動を加える（実際のAI分析の代わり）
    import random
    scores = {}
    for category in STRENGTH_CATEGORIES.keys():
        variation = random.randint(-10, 10)
        scores[category] = max(40, min(95, base_score + variation))
    
    return scores


def create_personalized_message_prompt(scores: Dict[str, float], 
                                     base_message: str) -> str:
    """
    AIによるパーソナライズされたメッセージ生成用プロンプト
    """
    top_strengths = get_top_strengths(scores, 3)
    strengths_text = "、".join([s["name"] for s in top_strengths])
    
    prompt = f"""ユーザーのコミュニケーションスキル分析結果：
- 特に優れている点: {strengths_text}
- 最高得点: {top_strengths[0]["name"]} ({top_strengths[0]["score"]}点)

基本メッセージ: {base_message}

このメッセージに続けて、ユーザーを励まし、次の練習への意欲を高める一言を追加してください。
具体的で前向きな内容にしてください。50文字以内で。"""
    
    return prompt