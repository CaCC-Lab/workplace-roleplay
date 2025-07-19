#!/usr/bin/env python3
"""
既存シナリオ（6-30）を要件定義書に基づいて修正するスクリプト
自己肯定感向上とセルフコンパッションに焦点を当てる
"""

import yaml
import os
from pathlib import Path

# 難易度の再定義マッピング
difficulty_mapping = {
    # 既存のbeginner/intermediate/advancedを適切に再マッピング
    6: "beginner",      # 休憩中の雑談
    7: "beginner",      # 電話での問い合わせ対応
    8: "beginner",      # 会議での意見発表
    9: "intermediate",  # 提案が却下された時
    10: "intermediate", # チームメンバーへの依頼
    11: "intermediate", # 上司からの急な業務依頼
    12: "intermediate", # クレーム対応
    13: "intermediate", # 同僚との意見の相違
    14: "intermediate", # 進捗報告
    15: "intermediate", # 新人への指導
    16: "advanced",     # プレゼンテーション
    17: "advanced",     # 交渉
    18: "advanced",     # 謝罪と関係修復
    19: "advanced",     # 昇進面接
    20: "advanced",     # 部署間の調整
    21: "beginner",     # 初対面の人との会話
    22: "intermediate", # フィードバックを受ける
    23: "intermediate", # 協力を求める
    24: "advanced",     # 難しい決定の説明
    25: "advanced",     # チームビルディング
    26: "beginner",     # 日常的な報告
    27: "intermediate", # 改善提案
    28: "advanced",     # リーダーシップ
    29: "advanced",     # 危機管理
    30: "advanced",     # ビジョンの共有
}

# サポーティブな要素を追加する関数
def add_supportive_elements(scenario_data, scenario_id):
    """既存のシナリオに自己肯定感向上の要素を追加"""
    
    # 基本情報は保持
    modified_scenario = scenario_data.copy()
    
    # 説明文に励ましの言葉を追加
    if "description" in modified_scenario:
        modified_scenario["description"] += " このシナリオを通じて、あなたの成長を一緒に確認しましょう。"
    
    # 難易度を適切に設定
    modified_scenario["difficulty"] = difficulty_mapping.get(scenario_id, "intermediate")
    
    # タグに自己肯定感関連を追加
    if "tags" in modified_scenario:
        if "自己肯定感" not in modified_scenario["tags"]:
            modified_scenario["tags"].append("自己肯定感")
        if "成長" not in modified_scenario["tags"]:
            modified_scenario["tags"].append("成長")
    
    # キャラクター設定をより共感的に
    if "character_setting" in modified_scenario:
        if "personality" in modified_scenario["character_setting"]:
            modified_scenario["character_setting"]["personality"] += " あなたの立場を理解し、成長を応援する姿勢を持っている。"
        
        if "speaking_style" in modified_scenario["character_setting"]:
            modified_scenario["character_setting"]["speaking_style"] += " 相手を尊重し、プレッシャーを与えない話し方を心がける。"
    
    # 学習ポイントをポジティブに
    if "learning_points" in modified_scenario:
        modified_scenario["learning_points"].append("どんな対応でも、チャレンジしたことに価値がある")
        modified_scenario["learning_points"].append("完璧を求めず、自分らしさを大切にする")
    
    # フィードバックポイントを全面的に書き換え
    new_feedback = {
        "excellent": [],
        "good_points": [],
        "next_steps": [],
        "self_compassion": []
    }
    
    # 既存のpositiveフィードバックを活用
    if "feedback_points" in scenario_data and "positive" in scenario_data["feedback_points"]:
        for point in scenario_data["feedback_points"]["positive"]:
            new_feedback["excellent"].append(point + " 素晴らしい成長です！")
    else:
        new_feedback["excellent"] = [
            "このシナリオに挑戦したこと自体が勇気ある一歩です",
            "あなたなりの対応ができたことを誇りに思ってください",
            "相手のことを考えながら対応できました"
        ]
    
    # good_pointsを追加
    new_feedback["good_points"] = [
        "緊張しながらも、最後まで対話を続けられました",
        "自分の気持ちを大切にしながら対応できています",
        "相手との関係を大切にしようとする姿勢が見えます"
    ]
    
    # negativeをnext_stepsに変換
    if "feedback_points" in scenario_data and "negative" in scenario_data["feedback_points"]:
        for point in scenario_data["feedback_points"]["negative"]:
            # ネガティブな表現をポジティブな提案に変換
            new_feedback["next_steps"].append("次回は" + point.replace("できていない", "を意識してみると良いかも"))
    else:
        new_feedback["next_steps"] = [
            "もう少し自信を持って話してみても大丈夫です",
            "相手の反応を見ながら、ペースを調整してみましょう",
            "今回の経験を活かして、次はさらに良くなります"
        ]
    
    # self_compassionを追加
    new_feedback["self_compassion"] = [
        "誰もが同じような場面で緊張します。あなただけではありません",
        "今日の練習が、明日の実践につながります",
        "完璧でなくていい。少しずつ成長していけば十分です",
        "自分に優しくすることも、大切なスキルです"
    ]
    
    modified_scenario["feedback_points"] = new_feedback
    
    return modified_scenario

def process_scenario_file(file_path, scenario_id):
    """シナリオファイルを読み込み、修正して保存"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            scenario_data = yaml.safe_load(f)
        
        # サポーティブな要素を追加
        modified_scenario = add_supportive_elements(scenario_data, scenario_id)
        
        # ファイルを上書き保存
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(modified_scenario, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        print(f"✅ シナリオ{scenario_id}を修正しました: {file_path}")
        return True
        
    except FileNotFoundError:
        print(f"⚠️ シナリオ{scenario_id}のファイルが見つかりません: {file_path}")
        return False
    except Exception as e:
        print(f"❌ シナリオ{scenario_id}の処理中にエラー: {e}")
        return False

def main():
    """メイン処理"""
    print("既存シナリオ（6-30）を要件定義書に基づいて修正します...")
    print("=" * 60)
    
    scenarios_dir = Path("scenarios/data")
    successful_count = 0
    
    # シナリオ6-30を処理
    for scenario_id in range(6, 31):
        file_path = scenarios_dir / f"scenario{scenario_id}.yaml"
        if process_scenario_file(file_path, scenario_id):
            successful_count += 1
    
    print("=" * 60)
    print(f"✅ 修正完了: {successful_count}/25 シナリオを更新しました")
    
    if successful_count < 25:
        print("⚠️ 一部のシナリオが見つからなかったか、エラーが発生しました")
        print("必要に応じて個別に確認してください")

if __name__ == "__main__":
    main()