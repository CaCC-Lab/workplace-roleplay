"""
シナリオモジュールの初期化
"""

import os
import yaml
import re
from typing import Dict, Any

def load_scenarios() -> Dict[str, Any]:
    """
    scenarios/dataディレクトリ内の全シナリオYAMLファイルをロードする
    """
    scenarios = {}
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
    # YAMLファイルを探してロード
    for filename in os.listdir(data_dir):
        if filename.endswith('.yaml') or filename.endswith('.yml'):
            scenario_id = filename.rsplit('.', 1)[0]  # 拡張子を除去
            try:
                with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as f:
                    scenarios[scenario_id] = yaml.safe_load(f)
            except Exception as e:
                print(f"Error loading scenario {filename}: {e}")
    
    # シナリオIDを自然な順序でソート（scenario1, scenario2, ..., scenario10）
    def natural_sort_key(scenario_id):
        """
        自然な順序でソートするためのキー関数
        'scenario1'のような文字列から数値部分を取り出してソートする
        """
        # 数値部分を抽出 (例: 'scenario123' -> 123)
        match = re.search(r'(\d+)$', scenario_id)
        if match:
            return int(match.group(1))  # 数値部分を整数として返す
        return 0  # 数値がない場合は0を返す
    
    # シナリオIDを自然な順序でソートした新しい辞書を作成
    sorted_scenarios = {}
    for key in sorted(scenarios.keys(), key=natural_sort_key):
        sorted_scenarios[key] = scenarios[key]
    
    # デバッグログを出力
    scenario_order = list(sorted_scenarios.keys())
    print(f"Loaded {len(sorted_scenarios)} scenarios in natural sort order")
    print(f"First 5 scenarios: {scenario_order[:5] if len(scenario_order) >= 5 else scenario_order}")
    
    return sorted_scenarios 