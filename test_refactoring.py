#!/usr/bin/env python
"""
リファクタリング後のアプリケーションテストスクリプト
"""
import sys
import os

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("1. アプリケーションのインポートテスト...")
    from application import create_app
    print("✅ application.create_app のインポート成功")
    
    print("\n2. アプリケーションインスタンスの作成テスト...")
    app = create_app('development')
    print("✅ アプリケーションインスタンスの作成成功")
    
    print("\n3. 設定の確認...")
    print(f"  - DEBUG: {app.config.get('DEBUG')}")
    print(f"  - SESSION_TYPE: {app.config.get('SESSION_TYPE')}")
    print(f"  - GOOGLE_API_KEY設定: {'設定済み' if app.config.get('GOOGLE_API_KEY') else '未設定'}")
    
    print("\n4. Blueprint登録の確認...")
    blueprints = list(app.blueprints.keys())
    print(f"  登録されたBlueprints: {blueprints}")
    
    print("\n5. ルートの確認...")
    with app.app_context():
        rules = []
        for rule in app.url_map.iter_rules():
            if str(rule).startswith('/api/') or str(rule) in ['/', '/chat', '/scenarios', '/watch']:
                rules.append(str(rule))
        print(f"  主要なルート数: {len(rules)}")
        for rule in sorted(rules)[:10]:
            print(f"    - {rule}")
    
    print("\n✅ すべてのテストが成功しました！")
    print("\nアプリケーションを起動するには以下のコマンドを実行してください:")
    print("  python app.py")
    
except ImportError as e:
    print(f"\n❌ インポートエラー: {e}")
    print("\n必要なモジュールが見つかりません。以下を確認してください:")
    print("1. すべての依存パッケージがインストールされているか")
    print("2. 新しく作成したファイルが正しい場所にあるか")
    
except Exception as e:
    print(f"\n❌ エラーが発生しました: {e}")
    print(f"エラーの型: {type(e).__name__}")
    import traceback
    traceback.print_exc()