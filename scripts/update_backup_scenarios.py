#!/usr/bin/env python3
"""
バックアップシナリオを更新してIDを追加し、difficulty値を標準化する
"""
import os
import re

# 更新するシナリオのマッピング
scenario_mapping = {
    "scenario43.yaml": {"id": 43, "original": "scenario10.yaml"},
    "scenario44.yaml": {"id": 44, "original": "scenario11.yaml"},
    "scenario45.yaml": {"id": 45, "original": "scenario12.yaml"},
    "scenario46.yaml": {"id": 46, "original": "scenario13.yaml"},
    "scenario47.yaml": {"id": 47, "original": "scenario17.yaml"},
    "scenario48.yaml": {"id": 48, "original": "scenario18.yaml"},
    "scenario49.yaml": {"id": 49, "original": "scenario19.yaml"},
    "scenario50.yaml": {"id": 50, "original": "scenario21.yaml"},
}

# difficulty値のマッピング
difficulty_mapping = {
    "初級": "beginner",
    "中級": "intermediate",
    "上級": "advanced"
}

def update_scenario(filepath, scenario_id):
    """シナリオファイルを更新"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # コメント行を削除
    content = re.sub(r'^#.*\n', '', content, flags=re.MULTILINE)
    
    # IDを最初に追加
    if not content.startswith('id:'):
        content = f'id: {scenario_id}\n' + content
    
    # difficulty値を更新
    for ja_diff, en_diff in difficulty_mapping.items():
        content = re.sub(f'difficulty: {ja_diff}', f'difficulty: {en_diff}', content)
    
    # その他の必要な修正
    # character_settingにinitial_approachがない場合は追加
    if 'initial_approach:' not in content and 'character_setting:' in content:
        # character_settingの最後に追加
        lines = content.split('\n')
        new_lines = []
        in_character_setting = False
        indent_level = 0
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            if 'character_setting:' in line:
                in_character_setting = True
                indent_level = len(line) - len(line.lstrip())
            elif in_character_setting and line.strip() and not line.startswith(' '):
                # character_settingが終わった
                new_lines.insert(-1, f"{' ' * (indent_level + 2)}initial_approach: |")
                new_lines.insert(-1, f"{' ' * (indent_level + 4)}「おはようございます。」")
                in_character_setting = False
        
        content = '\n'.join(new_lines)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated {filepath}")

# メイン処理
if __name__ == "__main__":
    scenarios_dir = "scenarios/data"
    
    for filename, info in scenario_mapping.items():
        filepath = os.path.join(scenarios_dir, filename)
        if os.path.exists(filepath):
            update_scenario(filepath, info['id'])
        else:
            print(f"File not found: {filepath}")