#!/usr/bin/env python3
"""
データベースマイグレーション作成スクリプト

Flask-Migrateを使用してユーザー認証テーブルのマイグレーションを作成
"""
import os
import sys
from flask import Flask
from flask_migrate import Migrate, init, migrate as flask_migrate
from database import init_database
from models import db

# アプリケーションのセットアップ
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# データベースとマイグレーションの初期化
init_database(app)
migrate_instance = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        # マイグレーションディレクトリの初期化（既に存在する場合はスキップ）
        if not os.path.exists('migrations'):
            print("マイグレーションディレクトリを初期化中...")
            init()
        
        # 新しいマイグレーションを作成
        print("新しいマイグレーションを作成中...")
        try:
            flask_migrate(message="Add user authentication tables")
            print("✅ マイグレーションが正常に作成されました")
            print("次のコマンドでマイグレーションを適用してください:")
            print("  flask db upgrade")
        except Exception as e:
            print(f"❌ マイグレーション作成エラー: {e}")
            sys.exit(1)