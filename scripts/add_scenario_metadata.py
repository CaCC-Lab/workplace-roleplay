#!/usr/bin/env python3
"""
シナリオYAMLファイルにメタデータ（target_strengths、difficulty）を一括追加するスクリプト

各シナリオの内容を分析して適切なスキルと難易度を設定
"""
import os
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any


# スキルマッピング辞書
SKILL_MAPPING = {
    'empathy': ['共感', '理解', '感情', '気持ち', 'メンタル', '心理', '悩み', '不安', '相談', 'カウンセリング', 'メンター'],
    'clarity': ['説明', '明確', '伝える', '報告', 'プレゼン', '発表', '資料', '提案', '企画', '要約'],
    'active_listening': ['聞く', '傾聴', '質問', 'ヒアリング', '相談', '面談', 'インタビュー', '対話'],
    'adaptability': ['変更', '調整', '柔軟', '対応', '適応', '交渉', '協調', '妥協', 'バランス', '課題解決'],
    'positivity': ['前向き', 'ポジティブ', '励まし', '褒める', '感謝', 'チーム', '協力', 'モチベーション'],
    'professionalism': ['挨拶', 'マナー', '敬語', 'ビジネス', '顧客', '会議', '報連相', '責任', 'リーダー', '管理']
}

# 難易度マッピング
DIFFICULTY_MAPPING = {
    'pre-beginner': 1,
    'beginner': 2,
    'intermediate': 3,
    'advanced': 4,
    'expert': 5
}


def analyze_scenario_content(scenario: Dict[str, Any]) -> List[str]:
    """
    シナリオの内容を分析してtarget_strengthsを決定
    
    Args:
        scenario: シナリオデータ
        
    Returns:
        適用可能なスキルリスト
    """
    content_text = ""
    
    # 分析対象のテキストを結合
    content_text += scenario.get('title', '') + " "
    content_text += scenario.get('description', '') + " "
    content_text += " ".join(scenario.get('tags', [])) + " "
    
    if 'learning_points' in scenario:
        content_text += " ".join(scenario['learning_points']) + " "
    
    content_text = content_text.lower()
    
    # 各スキルとの関連度をチェック
    matching_skills = []
    skill_scores = {}
    
    for skill, keywords in SKILL_MAPPING.items():
        score = 0
        for keyword in keywords:
            score += content_text.count(keyword.lower())
        
        if score > 0:
            skill_scores[skill] = score
    
    # スコア順でソートして上位2-3個を選択
    sorted_skills = sorted(skill_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 最低1つ、最大3つのスキルを選択
    selected_skills = []
    for skill, score in sorted_skills[:3]:
        if score > 0:
            selected_skills.append(skill)
    
    # スキルが特定できない場合のデフォルト
    if not selected_skills:
        # タグベースの簡易判定
        tags = [tag.lower() for tag in scenario.get('tags', [])]
        if any(tag in ['挨拶', 'マナー', '基本'] for tag in tags):
            selected_skills = ['professionalism']
        elif any(tag in ['対応', '顧客', '調整'] for tag in tags):
            selected_skills = ['adaptability', 'professionalism']
        else:
            selected_skills = ['clarity', 'professionalism']
    
    return selected_skills


def determine_difficulty(scenario: Dict[str, Any]) -> int:
    """
    シナリオの難易度を決定
    
    Args:
        scenario: シナリオデータ
        
    Returns:
        難易度（1-5）
    """
    current_difficulty = scenario.get('difficulty', 'intermediate')
    return DIFFICULTY_MAPPING.get(current_difficulty, 3)


def add_metadata_to_scenario(file_path: Path) -> bool:
    """
    単一のシナリオファイルにメタデータを追加
    
    Args:
        file_path: シナリオファイルのパス
        
    Returns:
        成功したかどうか
    """
    try:
        # YAMLファイルを読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            scenario = yaml.safe_load(f)
        
        # すでにmetadataが存在する場合はスキップ
        if 'metadata' in scenario:
            print(f"Skipping {file_path.name} - metadata already exists")
            return True
        
        # スキルと難易度を分析
        target_strengths = analyze_scenario_content(scenario)
        difficulty = determine_difficulty(scenario)
        
        # メタデータを追加
        scenario['metadata'] = {
            'target_strengths': target_strengths,
            'difficulty': difficulty
        }
        
        # ファイルに書き戻し
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(scenario, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        print(f"Updated {file_path.name}: {target_strengths}, difficulty={difficulty}")
        return True
        
    except Exception as e:
        print(f"Error processing {file_path.name}: {str(e)}")
        return False


def main():
    """メイン処理"""
    # scenarios/dataディレクトリのパス
    scenarios_dir = Path(__file__).parent.parent / 'scenarios' / 'data'
    
    if not scenarios_dir.exists():
        print(f"Scenarios directory not found: {scenarios_dir}")
        return
    
    # 全YAMLファイルを処理
    yaml_files = list(scenarios_dir.glob('*.yaml'))
    
    print(f"Found {len(yaml_files)} scenario files")
    print("Adding metadata to scenario files...")
    
    success_count = 0
    for yaml_file in sorted(yaml_files):
        if add_metadata_to_scenario(yaml_file):
            success_count += 1
    
    print(f"\nCompleted: {success_count}/{len(yaml_files)} files updated successfully")
    
    # 結果の確認（いくつかのファイルをサンプル表示）
    print("\nSample results:")
    sample_files = yaml_files[:3]  # 最初の3ファイルをサンプル
    
    for yaml_file in sample_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                scenario = yaml.safe_load(f)
            
            if 'metadata' in scenario:
                metadata = scenario['metadata']
                print(f"{yaml_file.name}: {metadata['target_strengths']}, difficulty={metadata['difficulty']}")
        except Exception as e:
            print(f"Error reading {yaml_file.name}: {str(e)}")


if __name__ == "__main__":
    main()