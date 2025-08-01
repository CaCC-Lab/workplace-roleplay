#!/usr/bin/env python3
"""
app.pyからapp_refactored.pyへの移行スクリプト
既存のapp.pyをバックアップし、リファクタリング版を本番用に設定
"""
import os
import shutil
from datetime import datetime
import logging

# ロギングの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def backup_original_app():
    """元のapp.pyをバックアップ"""
    if os.path.exists('app.py'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'app_backup_{timestamp}.py'
        shutil.copy2('app.py', backup_name)
        logging.info(f"✅ app.pyを{backup_name}としてバックアップしました")
        return True
    else:
        logging.error("❌ app.pyが見つかりません")
        return False


def check_dependencies():
    """必要なモジュールが存在するか確認"""
    required_dirs = ['services', 'routes']
    required_files = [
        'services/__init__.py',
        'services/session_service.py',
        'services/llm_service.py',
        'services/chat_service.py',
        'services/scenario_service.py',
        'services/watch_service.py',
        'routes/__init__.py',
        'routes/chat_routes.py',
        'routes/scenario_routes.py',
        'routes/watch_routes.py',
        'routes/model_routes.py',
        'routes/history_routes.py'
    ]
    
    missing = []
    
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            missing.append(f"ディレクトリ: {dir_path}")
    
    for file_path in required_files:
        if not os.path.isfile(file_path):
            missing.append(f"ファイル: {file_path}")
    
    if missing:
        print("❌ 以下のモジュールが不足しています:")
        for item in missing:
            print(f"  - {item}")
        return False
    
    print("✅ すべての必要なモジュールが存在します")
    return True


def migrate_to_refactored():
    """リファクタリング版を本番用に設定"""
    if os.path.exists('app_refactored.py'):
        # app_refactored.pyをapp.pyにコピー
        shutil.copy2('app_refactored.py', 'app.py')
        print("✅ app_refactored.pyをapp.pyとして設定しました")
        return True
    else:
        print("❌ app_refactored.pyが見つかりません")
        return False


def main():
    """移行プロセスのメイン関数"""
    print("=== app.py移行スクリプト ===")
    print()
    
    # 1. 依存関係の確認
    print("1. 依存関係の確認...")
    if not check_dependencies():
        print("\n❌ 移行を中止します。必要なモジュールを作成してください。")
        return
    
    print()
    
    # 2. 元のapp.pyのバックアップ
    print("2. 元のapp.pyのバックアップ...")
    if not backup_original_app():
        print("\n❌ 移行を中止します。")
        return
    
    print()
    
    # 3. リファクタリング版への移行
    print("3. リファクタリング版への移行...")
    if not migrate_to_refactored():
        print("\n❌ 移行を中止します。")
        return
    
    print()
    print("✅ 移行が完了しました！")
    print()
    print("次のステップ:")
    print("1. python app.py でアプリケーションを起動")
    print("2. すべての機能が正常に動作することを確認")
    print("3. 問題がある場合は、バックアップファイルから復元可能")


if __name__ == '__main__':
    main()