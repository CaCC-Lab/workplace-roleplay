#!/usr/bin/env python3
"""
パフォーマンス問題を修正するスクリプト
"""
import os

print("=== パフォーマンス問題の修正 ===\n")

# 1. 不要なデータベース初期化を無効化
print("1. データベース初期化の最適化...")

# app.pyのバックアップ
os.system("cp app.py app_before_fix.py")

# app.pyを読み込み
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# データベース初期化を条件付きに変更
if 'database_available = init_database(app)' in content:
    # 環境変数でデータベース初期化を制御
    new_content = content.replace(
        'database_available = init_database(app)',
        '# データベース初期化を環境変数で制御\nUSE_DATABASE = os.environ.get("USE_DATABASE", "false").lower() == "true"\nif USE_DATABASE:\n    database_available = init_database(app)\nelse:\n    database_available = False\n    print("📁 データベース初期化をスキップ（ファイルシステムモード）")'
    )
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("   ✅ データベース初期化を条件付きに変更")

# 2. .envファイルにデータベース無効化設定を追加
print("\n2. 環境変数の設定...")

env_content = """
# データベース使用設定（パフォーマンス問題対策）
USE_DATABASE=false

# セッション設定（ファイルシステム使用）
SESSION_TYPE=filesystem
"""

# .envファイルが存在する場合は追記、なければ作成
if os.path.exists('.env'):
    with open('.env', 'a', encoding='utf-8') as f:
        f.write(env_content)
else:
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)

print("   ✅ 環境変数を設定")

# 3. シナリオデータのキャッシュ最適化
print("\n3. シナリオデータのキャッシュ最適化...")

# scenarios/__init__.pyを確認
scenarios_init_path = 'scenarios/__init__.py'
if os.path.exists(scenarios_init_path):
    with open(scenarios_init_path, 'r', encoding='utf-8') as f:
        scenarios_content = f.read()
    
    # キャッシュ機能を追加（既に存在しない場合）
    if '@lru_cache' not in scenarios_content:
        # インポートを追加
        new_scenarios_content = 'from functools import lru_cache\n' + scenarios_content
        
        # load_scenarios関数にキャッシュデコレータを追加
        new_scenarios_content = new_scenarios_content.replace(
            'def load_scenarios():',
            '@lru_cache(maxsize=1)\ndef load_scenarios():'
        )
        
        with open(scenarios_init_path, 'w', encoding='utf-8') as f:
            f.write(new_scenarios_content)
        
        print("   ✅ シナリオデータのキャッシュを有効化")
    else:
        print("   ℹ️ シナリオデータのキャッシュは既に有効")

print("\n✅ パフォーマンス修正が完了しました")
print("\n次のコマンドでアプリケーションを起動してください:")
print("python app.py")
print("\n注意: データベース機能は無効化されています。")
print("データベースを使用する場合は、.envファイルで USE_DATABASE=true に設定してください。")