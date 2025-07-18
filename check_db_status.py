#!/usr/bin/env python3
"""
データベースとテーブルの状態を確認するスクリプト
"""
import os
import sys
from flask import Flask
from database import init_database
from models import db, User

# アプリケーションのセットアップ
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# データベースの初期化
if not init_database(app):
    print("❌ データベース接続に失敗しました")
    sys.exit(1)

with app.app_context():
    try:
        # テーブルの存在確認
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        print("=== データベースの状態 ===")
        print(f"接続先: {app.config.get('SQLALCHEMY_DATABASE_URI', 'セッションベースモード')}")
        print(f"\n既存のテーブル: {tables}")
        
        if 'users' in tables:
            print("\n✅ usersテーブルが存在します")
            
            # ユーザー数を確認
            user_count = User.query.count()
            print(f"ユーザー数: {user_count}")
            
            # 既存ユーザーをリスト
            if user_count > 0:
                print("\n既存のユーザー:")
                users = User.query.all()
                for user in users:
                    print(f"  - ID: {user.id}, ユーザー名: {user.username}, メール: {user.email}")
        else:
            print("\n❌ usersテーブルが存在しません")
            print("create_user_table.py を実行してテーブルを作成してください")
            
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")