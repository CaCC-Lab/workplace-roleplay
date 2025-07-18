#!/usr/bin/env python3
"""
ユーザー認証テーブル作成スクリプト

Flask-Migrateの代わりにシンプルなSQLスクリプトでテーブルを作成
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

def create_user_table():
    """
    データベースにユーザーテーブル（users）が存在しない場合に新規作成します。
    
    Returns:
        bool: テーブル作成に成功した場合はTrue、失敗した場合はFalseを返します。既にテーブルが存在する場合もTrueを返します。
    """
    with app.app_context():
        try:
            # テーブルの存在確認
            inspector = db.inspect(db.engine)
            if 'users' in inspector.get_table_names():
                print("ℹ️ ユーザーテーブルは既に存在します")
                return True
            
            # ユーザーテーブルのみを作成
            User.__table__.create(db.engine)
            print("✅ ユーザーテーブルが正常に作成されました")
            return True
            
        except Exception as e:
            print(f"❌ テーブル作成エラー: {e}")
            return False

if __name__ == '__main__':
    if create_user_table():
        print("\n✅ データベースの準備が完了しました")
        print("次のコマンドでテストユーザーを作成できます:")
        print("  python create_test_user.py")
    else:
        print("\n❌ データベースの準備に失敗しました")
        sys.exit(1)