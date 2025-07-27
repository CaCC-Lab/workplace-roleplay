#!/usr/bin/env python
"""
AIペルソナシステムのマイグレーション作成スクリプト

新しいペルソナテーブルのマイグレーションを作成します
"""
import os
import sys
from flask import Flask
from flask_migrate import Migrate, init, migrate as flask_migrate_cmd, upgrade

# アプリケーションのインポート
from app import app
from database import db, init_database
from models import AIPersona, PersonaMemory, PersonaScenarioConfig, UserPersonaInteraction

def create_persona_migration():
    """ペルソナテーブルのマイグレーションを作成"""
    with app.app_context():
        # Migrateの初期化
        migrate_obj = Migrate(app, db)
        
        # migrationsディレクトリが存在しない場合は初期化
        if not os.path.exists('migrations'):
            print("Migrationsディレクトリを初期化しています...")
            init()
        
        # マイグレーションを作成
        print("AIペルソナシステムのマイグレーションを作成しています...")
        try:
            flask_migrate_cmd(message="Add AI Persona system tables")
            print("✅ マイグレーションが正常に作成されました")
            
            # マイグレーションを適用するか確認
            apply = input("\nマイグレーションを適用しますか？ (y/n): ")
            if apply.lower() == 'y':
                print("マイグレーションを適用しています...")
                upgrade()
                print("✅ マイグレーションが正常に適用されました")
                
                # ペルソナデータを読み込むか確認
                load_personas = input("\n初期ペルソナデータを読み込みますか？ (y/n): ")
                if load_personas.lower() == 'y':
                    from services.persona_service import persona_service
                    persona_service.load_personas_from_yaml()
                    print("✅ ペルソナデータが正常に読み込まれました")
            else:
                print("マイグレーションの適用をスキップしました")
                print("後で適用するには以下のコマンドを実行してください:")
                print("  flask db upgrade")
                
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            print("\nデバッグ情報:")
            print(f"  - データベースURI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
            print(f"  - Migrationsディレクトリ: {'存在' if os.path.exists('migrations') else '存在しない'}")
            return False
        
    return True

if __name__ == "__main__":
    create_persona_migration()