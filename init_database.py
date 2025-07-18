#!/usr/bin/env python
"""
データベース初期化スクリプト

使い方:
    python init_database.py         # データベースの作成とマイグレーションの実行
    python init_database.py --reset # データベースのリセット（既存データを削除）
"""
import os
import sys
import argparse
from flask import Flask
from flask_migrate import Migrate, init, migrate as migrate_cmd, upgrade
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db
from database import get_database_uri, create_initial_data


def create_database_if_not_exists():
    """データベースが存在しない場合は作成する"""
    # データベース名を除いたURIを構築
    db_uri = get_database_uri()
    
    # PostgreSQLの場合、データベース名を抽出
    if 'postgresql' in db_uri:
        # データベース名を取得
        db_name = db_uri.split('/')[-1].split('?')[0]
        # postgresデータベースに接続するURIを作成
        base_uri = db_uri.rsplit('/', 1)[0] + '/postgres'
        
        try:
            engine = create_engine(base_uri)
            with engine.connect() as conn:
                # データベースの存在確認
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": db_name}
                )
                if not result.fetchone():
                    # データベースを作成
                    conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                    conn.commit()
                    print(f"✅ データベース '{db_name}' を作成しました")
                else:
                    print(f"ℹ️ データベース '{db_name}' は既に存在します")
        except OperationalError as e:
            print(f"❌ データベースサーバーに接続できません: {e}")
            return False
        except Exception as e:
            print(f"❌ データベース作成中にエラーが発生しました: {e}")
            return False
    
    return True


def init_migrations():
    """マイグレーションディレクトリを初期化"""
    try:
        with app.app_context():
            # migrationsディレクトリが存在しない場合のみ初期化
            if not os.path.exists('migrations'):
                init()
                print("✅ マイグレーションディレクトリを初期化しました")
            else:
                print("ℹ️ マイグレーションディレクトリは既に存在します")
    except Exception as e:
        print(f"❌ マイグレーション初期化エラー: {e}")
        return False
    return True


def create_migration():
    """初期マイグレーションを作成"""
    try:
        with app.app_context():
            # 既存のマイグレーションファイルをチェック
            versions_dir = 'migrations/versions'
            if os.path.exists(versions_dir) and os.listdir(versions_dir):
                print("ℹ️ マイグレーションファイルは既に存在します")
                return True
            
            # 新しいマイグレーションを作成
            migrate_cmd(message='Initial migration')
            print("✅ 初期マイグレーションファイルを作成しました")
    except Exception as e:
        print(f"❌ マイグレーション作成エラー: {e}")
        return False
    return True


def run_migrations():
    """マイグレーションを実行"""
    try:
        with app.app_context():
            upgrade()
            print("✅ データベースマイグレーションを実行しました")
    except Exception as e:
        print(f"❌ マイグレーション実行エラー: {e}")
        return False
    return True


def reset_database():
    """データベースをリセット（開発環境用）"""
    if input("⚠️ 警告: すべてのデータが削除されます。続行しますか？ (yes/no): ").lower() != 'yes':
        print("キャンセルしました")
        return False
    
    try:
        with app.app_context():
            # すべてのテーブルを削除
            db.drop_all()
            print("✅ すべてのテーブルを削除しました")
            
            # テーブルを再作成
            db.create_all()
            print("✅ テーブルを再作成しました")
            
            # 初期データを作成
            create_initial_data(app)
            print("✅ 初期データを作成しました")
    except Exception as e:
        print(f"❌ データベースリセットエラー: {e}")
        return False
    return True


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='データベース初期化スクリプト')
    parser.add_argument('--reset', action='store_true', help='データベースをリセット')
    args = parser.parse_args()
    
    print("🔧 データベース初期化を開始します...")
    
    # データベースの存在確認と作成
    if not create_database_if_not_exists():
        print("❌ データベースの準備に失敗しました")
        return 1
    
    if args.reset:
        # リセットモード
        if not reset_database():
            return 1
    else:
        # 通常モード: マイグレーションの初期化と実行
        if not init_migrations():
            return 1
        
        if not create_migration():
            return 1
        
        if not run_migrations():
            return 1
        
        # 初期データの作成
        try:
            with app.app_context():
                create_initial_data(app)
        except Exception as e:
            print(f"⚠️ 初期データ作成時の警告: {e}")
    
    print("✅ データベース初期化が完了しました！")
    print("\n次のステップ:")
    print("1. docker-compose up -d  # PostgreSQLとRedisを起動")
    print("2. python app.py         # アプリケーションを起動")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())