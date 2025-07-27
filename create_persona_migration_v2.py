#!/usr/bin/env python
"""
ペルソナシステムのデータベースマイグレーション作成スクリプト（改良版）
"""
import os
import sys
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 環境変数の設定
os.environ['FLASK_APP'] = 'app.py'

def create_migration():
    """マイグレーションファイルを作成"""
    try:
        # Flask-Migrateを使用してマイグレーションを生成
        from app import app
        from models import db
        from flask_migrate import Migrate, init, migrate, stamp
        
        with app.app_context():
            # Migrateの初期化
            migrate_instance = Migrate(app, db)
            
            # マイグレーションディレクトリが存在しない場合は初期化
            if not os.path.exists('migrations'):
                print("マイグレーションディレクトリを初期化しています...")
                init()
                stamp()  # 現在のデータベース状態をマークする
            
            # マイグレーションファイルの生成
            print("ペルソナシステムのマイグレーションを作成しています...")
            message = "Add AI Persona system tables"
            
            # マイグレーションの作成
            from flask_migrate import migrate as create_migration_command
            create_migration_command(message=message)
            
            print("マイグレーションファイルが正常に作成されました。")
            print("\n次のコマンドでマイグレーションを適用してください:")
            print("flask db upgrade")
            
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_migration()