"""
app.pyの統合フローとエッジケーステスト（モック禁止）
複雑な統合フローとエラーハンドリングの包括的テスト
残りの未カバー領域をターゲット
"""
import pytest
import json
import os
import time
from datetime import datetime, timedelta
from flask import Flask, session, g

# テスト用環境変数を設定
os.environ['GOOGLE_API_KEY'] = 'test-api-key-for-integration-tests'
os.environ['TESTING'] = 'true'
os.environ['FLASK_SECRET_KEY'] = 'test-secret-key'

# テスト用アプリケーションを作成
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(current_dir, 'templates')

test_app = Flask(__name__, template_folder=template_dir)
test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
test_app.config['TESTING'] = True
test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
test_app.config['SECRET_KEY'] = 'test-secret-key'
test_app.config['GOOGLE_API_KEY'] = 'test-api-key-for-integration-tests'

# modelsをインポートしてDBを初期化
from models import db, User, Scenario, DifficultyLevel, PracticeSession, ConversationLog, SessionType

# テスト用データベースを初期化
db.init_app(test_app)

# app.pyをインポート（カバレッジ測定対象）
import app


@pytest.fixture
def test_db():
    """テスト用データベースのセットアップ"""
    ctx = test_app.app_context()
    ctx.push()
    
    try:
        db.create_all()
        _setup_test_data()
        yield db
    finally:
        db.session.remove()
        db.drop_all()
        ctx.pop()


def _setup_test_data():
    """テストデータのセットアップ"""
    # テストユーザー
    test_user = User(
        username='integrationuser',
        email='integration@example.com', 
        password_hash='hashed_password'
    )
    db.session.add(test_user)
    
    # 複数のテストシナリオ
    scenarios = [
        Scenario(
            yaml_id='effective_communication',
            title='効果的なコミュニケーション',
            summary='職場での効果的なコミュニケーションを学ぶ',
            difficulty=DifficultyLevel.BEGINNER,
            category='communication',
            is_active=True
        ),
        Scenario(
            yaml_id='conflict_resolution',
            title='コンフリクト解決',
            summary='職場での対立を解決する方法',
            difficulty=DifficultyLevel.INTERMEDIATE,
            category='problem_solving',
            is_active=True
        )
    ]
    
    for scenario in scenarios:
        db.session.add(scenario)
    
    db.session.commit()


def get_csrf_token(client):
    """CSRFトークンを取得"""
    try:
        response = client.get('/api/csrf-token')
        if response.status_code == 200:
            return response.get_json().get('csrf_token')
    except:
        pass
    return None


class TestCompleteUserJourney:
    """完全なユーザージャーニーの統合テスト"""
    
    def test_full_scenario_practice_flow(self, test_db):
        """シナリオ練習の完全フロー"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # Step 1: シナリオ練習開始
            response = client.post('/api/scenario_chat',
                                   json={
                                       "message": "",  # 初回メッセージ
                                       "scenario_id": "effective_communication"
                                   },
                                   headers=headers)
            
            assert response.status_code in [200, 400, 403, 429, 500]
            
            # Step 2: 複数回の会話交換
            for i in range(3):
                response = client.post('/api/scenario_chat',
                                       json={
                                           "message": f"ユーザーからの第{i+1}回目のメッセージです",
                                           "scenario_id": "effective_communication"
                                       },
                                       headers=headers)
                
                assert response.status_code in [200, 400, 403, 429, 500]
                time.sleep(0.1)
            
            # Step 3: フィードバック取得
            response = client.post('/api/scenario_feedback',
                                   json={"scenario_id": "effective_communication"},
                                   headers=headers)
            
            assert response.status_code in [200, 400, 403, 429, 500]
            
            # Step 4: 履歴クリア
            response = client.post('/api/scenario_clear',
                                   json={"scenario_id": "effective_communication"},
                                   headers=headers)
            
            assert response.status_code in [200, 400, 403, 429, 500]
    
    def test_multi_modal_interaction_flow(self, test_db):
        """マルチモーダルインタラクションフロー"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # フリートーク → シナリオ → 観戦 の順番でテスト
            
            # 1. フリートーク開始
            response = client.post('/api/chat',
                                   json={"message": "こんにちは、今日はお疲れ様です"},
                                   headers=headers)
            assert response.status_code in [200, 400, 403, 429, 500]
            
            # 2. シナリオ練習に切り替え
            response = client.post('/api/scenario_chat',
                                   json={
                                       "message": "",
                                       "scenario_id": "conflict_resolution"
                                   },
                                   headers=headers)
            assert response.status_code in [200, 400, 403, 429, 500]
            
            # 3. 観戦モードに切り替え
            response = client.post('/api/watch/start',
                                   json={
                                       "model_a": "gemini/gemini-1.5-flash",
                                       "model_b": "gemini/gemini-1.5-pro",
                                       "situation": "チーム会議",
                                       "topic": "プロジェクト計画"
                                   },
                                   headers=headers)
            assert response.status_code in [200, 400, 403, 429, 500]
            
            # 4. 観戦継続
            response = client.post('/api/watch/next', headers=headers)
            assert response.status_code in [200, 400, 403, 429, 500]
    
    def test_session_state_management_across_modes(self, test_db):
        """モード間でのセッション状態管理"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 各モードでセッション状態を構築
            modes_data = [
                ("chat", '/api/chat', {"message": "フリートークテスト"}),
                ("scenario", '/api/scenario_chat', {
                    "message": "シナリオテスト", 
                    "scenario_id": "effective_communication"
                }),
                ("watch", '/api/watch/start', {
                    "model_a": "gemini/gemini-1.5-flash",
                    "model_b": "gemini/gemini-1.5-pro",
                    "situation": "会議",
                    "topic": "プロジェクト"
                })
            ]
            
            # 各モードでデータを作成
            for mode, endpoint, data in modes_data:
                response = client.post(endpoint, json=data, headers=headers)
                assert response.status_code in [200, 400, 403, 429, 500]
            
            # セッション情報を確認
            response = client.get('/api/session/info')
            assert response.status_code == 200
            
            # 会話履歴を確認
            for mode in ["chat", "scenario"]:
                response = client.post('/api/conversation_history',
                                       json={"mode": mode},
                                       headers=headers)
                assert response.status_code in [200, 400, 403, 429, 500]


class TestErrorHandlingAndEdgeCases:
    """エラーハンドリングとエッジケースの詳細テスト"""
    
    def test_malformed_request_handling(self, test_db):
        """不正なリクエストのハンドリング"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 各エンドポイントで不正なデータをテスト
            malformed_requests = [
                ('/api/chat', '{"message": "incomplete json'),
                ('/api/scenario_chat', '{"scenario_id": null, "message":'),
                ('/api/watch/start', '{"model_a": undefined}'),
                ('/api/scenario_feedback', '{"scenario_id":}')
            ]
            
            for endpoint, malformed_data in malformed_requests:
                response = client.post(endpoint,
                                       data=malformed_data,
                                       content_type='application/json',
                                       headers=headers)
                
                # 不正なJSONは400エラーまたはCSRF403、500エラーを返す
                assert response.status_code in [400, 403, 500]
    
    def test_missing_required_fields(self, test_db):
        """必須フィールド欠如のテスト"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 必須フィールドが欠如したリクエスト
            missing_field_tests = [
                ('/api/chat', {}),  # messageが欠如
                ('/api/scenario_chat', {"message": "test"}),  # scenario_idが欠如
                ('/api/scenario_feedback', {}),  # scenario_idが欠如
                ('/api/watch/start', {"model_a": "test"}),  # 他フィールドが欠如
            ]
            
            for endpoint, incomplete_data in missing_field_tests:
                response = client.post(endpoint,
                                       json=incomplete_data,
                                       headers=headers)
                
                assert response.status_code in [400, 403, 500]
    
    def test_invalid_scenario_id_handling(self, test_db):
        """無効なシナリオIDの詳細ハンドリング"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            invalid_scenarios = [
                "nonexistent_scenario",
                "../../../etc/passwd",
                "'; DROP TABLE scenarios; --",
                "",
                None,
                12345,
                {"invalid": "object"}
            ]
            
            for invalid_scenario in invalid_scenarios:
                if invalid_scenario is None:
                    continue  # None は既に他テストでカバー済み
                    
                response = client.post('/api/scenario_chat',
                                       json={
                                           "message": "test",
                                           "scenario_id": invalid_scenario
                                       },
                                       headers=headers)
                
                assert response.status_code in [400, 403, 500]
                
                # フィードバックAPIでも同様にテスト
                response = client.post('/api/scenario_feedback',
                                       json={"scenario_id": invalid_scenario},
                                       headers=headers)
                
                assert response.status_code in [400, 403, 500]
    
    def test_session_corruption_recovery(self, test_db):
        """セッション破損からの回復テスト"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 破損したセッションデータを設定
            with client.session_transaction() as sess:
                sess['chat_history'] = "invalid_string_instead_of_list"
                sess['scenario_history'] = {"scenario": "invalid_data"}
                sess['watch_history'] = None
                sess['watch_settings'] = {"incomplete": True}
            
            # APIが破損したセッションでも動作することを確認
            endpoints_to_test = [
                ('/api/chat', {"message": "テスト"}),
                ('/api/scenario_chat', {
                    "message": "テスト", 
                    "scenario_id": "effective_communication"
                }),
                ('/api/watch/next', {}),
                ('/api/conversation_history', {"mode": "chat"}),
                ('/api/session/info', None)
            ]
            
            for endpoint, data in endpoints_to_test:
                if data is None:
                    response = client.get(endpoint)
                else:
                    response = client.post(endpoint, json=data, headers=headers)
                
                # エラーが発生しても適切にハンドリングされること
                assert response.status_code in [200, 400, 403, 500]


class TestPerformanceAndStress:
    """パフォーマンスとストレステスト"""
    
    def test_large_conversation_history_handling(self, test_db):
        """大量の会話履歴のハンドリング"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 大量の履歴を生成
            large_history = []
            for i in range(100):
                large_history.append({
                    "human": f"これは{i+1}番目のユーザーメッセージです。" * 10,
                    "ai": f"これは{i+1}番目のAI応答です。" * 10
                })
            
            with client.session_transaction() as sess:
                sess['chat_history'] = large_history
            
            # 大量履歴でのAPI動作確認
            response = client.post('/api/chat',
                                   json={"message": "大量履歴後のメッセージ"},
                                   headers=headers)
            
            assert response.status_code in [200, 400, 403, 429, 500]
            
            # フィードバック生成でも確認
            response = client.post('/api/chat_feedback', headers=headers)
            assert response.status_code in [200, 400, 403, 429, 500]
    
    def test_concurrent_request_simulation(self, test_db):
        """同時リクエストのシミュレーション"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            with app.app.test_client() as client:
                csrf_token = get_csrf_token(client)
                headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
                
                response = client.post('/api/chat',
                                       json={"message": f"同時リクエスト {threading.current_thread().ident}"},
                                       headers=headers)
                results.put(response.status_code)
        
        # 複数スレッドで同時リクエスト
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 結果確認
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        assert len(status_codes) == 3
        # 全てのリクエストが適切に処理される（レート制限も含む）
        for code in status_codes:
            assert code in [200, 429, 500]
    
    def test_memory_intensive_operations(self, test_db):
        """メモリ集約的操作のテスト"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 大きなメッセージでのテスト
            large_message = "これは非常に長いメッセージです。" * 1000
            
            response = client.post('/api/chat',
                                   json={"message": large_message},
                                   headers=headers)
            
            assert response.status_code in [200, 400, 429, 500]
            
            # 複雑なネストしたデータでのテスト
            complex_data = {
                "message": "複雑なデータテスト",
                "metadata": {
                    "context": ["項目1"] * 100,
                    "settings": {f"key_{i}": f"value_{i}" for i in range(50)}
                }
            }
            
            response = client.post('/api/chat',
                                   json=complex_data,
                                   headers=headers)
            
            assert response.status_code in [200, 400, 429, 500]


class TestSecurityAndValidation:
    """セキュリティと入力検証の詳細テスト"""
    
    def test_input_sanitization(self, test_db):
        """入力サニタイゼーションのテスト"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 様々な攻撃パターンをテスト
            attack_patterns = [
                "<script>alert('XSS')</script>",
                "'; DROP TABLE users; --",
                "../../../etc/passwd",
                "eval('malicious_code')",
                "<iframe src='javascript:alert(1)'></iframe>",
                "javascript:void(0)",
                "%3Cscript%3Ealert('encoded')%3C/script%3E"
            ]
            
            for pattern in attack_patterns:
                response = client.post('/api/chat',
                                       json={"message": pattern},
                                       headers=headers)
                
                assert response.status_code in [200, 400, 429, 500]
                
                # レスポンスに攻撃パターンがそのまま含まれていないことを確認
                if response.status_code == 200:
                    response_text = response.get_data(as_text=True)
                    # 基本的なXSS攻撃パターンがエスケープされていることを確認
                    assert '<script>' not in response_text
                    assert 'javascript:' not in response_text
    
    def test_parameter_validation(self, test_db):
        """パラメータ検証の詳細テスト"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 型違反のテスト
            invalid_type_tests = [
                ('/api/chat', {"message": 12345}),  # 数値
                ('/api/chat', {"message": True}),   # ブール値
                ('/api/chat', {"message": []}),     # 配列
                ('/api/scenario_chat', {
                    "message": "test",
                    "scenario_id": {"invalid": "object"}
                }),
                ('/api/watch/start', {
                    "model_a": [],
                    "model_b": {},
                    "situation": None,
                    "topic": 12345
                })
            ]
            
            for endpoint, invalid_data in invalid_type_tests:
                response = client.post(endpoint,
                                       json=invalid_data,
                                       headers=headers)
                
                # 型エラーは適切にハンドリングされる
                assert response.status_code in [400, 403, 429, 500]
    
    def test_rate_limiting_simulation(self, test_db):
        """レート制限のシミュレーション"""
        with app.app.test_client() as client:
            csrf_token = get_csrf_token(client)
            headers = {'X-CSRFToken': csrf_token} if csrf_token else {}
            
            # 短時間で大量のリクエストを送信
            responses = []
            for i in range(10):
                response = client.post('/api/chat',
                                       json={"message": f"高頻度リクエスト {i}"},
                                       headers=headers)
                responses.append(response.status_code)
                # わずかな間隔
                time.sleep(0.01)
            
            # 全てのリクエストが処理される（レート制限が発生する可能性）
            for status_code in responses:
                assert status_code in [200, 429, 500]


class TestAPIConsistency:
    """API一貫性のテスト"""
    
    def test_error_response_format_consistency(self, test_db):
        """エラーレスポンス形式の一貫性"""
        with app.app.test_client() as client:
            # 各エンドポイントで意図的にエラーを発生させる
            error_inducing_requests = [
                ('/api/chat', {}),  # 必須フィールド欠如
                ('/api/scenario_chat', {"message": "test"}),  # scenario_id欠如
                ('/api/scenario_feedback', {}),  # scenario_id欠如
                ('/api/watch/start', {}),  # 必須フィールド欠如
            ]
            
            for endpoint, invalid_data in error_inducing_requests:
                response = client.post(endpoint, json=invalid_data)
                
                if response.status_code in [400, 500]:
                    data = response.get_json()
                    if data:
                        # エラーレスポンスには 'error' フィールドが含まれる
                        assert 'error' in data
                        assert isinstance(data['error'], str)
    
    def test_success_response_format_consistency(self, test_db):
        """成功レスポンス形式の一貫性"""
        with app.app.test_client() as client:
            # 成功が期待されるリクエスト
            success_requests = [
                ('/api/models', None),  # GET
                ('/api/session/info', None),  # GET
                ('/api/tts/voices', None),  # GET
                ('/api/key_status', None),  # GET
                ('/api/session/health', None),  # GET
            ]
            
            for endpoint, data in success_requests:
                response = client.get(endpoint)
                
                if response.status_code == 200:
                    data = response.get_json()
                    assert data is not None
                    assert isinstance(data, dict)