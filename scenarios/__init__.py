"""
シナリオモジュールの初期化
"""

import os
import yaml
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
    
    return scenarios 