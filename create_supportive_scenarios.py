#!/usr/bin/env python3
"""
要件定義書に基づいた、自己肯定感を高めるシナリオを作成するスクリプト
"""

import yaml
import os
from pathlib import Path

# 新しいpre-beginnerレベルのシナリオ
pre_beginner_scenarios = {
    1: {
        "id": 1,
        "title": "朝の挨拶から始めよう",
        "description": "オフィスで出会った人に挨拶をする練習です。まずは「おはようございます」と返すだけで大丈夫。あなたのペースで進めましょう。",
        "difficulty": "pre-beginner",
        "tags": ["挨拶", "基本", "朝の場面", "安心"],
        "role_info": "AIは優しい先輩社員、あなたは新しく入った社員",
        "character_setting": {
            "personality": "30代の優しい先輩。新人の緊張を理解していて、温かく見守ってくれる。自分も最初は緊張していたことを覚えている。",
            "speaking_style": "「おはよう！」「大丈夫だよ」など、親しみやすくプレッシャーを与えない話し方。笑顔が多い。",
            "situation": "朝、エレベーターホールで偶然会った。先輩も少し眠そうで、リラックスした雰囲気。",
            "initial_approach": "「あ、おはよう！今日は少し暖かいね。眠い月曜日の朝だけど、ゆっくりいこう～」"
        },
        "learning_points": [
            "挨拶を返すことができれば、それだけで素晴らしいコミュニケーション",
            "相手も人間だから、完璧じゃなくていいことを知る",
            "自分のペースで少しずつ会話を広げていける"
        ],
        "feedback_points": {
            "excellent": [
                "挨拶を返せたこと自体が、とても勇気のいる素晴らしい一歩です",
                "相手の話を聞こうとする姿勢が見えました",
                "緊張しながらも応答できたあなたは、確実に成長しています"
            ],
            "good_points": [
                "声が小さくても、相手に伝わろうとする気持ちが大切",
                "タイミングが遅れても、挨拶しようとしたその勇気を認めましょう",
                "短い返事でも、それがあなたの精一杯なら100点満点です"
            ],
            "next_steps": [
                "次は自分から「おはようございます」と言ってみるのもいいかも",
                "でも焦る必要はありません。今のペースで十分です",
                "相手の目を一瞬でも見られたら、さらに素敵ですね"
            ],
            "self_compassion": [
                "緊張するのは当たり前。みんな最初は同じように感じています",
                "今日の小さな挨拶が、明日の大きな自信につながります",
                "完璧じゃなくていい。あなたらしさが一番大切です"
            ]
        }
    },
    
    2: {
        "id": 2,
        "title": "「ありがとう」を伝える練習",
        "description": "誰かに何かをしてもらった時、「ありがとう」と伝える練習です。感謝の気持ちを言葉にすることから始めましょう。",
        "difficulty": "pre-beginner",
        "tags": ["感謝", "基本", "日常", "温かい気持ち"],
        "role_info": "AIは親切な同僚、あなたは助けてもらった社員",
        "character_setting": {
            "personality": "同年代の親切な同僚。人助けが好きで、見返りを求めない。相手のペースを大切にする。",
            "speaking_style": "「どういたしまして」「お互い様だよ」など、相手を安心させる優しい話し方。",
            "situation": "書類を落としてしまったあなたを、同僚が手伝ってくれた場面。",
            "initial_approach": "「あ、大丈夫？一緒に拾うよ。たくさん落ちちゃったね、手伝うから気にしないで」"
        },
        "learning_points": [
            "「ありがとう」の一言が、相手も自分も温かい気持ちにする",
            "感謝を伝えることは、素敵な人間関係の第一歩",
            "言葉にすることで、自分の気持ちも整理される"
        ],
        "feedback_points": {
            "excellent": [
                "感謝の気持ちを言葉にできたことが素晴らしいです",
                "相手の親切を受け入れられる柔軟さがあります",
                "「ありがとう」と言えるあなたは、周りを明るくする力があります"
            ],
            "good_points": [
                "言葉にならなくても、感謝の気持ちは表情で伝わっています",
                "助けを受け入れられることも、大切な強さです",
                "小さな声でも、あなたの「ありがとう」には価値があります"
            ],
            "next_steps": [
                "慣れてきたら「○○してくれて、ありがとう」と具体的に伝えてみては",
                "でも今は「ありがとう」だけで十分素敵です",
                "相手の反応を見て、お互いが笑顔になれたら最高ですね"
            ],
            "self_compassion": [
                "助けてもらうことは恥ずかしいことじゃありません",
                "感謝を伝えられるあなたは、既に素敵な人です",
                "一つ一つの「ありがとう」が、あなたの成長の証です"
            ]
        }
    },
    
    3: {
        "id": 3,
        "title": "体調を聞かれた時の返事",
        "description": "「調子はどう？」と聞かれた時の返事の練習です。正直に、でも相手を心配させすぎない程度に答えてみましょう。",
        "difficulty": "pre-beginner",
        "tags": ["体調", "日常会話", "自己開示", "基本"],
        "role_info": "AIは気遣いのできる上司、あなたは部下",
        "character_setting": {
            "personality": "40代の理解ある上司。部下の健康を本当に気にかけている。プレッシャーは与えない。",
            "speaking_style": "「無理しなくていいよ」「体が一番大事」など、部下を思いやる温かい話し方。",
            "situation": "朝、あなたの顔色を見て、上司が声をかけてくれた。",
            "initial_approach": "「おはよう。なんだか疲れてる顔してるけど、大丈夫？無理しないでね」"
        },
        "learning_points": [
            "自分の状態を素直に伝えることの大切さ",
            "相手は本当に心配してくれていることを知る",
            "「大丈夫」以外の答え方もあることを学ぶ"
        ],
        "feedback_points": {
            "excellent": [
                "自分の状態を正直に伝えられたことが素晴らしいです",
                "相手の心配を受け止められる素直さがあります",
                "体調について話せることは、信頼関係の第一歩です"
            ],
            "good_points": [
                "「大丈夫」と答えるだけでも、応答できています",
                "相手を心配させまいとする優しさが感じられます",
                "短い返事でも、コミュニケーションは成立しています"
            ],
            "next_steps": [
                "時には「少し疲れています」と正直に言ってもいいんです",
                "相手はあなたの味方だということを覚えておいて",
                "体調を共有することで、お互いに配慮し合えます"
            ],
            "self_compassion": [
                "疲れていることは恥ずかしいことではありません",
                "自分の体調を大切にすることは、とても重要です",
                "正直に話せる相手がいることに感謝しましょう"
            ]
        }
    },
    
    4: {
        "id": 4,
        "title": "わからないことを聞く勇気",
        "description": "仕事でわからないことがあった時、「教えてください」と聞く練習です。知らないことは恥ずかしくありません。",
        "difficulty": "beginner",
        "tags": ["質問", "学習", "勇気", "成長"],
        "role_info": "AIは教えることが好きな先輩、あなたは質問したい後輩",
        "character_setting": {
            "personality": "教えることが大好きな先輩。質問されると嬉しそうに説明してくれる。決して見下したりしない。",
            "speaking_style": "「いい質問だね！」「聞いてくれてありがとう」など、質問を歓迎する話し方。",
            "situation": "新しいシステムの使い方がわからなくて困っている。",
            "initial_approach": "「その作業、初めてだと難しいよね。私も最初は全然わからなかったよ。何か困ってることある？」"
        },
        "learning_points": [
            "わからないことを聞くのは、成長への第一歩",
            "質問することで、相手も教える喜びを感じる",
            "知らないことを認める勇気の大切さ"
        ],
        "feedback_points": {
            "excellent": [
                "わからないことを素直に聞けたことが素晴らしいです",
                "学ぼうとする姿勢が、あなたの強みです",
                "質問できる勇気は、多くの人が持てない貴重な能力です"
            ],
            "good_points": [
                "聞きたそうな様子が伝わっていました",
                "タイミングを見計らっていた配慮が素敵です",
                "小さな質問から始めるのは賢明な方法です"
            ],
            "next_steps": [
                "次は「ここがわからない」と具体的に聞いてみても",
                "メモを取りながら聞くと、さらに理解が深まります",
                "お礼を言うことも忘れずに。でも今は聞けただけで十分です"
            ],
            "self_compassion": [
                "誰でも最初はわからないことだらけです",
                "質問することは、あなたが真剣に取り組んでいる証拠",
                "今日の勇気ある一歩を、自分で褒めてあげてください"
            ]
        }
    },
    
    5: {
        "id": 5,
        "title": "休憩時間の雑談デビュー",
        "description": "休憩室で同僚と軽い雑談をする練習です。天気の話から始めれば、プレッシャーも少ないはず。",
        "difficulty": "beginner",
        "tags": ["雑談", "休憩", "リラックス", "日常"],
        "role_info": "AIはフレンドリーな同僚、あなたは休憩中の社員",
        "character_setting": {
            "personality": "話しやすい同僚。相手のペースに合わせて会話ができる。沈黙も苦にしない。",
            "speaking_style": "「そうだよね～」「わかる！」など、共感的で気楽な話し方。",
            "situation": "休憩室でコーヒーを飲んでいたら、同僚も休憩に来た。",
            "initial_approach": "「お疲れ様～。今日は天気いいね。休憩室から見える空が気持ちいいよ」"
        },
        "learning_points": [
            "雑談は完璧である必要はないこと",
            "共通の話題（天気など）から始めると楽",
            "短い会話でも、人間関係を築く大切な一歩"
        ],
        "feedback_points": {
            "excellent": [
                "リラックスした雰囲気で会話に参加できました",
                "相手の話に反応を示せたことが素晴らしいです",
                "雑談を楽しもうとする姿勢が見えました"
            ],
            "good_points": [
                "相槌を打つだけでも、立派な会話の参加です",
                "笑顔で聞いている姿勢が、相手に安心感を与えます",
                "短い返事でも、あなたらしさが表れています"
            ],
            "next_steps": [
                "次は自分からも一言、天気について話してみては",
                "でも聞き役に徹するのも、素敵なコミュニケーションです",
                "相手も話を聞いてもらえて嬉しいはずです"
            ],
            "self_compassion": [
                "雑談が苦手でも、それはあなたの個性です",
                "少しずつ慣れていけば大丈夫",
                "今日の小さな会話も、大切な経験値になっています"
            ]
        }
    }
}

# 既存シナリオの修正関数
def create_supportive_version(scenario_data, scenario_id):
    """既存のシナリオを自己肯定感重視のバージョンに変換"""
    
    # 基本構造は維持しつつ、内容を大幅に修正
    supportive_scenario = {
        "id": scenario_id,
        "title": scenario_data.get("title", ""),
        "description": scenario_data.get("description", "") + " どんな対応でも、チャレンジしたことに価値があります。",
        "difficulty": scenario_data.get("difficulty", "intermediate"),
        "tags": scenario_data.get("tags", []) + ["自己肯定感", "成長"],
        "role_info": scenario_data.get("role_info", ""),
        "character_setting": scenario_data.get("character_setting", {}),
        "learning_points": scenario_data.get("learning_points", []),
        "feedback_points": {
            "excellent": [],
            "good_points": [],
            "next_steps": [],
            "self_compassion": []
        }
    }
    
    # character_settingの調整（より共感的に）
    if "personality" in supportive_scenario["character_setting"]:
        supportive_scenario["character_setting"]["personality"] += " 相手の立場を理解し、プレッシャーを与えない。"
    
    # feedback_pointsの変換
    original_feedback = scenario_data.get("feedback_points", {})
    
    # positiveをexcellentに
    if "positive" in original_feedback:
        supportive_scenario["feedback_points"]["excellent"] = [
            point + " これができるあなたは素晴らしいです。" 
            for point in original_feedback["positive"]
        ]
    
    # good_pointsを追加
    supportive_scenario["feedback_points"]["good_points"] = [
        "チャレンジしようとした勇気を認めましょう",
        "完璧でなくても、あなたなりに考えて行動したことに価値があります",
        "この経験が、必ず次につながります"
    ]
    
    # negativeをnext_stepsに変換（ポジティブに）
    if "negative" in original_feedback:
        supportive_scenario["feedback_points"]["next_steps"] = [
            "もし" + point + "となったとしても、それは学びの機会です"
            for point in original_feedback["negative"]
        ]
    
    # self_compassionを追加
    supportive_scenario["feedback_points"]["self_compassion"] = [
        "誰もが同じような場面で悩みます。あなただけではありません",
        "今日の経験は、明日のあなたを強くします",
        "自分のペースで成長していけば大丈夫です"
    ]
    
    return supportive_scenario

def save_scenario(scenario_data, filename):
    """シナリオをYAMLファイルとして保存"""
    output_path = Path(f"scenarios/data/{filename}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(scenario_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"Created: {output_path}")

def main():
    """メイン処理"""
    print("要件定義書に基づいたシナリオ作成を開始します...")
    
    # 1. pre-beginnerシナリオの作成
    print("\n1. Pre-beginnerレベルのシナリオを作成中...")
    for scenario_id, scenario_data in pre_beginner_scenarios.items():
        save_scenario(scenario_data, f"scenario{scenario_id}.yaml")
    
    # 2. 既存シナリオ（6-10）をbeginnerレベルに調整
    print("\n2. Beginnerレベルのシナリオを修正中...")
    
    # ここでは既存のシナリオを読み込んで修正する
    # （実際の実装では既存ファイルを読み込んで処理）
    
    print("\n✅ シナリオの作成が完了しました！")
    print("次のステップ: 作成したシナリオをテストし、フィードバックを収集してください。")

if __name__ == "__main__":
    main()