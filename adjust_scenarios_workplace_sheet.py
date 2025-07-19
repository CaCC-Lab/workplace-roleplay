#!/usr/bin/env python3
"""
「職場のあなた再現シート」の考え方に基づいてシナリオを調整するスクリプト
"""

import yaml
import os
from pathlib import Path

def add_workplace_sheet_elements(scenario_data, scenario_id):
    """既存のシナリオに職場のあなた再現シートの要素を追加"""
    
    # 基本構造は保持
    adjusted_scenario = scenario_data.copy()
    
    # シナリオ分析セクションを追加
    adjusted_scenario["scenario_analysis"] = create_scenario_analysis(scenario_id)
    
    # 自己振り返りプロンプトを追加
    adjusted_scenario["self_reflection_prompts"] = [
        "この場面で、あなたはどう感じましたか？",
        "なぜそのような対応を選びましたか？",
        "相手はどう感じたと思いますか？",
        "もし同じ場面に遭遇したら、どう対応したいですか？"
    ]
    
    # 代替アプローチを追加
    adjusted_scenario["alternative_approaches"] = create_alternative_approaches(scenario_id)
    
    # スキルトラッキング要素を追加
    adjusted_scenario["skill_focus"] = identify_skill_focus(scenario_id)
    
    return adjusted_scenario

def create_scenario_analysis(scenario_id):
    """シナリオIDに基づいて典型的な反応パターンを作成"""
    
    # シナリオ1: 朝の挨拶
    if scenario_id == 1:
        return {
            "typical_responses": [
                {
                    "pattern": "回避型",
                    "description": "視線を合わせず、小さな声で返事",
                    "example": "（下を向いて）...はい...",
                    "underlying_feeling": "緊張、自信のなさ"
                },
                {
                    "pattern": "形式的型",
                    "description": "決まった言葉だけで対応",
                    "example": "おはようございます（それ以上話さない）",
                    "underlying_feeling": "これ以上の会話への不安"
                },
                {
                    "pattern": "過剰適応型",
                    "description": "相手に合わせようと頑張りすぎる",
                    "example": "お、おはようございます！はい、暖かいですね！そうですね！",
                    "underlying_feeling": "相手に嫌われたくない気持ち"
                }
            ]
        }
    
    # シナリオ2: 感謝を伝える
    elif scenario_id == 2:
        return {
            "typical_responses": [
                {
                    "pattern": "遠慮型",
                    "description": "申し訳なさを前面に出す",
                    "example": "すみません、すみません、申し訳ないです",
                    "underlying_feeling": "助けてもらうことへの罪悪感"
                },
                {
                    "pattern": "最小限型",
                    "description": "最低限の言葉で済ませる",
                    "example": "...ども...",
                    "underlying_feeling": "感謝の表現への照れ、不慣れ"
                },
                {
                    "pattern": "説明過多型",
                    "description": "状況を詳しく説明しすぎる",
                    "example": "本当にすみません、私がドジで、いつもこうで...",
                    "underlying_feeling": "自己否定、過度な責任感"
                }
            ]
        }
    
    # デフォルト
    else:
        return {
            "typical_responses": [
                {
                    "pattern": "一般的な反応",
                    "description": "このシナリオでよく見られる反応",
                    "example": "具体的な例",
                    "underlying_feeling": "背景にある感情"
                }
            ]
        }

def create_alternative_approaches(scenario_id):
    """より適切な対応方法を提示"""
    
    if scenario_id == 1:  # 朝の挨拶
        return [
            {
                "approach": "自然な挨拶",
                "example": "おはようございます。（一呼吸おいて）暖かいですね",
                "benefit": "無理のない範囲で会話を続けられる",
                "practice_point": "相手と同じトーンで返すことから始める"
            },
            {
                "approach": "素直な反応",
                "example": "おはようございます。月曜日はちょっと眠いです",
                "benefit": "自分の状態を正直に伝えることで親近感が生まれる",
                "practice_point": "完璧でない自分を見せても大丈夫"
            },
            {
                "approach": "共感的な返答",
                "example": "おはようございます。本当に、今日は過ごしやすそうですね",
                "benefit": "相手の話題に乗ることで自然な会話になる",
                "practice_point": "相手の言葉を少し言い換えて返す"
            }
        ]
    
    elif scenario_id == 2:  # 感謝を伝える
        return [
            {
                "approach": "シンプルな感謝",
                "example": "ありがとうございます。助かりました",
                "benefit": "素直な感謝は相手も受け取りやすい",
                "practice_point": "「すみません」より「ありがとう」を使う"
            },
            {
                "approach": "具体的な感謝",
                "example": "手伝ってくれてありがとうございます。一人だと大変でした",
                "benefit": "何に感謝しているか伝わりやすい",
                "practice_point": "助かった具体的な点を一つ伝える"
            },
            {
                "approach": "前向きな感謝",
                "example": "ありがとうございます！おかげで早く片付きそうです",
                "benefit": "ポジティブな雰囲気を作れる",
                "practice_point": "感謝と一緒に良い結果を伝える"
            }
        ]
    
    # デフォルト
    else:
        return [
            {
                "approach": "基本的なアプローチ",
                "example": "状況に応じた対応例",
                "benefit": "期待される効果",
                "practice_point": "練習のポイント"
            }
        ]

def identify_skill_focus(scenario_id):
    """各シナリオで焦点を当てるスキル"""
    
    skill_map = {
        1: {
            "primary": "基本的な挨拶",
            "secondary": ["アイコンタクト", "声の大きさ", "自然な会話の始め方"],
            "workplace_relevance": "職場での第一印象と人間関係の基礎"
        },
        2: {
            "primary": "感謝の表現",
            "secondary": ["適切な言葉選び", "感情の表現", "相互援助の意識"],
            "workplace_relevance": "チームワークと信頼関係の構築"
        },
        3: {
            "primary": "自己開示",
            "secondary": ["適度な情報共有", "境界線の設定", "共感の獲得"],
            "workplace_relevance": "上司との適切な関係構築"
        },
        4: {
            "primary": "質問力",
            "secondary": ["タイミング", "明確な表現", "学習意欲の表明"],
            "workplace_relevance": "成長意欲と問題解決能力"
        },
        5: {
            "primary": "雑談力",
            "secondary": ["話題選び", "相槌", "会話の終わらせ方"],
            "workplace_relevance": "職場の雰囲気作りと人間関係"
        }
    }
    
    return skill_map.get(scenario_id, {
        "primary": "コミュニケーション全般",
        "secondary": ["状況判断", "適切な対応"],
        "workplace_relevance": "職場での円滑なコミュニケーション"
    })

def process_scenario_file(file_path, scenario_id):
    """シナリオファイルを読み込み、調整して保存"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            scenario_data = yaml.safe_load(f)
        
        # 職場のあなた再現シートの要素を追加
        adjusted_scenario = add_workplace_sheet_elements(scenario_data, scenario_id)
        
        # ファイルを上書き保存
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(adjusted_scenario, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        print(f"✅ シナリオ{scenario_id}を調整しました: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ シナリオ{scenario_id}の処理中にエラー: {e}")
        return False

def main():
    """メイン処理"""
    print("「職場のあなた再現シート」の考え方に基づいてシナリオを調整します...")
    print("=" * 60)
    
    scenarios_dir = Path("scenarios/data")
    
    # まずはシナリオ1-5（pre-beginner/beginner）を調整
    for scenario_id in range(1, 6):
        file_path = scenarios_dir / f"scenario{scenario_id}.yaml"
        process_scenario_file(file_path, scenario_id)
    
    print("=" * 60)
    print("✅ シナリオ1-5の調整が完了しました")
    print("次のステップ: 調整したシナリオをテストし、残りのシナリオも同様に調整")

if __name__ == "__main__":
    main()