#!/usr/bin/env python3
"""
残りのシナリオ（6-30）に「職場のあなた再現シート」の要素を追加するスクリプト
Ministry of Health, Labour and Welfareの「職場のあなた再現シート」に基づく
"""

import yaml
import os

def load_yaml_file(filepath):
    """YAMLファイルを読み込む"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml_file(filepath, data):
    """YAMLファイルを保存"""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, 
                 default_flow_style=False, width=1000)

def get_typical_responses_for_scenario(scenario_id, difficulty):
    """シナリオに応じた典型的な反応パターンを返す"""
    
    # 指導・教育系（6, 8）
    if scenario_id in [6, 8]:
        return [
            {
                "pattern": "過度な責任感型",
                "description": "全てを完璧に教えようとして混乱を招く",
                "example": "えっと、まず...あ、その前に...いや、これも大事で...",
                "underlying_feeling": "相手に申し訳ない、失敗したくない"
            },
            {
                "pattern": "回避型",
                "description": "教えることを避けて他の人に任せようとする",
                "example": "私より〇〇さんの方が詳しいので...",
                "underlying_feeling": "自信のなさ、責任を負いたくない"
            },
            {
                "pattern": "威圧型",
                "description": "緊張から必要以上に厳しくなる",
                "example": "前も言いましたよね？ちゃんと聞いてました？",
                "underlying_feeling": "不安を隠すための防御反応"
            }
        ]
    
    # 謝罪・クレーム系（7, 16, 17）
    elif scenario_id in [7, 16, 17]:
        return [
            {
                "pattern": "過剰謝罪型",
                "description": "必要以上に謝り続ける",
                "example": "本当にすみません、すみません、申し訳ございません...",
                "underlying_feeling": "強い罪悪感、自己否定"
            },
            {
                "pattern": "防御型",
                "description": "言い訳を並べて自己防衛",
                "example": "いや、それは私じゃなくて...システムが...",
                "underlying_feeling": "責任を認めることへの恐怖"
            },
            {
                "pattern": "フリーズ型",
                "description": "何も言えずに固まってしまう",
                "example": "...（無言）...",
                "underlying_feeling": "パニック、思考停止"
            }
        ]
    
    # 会議・発表系（9, 11, 12, 13, 24）
    elif scenario_id in [9, 11, 12, 13, 24]:
        return [
            {
                "pattern": "小声型",
                "description": "声が小さくて聞き取れない",
                "example": "（ぼそぼそ）...だと思います...",
                "underlying_feeling": "自信のなさ、注目されることへの恐怖"
            },
            {
                "pattern": "早口型",
                "description": "緊張で早口になり内容が伝わらない",
                "example": "えーっとですねこれはつまりその...",
                "underlying_feeling": "早く終わらせたい、緊張"
            },
            {
                "pattern": "過剰準備型",
                "description": "資料を読み上げるだけで終わる",
                "example": "資料の通りですが、1ページ目から...",
                "underlying_feeling": "失敗への恐怖、完璧主義"
            }
        ]
    
    # 交渉・調整系（10, 14, 15, 18, 19, 20）
    elif scenario_id in [10, 14, 15, 18, 19, 20]:
        return [
            {
                "pattern": "即承諾型",
                "description": "相手の要求を全て受け入れてしまう",
                "example": "はい、分かりました。それで大丈夫です。",
                "underlying_feeling": "対立を避けたい、嫌われたくない"
            },
            {
                "pattern": "先延ばし型",
                "description": "決断を避けて曖昧にする",
                "example": "ちょっと確認してからでもいいですか...",
                "underlying_feeling": "決断への不安、責任回避"
            },
            {
                "pattern": "過度な譲歩型",
                "description": "自分を犠牲にして相手に合わせる",
                "example": "私が我慢すれば済むことなので...",
                "underlying_feeling": "自己犠牲、自己価値の低さ"
            }
        ]
    
    # その他・日常会話系
    else:
        return [
            {
                "pattern": "最小限応答型",
                "description": "必要最小限の返事だけ",
                "example": "はい。そうですね。",
                "underlying_feeling": "会話を早く終わらせたい"
            },
            {
                "pattern": "話題回避型",
                "description": "別の話題に逸らそうとする",
                "example": "そういえば、別の件ですが...",
                "underlying_feeling": "苦手な話題から逃げたい"
            },
            {
                "pattern": "同調過多型",
                "description": "相手に過度に同調する",
                "example": "本当にその通りです！私もそう思います！",
                "underlying_feeling": "認められたい、好かれたい"
            }
        ]

def get_alternative_approaches_for_scenario(scenario_id, difficulty):
    """シナリオに応じた代替アプローチを返す"""
    
    # 指導・教育系
    if scenario_id in [6, 8]:
        return [
            {
                "approach": "段階的説明",
                "example": "まず一番大事なポイントから説明しますね。これができたら次に進みましょう",
                "benefit": "相手の理解度に合わせて進められる",
                "practice_point": "一度に全部教えようとしない"
            },
            {
                "approach": "共感的指導",
                "example": "私も最初は同じところで迷いました。一緒に確認していきましょう",
                "benefit": "相手の不安を和らげながら教えられる",
                "practice_point": "自分の経験を交えて親近感を作る"
            },
            {
                "approach": "確認型指導",
                "example": "ここまでで分からないところはありますか？遠慮なく聞いてくださいね",
                "benefit": "相手の理解度を確認しながら進められる",
                "practice_point": "質問しやすい雰囲気を作る"
            }
        ]
    
    # 謝罪・クレーム系
    elif scenario_id in [7, 16, 17]:
        return [
            {
                "approach": "適切な謝罪",
                "example": "ご迷惑をおかけして申し訳ございません。まず状況を確認させていただけますか",
                "benefit": "誠実さを示しつつ冷静に対処できる",
                "practice_point": "謝罪と状況確認のバランス"
            },
            {
                "approach": "解決志向",
                "example": "申し訳ございません。今後このようなことがないよう、〇〇という対策を取ります",
                "benefit": "前向きな印象を与えられる",
                "practice_point": "謝罪だけでなく改善策も示す"
            },
            {
                "approach": "共感的対応",
                "example": "お気持ちお察しします。私も同じ立場なら困ってしまいます",
                "benefit": "相手の感情を受け止められる",
                "practice_point": "相手の立場に立って考える"
            }
        ]
    
    # 会議・発表系
    elif scenario_id in [9, 11, 12, 13, 24]:
        return [
            {
                "approach": "構造化発表",
                "example": "3つのポイントでお話しします。1つ目は...",
                "benefit": "聞き手にも自分にも分かりやすい",
                "practice_point": "話す内容を整理してから話す"
            },
            {
                "approach": "対話型発表",
                "example": "まず現状について皆さんの認識を確認したいのですが...",
                "benefit": "一方的でなく双方向のコミュニケーション",
                "practice_point": "聞き手を巻き込む"
            },
            {
                "approach": "ビジュアル活用",
                "example": "この図を見ていただくと分かりやすいと思います",
                "benefit": "言葉だけでなく視覚的に伝えられる",
                "practice_point": "資料を効果的に使う"
            }
        ]
    
    # 交渉・調整系
    elif scenario_id in [10, 14, 15, 18, 19, 20]:
        return [
            {
                "approach": "Win-Win探索",
                "example": "お互いにメリットがある方法を一緒に考えませんか",
                "benefit": "対立ではなく協力関係を作れる",
                "practice_point": "相手の利益も考慮する"
            },
            {
                "approach": "条件提示",
                "example": "その条件でしたら、こちらは〇〇していただければ可能です",
                "benefit": "一方的な譲歩を避けられる",
                "practice_point": "give and takeを意識する"
            },
            {
                "approach": "時間確保",
                "example": "重要な件なので、一度持ち帰って検討させていただけますか",
                "benefit": "冷静に判断する時間を作れる",
                "practice_point": "即断を避ける勇気"
            }
        ]
    
    # その他
    else:
        return [
            {
                "approach": "自然な応答",
                "example": "なるほど、それは大変でしたね",
                "benefit": "無理のない会話ができる",
                "practice_point": "素直な反応を大切にする"
            },
            {
                "approach": "質問返し",
                "example": "それについて、もう少し詳しく教えていただけますか",
                "benefit": "会話を深められる",
                "practice_point": "相手に興味を示す"
            },
            {
                "approach": "共感表現",
                "example": "私も似たような経験があります",
                "benefit": "親近感を作れる",
                "practice_point": "共通点を見つける"
            }
        ]

def get_skill_focus_for_scenario(scenario_id, title):
    """シナリオに応じたスキルフォーカスを返す"""
    
    skill_map = {
        6: {"primary": "指導・教育力", "secondary": ["忍耐力", "説明力", "相手のペースに合わせる力"]},
        7: {"primary": "謝罪・対応力", "secondary": ["冷静さ", "誠実さ", "問題解決志向"]},
        8: {"primary": "引き継ぎ力", "secondary": ["整理力", "説明力", "確認力"]},
        9: {"primary": "発言力", "secondary": ["要約力", "タイミング", "自己主張"]},
        10: {"primary": "スケジュール調整力", "secondary": ["交渉力", "優先順位付け", "断る勇気"]},
        11: {"primary": "プレゼンテーション力", "secondary": ["構成力", "話術", "資料作成"]},
        12: {"primary": "意見表明力", "secondary": ["論理性", "説得力", "自信"]},
        13: {"primary": "司会進行力", "secondary": ["時間管理", "まとめ力", "公平性"]},
        14: {"primary": "報連相", "secondary": ["タイミング", "要約力", "判断力"]},
        15: {"primary": "仕事の断り方", "secondary": ["アサーション", "代替案提示", "関係維持"]},
        16: {"primary": "電話応対", "secondary": ["声のトーン", "聞き取り力", "メモ力"]},
        17: {"primary": "クレーム対応", "secondary": ["傾聴力", "感情コントロール", "解決志向"]},
        18: {"primary": "チーム協力", "secondary": ["協調性", "役割分担", "サポート力"]},
        19: {"primary": "交渉力", "secondary": ["準備力", "柔軟性", "Win-Win思考"]},
        20: {"primary": "期限交渉", "secondary": ["現実的判断", "説明力", "代替案提示"]},
        21: {"primary": "異なる意見の調整", "secondary": ["中立性", "傾聴力", "まとめ力"]},
        22: {"primary": "リモートコミュニケーション", "secondary": ["明確な表現", "テキスト力", "タイミング"]},
        23: {"primary": "上司への相談", "secondary": ["要点整理", "タイミング", "提案力"]},
        24: {"primary": "緊急発表対応", "secondary": ["即応力", "冷静さ", "優先順位"]},
        25: {"primary": "フィードバック受容力", "secondary": ["素直さ", "改善志向", "感謝の表現"]},
        26: {"primary": "退職相談対応", "secondary": ["傾聴力", "守秘義務", "適切な助言"]},
        27: {"primary": "世代間コミュニケーション", "secondary": ["柔軟性", "敬語", "価値観の理解"]},
        28: {"primary": "飲み会参加力", "secondary": ["適度な距離感", "話題選び", "退席タイミング"]},
        29: {"primary": "部署間調整", "secondary": ["全体視点", "バランス感覚", "説明力"]},
        30: {"primary": "プロジェクト提案力", "secondary": ["企画力", "プレゼン力", "熱意の伝え方"]}
    }
    
    default_focus = {
        "primary": "コミュニケーション力",
        "secondary": ["傾聴力", "共感力", "表現力"]
    }
    
    focus = skill_map.get(scenario_id, default_focus)
    focus["workplace_relevance"] = f"{focus['primary']}は職場での信頼関係構築の基礎"
    
    return focus

def add_workplace_sheet_elements_to_remaining(scenario_data, scenario_id):
    """残りのシナリオに職場のあなた再現シート要素を追加"""
    
    adjusted_scenario = scenario_data.copy()
    
    # scenario_analysisセクションを追加
    adjusted_scenario["scenario_analysis"] = {
        "typical_responses": get_typical_responses_for_scenario(
            scenario_id, 
            scenario_data.get("difficulty", "intermediate")
        )
    }
    
    # self_reflection_promptsを追加
    adjusted_scenario["self_reflection_prompts"] = [
        "この場面で、あなたはどう感じましたか？",
        "なぜそのような対応を選びましたか？",
        "相手はどう感じたと思いますか？",
        "もし同じ場面に遭遇したら、どう対応したいですか？"
    ]
    
    # alternative_approachesを追加
    adjusted_scenario["alternative_approaches"] = get_alternative_approaches_for_scenario(
        scenario_id,
        scenario_data.get("difficulty", "intermediate")
    )
    
    # skill_focusを追加
    adjusted_scenario["skill_focus"] = get_skill_focus_for_scenario(
        scenario_id,
        scenario_data.get("title", "")
    )
    
    return adjusted_scenario

def main():
    """メイン処理"""
    scenario_dir = "/Users/ryu/dev/workplace-roleplay/scenarios/data"
    
    # シナリオ6-30を処理
    success_count = 0
    error_count = 0
    
    for i in range(6, 31):
        yaml_file = os.path.join(scenario_dir, f"scenario{i}.yaml")
        
        try:
            # YAMLファイルを読み込み
            scenario_data = load_yaml_file(yaml_file)
            
            # 職場のあなた再現シート要素を追加
            adjusted_data = add_workplace_sheet_elements_to_remaining(scenario_data, i)
            
            # ファイルを保存
            save_yaml_file(yaml_file, adjusted_data)
            
            print(f"✅ シナリオ{i}の調整が完了しました: {adjusted_data.get('title', '')}")
            success_count += 1
            
        except FileNotFoundError:
            print(f"⚠️ シナリオ{i}のファイルが見つかりません")
            error_count += 1
        except Exception as e:
            print(f"❌ シナリオ{i}の処理中にエラーが発生しました: {e}")
            error_count += 1
    
    print(f"\n処理完了: 成功 {success_count} / エラー {error_count}")

if __name__ == "__main__":
    main()