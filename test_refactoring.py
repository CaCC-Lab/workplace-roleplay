#!/usr/bin/env python3
"""
リファクタリング後のモジュールのテスト
各サービスとルートが正しくインポートできるか確認
"""
import sys


def test_imports():
    """モジュールのインポートテスト"""
    print("=== モジュールインポートテスト ===\n")
    
    modules_to_test = [
        # サービスモジュール
        ('services.session_service', 'SessionService'),
        ('services.llm_service', 'LLMService'),
        ('services.chat_service', 'ChatService'),
        ('services.scenario_service', 'ScenarioService'),
        ('services.watch_service', 'WatchService'),
        
        # ルートモジュール
        ('routes.chat_routes', 'chat_bp'),
        ('routes.scenario_routes', 'scenario_bp'),
        ('routes.watch_routes', 'watch_bp'),
        ('routes.model_routes', 'model_bp'),
        ('routes.history_routes', 'history_bp'),
    ]
    
    success_count = 0
    error_count = 0
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            if hasattr(module, class_name):
                print(f"✅ {module_name}.{class_name} - OK")
                success_count += 1
            else:
                print(f"❌ {module_name}.{class_name} - クラス/オブジェクトが見つかりません")
                error_count += 1
        except ImportError as e:
            print(f"❌ {module_name} - インポートエラー: {e}")
            error_count += 1
        except Exception as e:
            print(f"❌ {module_name} - エラー: {e}")
            error_count += 1
    
    print(f"\n結果: 成功 {success_count}, 失敗 {error_count}")
    return error_count == 0


def test_service_methods():
    """サービスメソッドの基本的なテスト"""
    print("\n=== サービスメソッドテスト ===\n")
    
    try:
        from services.llm_service import LLMService
        
        # 利用可能なモデルの取得テスト
        models = LLMService.get_available_models()
        if isinstance(models, dict):
            print(f"✅ LLMService.get_available_models() - OK ({len(models)} models)")
        else:
            print("❌ LLMService.get_available_models() - 予期しない戻り値")
            
    except Exception as e:
        print(f"❌ LLMServiceのテスト中にエラー: {e}")
    
    try:
        from services.session_service import SessionService
        
        # SessionServiceのメソッド存在確認
        methods = [
            'initialize_session_history',
            'add_to_session_history',
            'get_session_history',
            'clear_session_history',
            'get_session_data',
            'set_session_data'
        ]
        
        for method in methods:
            if hasattr(SessionService, method):
                print(f"✅ SessionService.{method} - 存在確認OK")
            else:
                print(f"❌ SessionService.{method} - メソッドが見つかりません")
                
    except Exception as e:
        print(f"❌ SessionServiceのテスト中にエラー: {e}")


def test_route_blueprints():
    """ルートBlueprintの基本的なテスト"""
    print("\n=== ルートBlueprintテスト ===\n")
    
    blueprints = [
        ('routes.chat_routes', 'chat_bp', ['/api/chat', '/api/chat_feedback', '/api/clear_chat']),
        ('routes.scenario_routes', 'scenario_bp', ['/api/scenarios', '/api/scenario_chat', '/api/scenario_feedback']),
        ('routes.watch_routes', 'watch_bp', ['/api/watch/start', '/api/watch/next', '/api/watch/summary']),
        ('routes.model_routes', 'model_bp', ['/api/models', '/api/select_model']),
        ('routes.history_routes', 'history_bp', ['/api/learning_history', '/api/chat_history']),
    ]
    
    for module_name, bp_name, expected_routes in blueprints:
        try:
            module = __import__(module_name, fromlist=[bp_name])
            bp = getattr(module, bp_name)
            
            # Blueprintの基本情報
            print(f"✅ {bp_name} - Blueprint名: {bp.name}")
            
            # 登録されているルートの数を確認（簡易的）
            # 注：実際のルート数の確認は、Flaskアプリケーションコンテキスト内で行う必要があります
            
        except Exception as e:
            print(f"❌ {module_name}.{bp_name} - エラー: {e}")


def main():
    """メインテスト関数"""
    print("リファクタリング後のモジュールテストを開始します...\n")
    
    # インポートテスト
    import_success = test_imports()
    
    if not import_success:
        print("\n❌ インポートテストに失敗しました。")
        print("モジュール構成を確認してください。")
        sys.exit(1)
    
    # サービスメソッドテスト
    test_service_methods()
    
    # ルートBlueprintテスト
    test_route_blueprints()
    
    print("\n✅ テストが完了しました！")
    print("\n次のステップ:")
    print("1. python migrate_app.py で移行スクリプトを実行")
    print("2. python app.py でアプリケーションを起動")
    print("3. ブラウザで各機能をテスト")


if __name__ == '__main__':
    main()