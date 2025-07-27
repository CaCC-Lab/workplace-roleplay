#!/usr/bin/env python
"""
YAMLファイルからペルソナをデータベースに読み込むスクリプト
"""
import os
import sys

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import app
from services.persona_service import PersonaService

def load_personas():
    """ペルソナをYAMLファイルからデータベースに読み込む"""
    with app.app_context():
        service = PersonaService()
        
        print("ペルソナをYAMLファイルから読み込んでいます...")
        loaded_count = service.load_personas_from_yaml()
        
        print(f"\n✅ {loaded_count}個のペルソナを正常に読み込みました。")
        
        # 読み込まれたペルソナを確認
        from models import AIPersona
        personas = AIPersona.query.all()
        
        print("\n読み込まれたペルソナ:")
        for persona in personas:
            print(f"  - {persona.name} ({persona.persona_code})")
            print(f"    業界: {persona.industry.value}, 役職: {persona.role.value}")
            print(f"    性格: {persona.personality_type.value}")
            print(f"    経験年数: {persona.years_experience}年")
            print()

if __name__ == "__main__":
    load_personas()