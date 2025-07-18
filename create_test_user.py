#!/usr/bin/env python3
"""
テストユーザー作成スクリプト

開発環境でテスト用のユーザーアカウントを作成
"""
import os
import sys
from flask import Flask
from database import init_database
from models import db, User
from flask_bcrypt import Bcrypt

# アプリケーションのセットアップ
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
bcrypt = Bcrypt(app)

# データベースの初期化
if not init_database(app):
    print("❌ データベース接続に失敗しました")
    sys.exit(1)

def create_test_users():
    """テストユーザーを作成"""
    test_users = [
        {
            'username': 'testuser1',
            'email': 'test1@example.com',
            'password': 'testpass123'
        },
        {
            'username': 'testuser2',
            'email': 'test2@example.com',
            'password': 'testpass456'
        }
    ]
    
    created_users = []
    
    for user_data in test_users:
        # 既存ユーザーのチェック
        existing_user = User.query.filter(
            (User.username == user_data['username']) | 
            (User.email == user_data['email'])
        ).first()
        
        if existing_user:
            print(f"⚠️ ユーザー '{user_data['username']}' は既に存在します")
            continue
        
        # 新規ユーザーの作成
        user = User(
            username=user_data['username'],
            email=user_data['email']
        )
        user.set_password(user_data['password'])
        
        db.session.add(user)
        created_users.append(user_data['username'])
        print(f"✅ ユーザー '{user_data['username']}' を作成しました")
    
    if created_users:
        db.session.commit()
        print(f"\n✅ {len(created_users)} 人のテストユーザーを作成しました")
    else:
        print("\n❌ 新しいテストユーザーは作成されませんでした")
    
    # 作成されたユーザー情報を表示
    print("\n📋 テストユーザー情報:")
    for user_data in test_users:
        print(f"  - ユーザー名: {user_data['username']}")
        print(f"    メール: {user_data['email']}")
        print(f"    パスワード: {user_data['password']}")
        print()

if __name__ == '__main__':
    with app.app_context():
        try:
            create_test_users()
        except Exception as e:
            print(f"❌ エラーが発生しました: {e}")
            db.session.rollback()
            sys.exit(1)