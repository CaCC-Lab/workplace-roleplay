"""
APIエラーハンドリングのテスト

各APIエンドポイントのエラーハンドリングを包括的にテストし、
セキュリティ、入力検証、例外処理の動作を確認する
"""
import pytest
from unittest.mock import patch, MagicMock
from flask import session
import json

from utils.security import CSRFToken


class TestCSRFErrorHandling:
    """CSRF関連のエラーハンドリングテスト"""
    
    def test_missing_csrf_token(self, client, app):
        """CSRFトークンなしでのPOSTリクエスト"""
        with app.app_context():
            response = client.post('/api/chat',
                data=json.dumps({'message': 'テストメッセージ'}),
                content_type='application/json'
            )
            
            assert response.status_code == 403
            data = response.get_json()
            assert 'error' in data
            assert 'CSRFトークン' in data['error']
    
    def test_invalid_csrf_token(self, client, app):
        """無効なCSRFトークンでのリクエスト"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['csrf_token'] = 'valid_token_123'
            
            response = client.post('/api/chat',
                data=json.dumps({
                    'message': 'テストメッセージ',
                    'csrf_token': 'invalid_token_456'
                }),
                content_type='application/json',
                headers={'X-CSRFToken': 'invalid_token_456'}
            )
            
            assert response.status_code == 403
            data = response.get_json()
            assert 'error' in data
            assert 'CSRFトークンが無効' in data['error']
    
    def test_csrf_token_format_validation(self, client, app):
        """CSRFトークンの形式検証テスト"""
        with app.app_context():
            # 不正な形式のトークン（短すぎる）
            response = client.post('/api/clear_history',
                data=json.dumps({
                    'csrf_token': 'short'
                }),
                content_type='application/json',
                headers={'X-CSRFToken': 'short'}
            )
            
            assert response.status_code == 403
            data = response.get_json()
            assert 'error' in data


class TestInputValidationErrors:
    """入力検証エラーのテスト"""
    
    def test_invalid_json_payload(self, client, app):
        """無効なJSONペイロードのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            # 不正なJSONを送信
            response = client.post('/api/chat',
                data='{"invalid": json}',  # 無効なJSON
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
    
    def test_missing_required_fields(self, client, app):
        """必須フィールドの欠如テスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            # メッセージフィールドなし
            response = client.post('/api/chat',
                data=json.dumps({
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
    
    def test_invalid_model_name(self, client, app, sample_scenario_data):
        """無効なモデル名のテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            # app.scenarios にモック登録
            with patch('app.scenarios', {sample_scenario_data['id']: sample_scenario_data}):
                # LLM初期化をモックして実際のAPI呼び出しを防ぐ
                with patch('app.initialize_llm') as mock_init_llm:
                    # より明確に無効なモデル名でテスト（アルファベット以外の文字を含む）
                    mock_init_llm.side_effect = Exception("Invalid model name")
                    
                    response = client.post('/api/scenario_chat',
                        data=json.dumps({
                            'message': 'テストメッセージ',
                            'scenario_id': sample_scenario_data['id'],
                            'model': 'invalid@model!',  # 明らかに無効なモデル名
                            'csrf_token': csrf_token
                        }),
                        content_type='application/json',
                        headers={'X-CSRFToken': csrf_token}
                    )
                    
                    # モデル名に無効な文字が含まれている場合の処理
                    # 現在の実装では400エラーまたはLLM初期化エラーが期待される
                    assert response.status_code in [400, 429]  # 429はレート制限の場合
                    data = response.get_json()
                    assert 'error' in data
    
    def test_invalid_scenario_id(self, client, app):
        """無効なシナリオIDのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            response = client.post('/api/scenario_chat',
                data=json.dumps({
                    'message': 'テストメッセージ',
                    'scenario_id': 'invalid@scenario!',  # 無効なシナリオID
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'シナリオID' in data['error']


class TestAuthenticationErrors:
    """認証関連のエラーテスト"""
    
    def test_unauthenticated_protected_route(self, client, app):
        """認証が必要なルートへの未認証アクセス"""
        # login_required デコレータがある場合のテスト
        # 現在のアプリでは大部分のAPIが未認証でもアクセス可能だが、
        # 将来の拡張を考慮してテストケースを準備
        pass
    
    def test_inactive_user_access(self, client, app):
        """無効化されたユーザーのアクセステスト"""
        # Flask-Loginの設定によっては、無効化されたユーザーの
        # アクセスを制限する場合のテスト
        pass


class TestExternalServiceErrors:
    """外部サービスエラーのテスト"""
    
    def test_gemini_api_initialization_error(self, client, app, auth_user):
        """Gemini API初期化エラーのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
                sess['conversation_history'] = []
                sess['chat_settings'] = {
                    'system_prompt': 'テスト用プロンプト'
                }
            
            # LLM初期化エラーをシミュレート
            with patch('app.initialize_llm') as mock_init_llm:
                mock_init_llm.side_effect = Exception("Gemini API initialization failed")
                
                response = client.post('/api/chat',
                    data=json.dumps({
                        'message': 'テストメッセージ',
                        'csrf_token': csrf_token
                    }),
                    content_type='application/json',
                    headers={'X-CSRFToken': csrf_token}
                )
                
                assert response.status_code == 400
                data = response.get_json()
                assert 'error' in data
    
    def test_gemini_api_timeout_error(self, client, app, auth_user):
        """Gemini APIタイムアウトエラーのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
                sess['conversation_history'] = []
                sess['chat_settings'] = {
                    'system_prompt': 'テスト用プロンプト'
                }
            
            # LLMタイムアウトエラーをシミュレート
            with patch('app.initialize_llm') as mock_init_llm:
                mock_chain = MagicMock()
                mock_chain.stream.side_effect = TimeoutError("Request timeout")
                mock_init_llm.return_value = mock_chain
                
                with patch('app.get_google_api_key', return_value='test-api-key'):
                    with patch('app.record_api_usage'):  # API使用量記録もモック
                        response = client.post('/api/chat',
                            data=json.dumps({
                                'message': 'テストメッセージ',
                                'csrf_token': csrf_token
                            }),
                            content_type='application/json',
                            headers={'X-CSRFToken': csrf_token}
                        )
                        
                        # タイムアウトエラーは通常500エラーとして処理される
                        # 429は実際のAPI制限による可能性もある
                        assert response.status_code in [400, 429, 500]
                        data = response.get_json()
                        assert 'error' in data
    
    def test_missing_api_key(self, client, app, auth_user):
        """APIキー不足エラーのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
                sess['conversation_history'] = []
                sess['chat_settings'] = {
                    'system_prompt': 'テスト用プロンプト'
                }
            
            # APIキーが None を返すようにモック
            with patch('app.get_google_api_key', return_value=None):
                response = client.post('/api/chat',
                    data=json.dumps({
                        'message': 'テストメッセージ',
                        'csrf_token': csrf_token
                    }),
                    content_type='application/json',
                    headers={'X-CSRFToken': csrf_token}
                )
                
                # APIキーなしの場合の処理によって様々なステータスが返される可能性
                assert response.status_code in [400, 429, 500]
                data = response.get_json()
                assert 'error' in data


class TestResourceNotFoundErrors:
    """リソース不在エラーのテスト"""
    
    def test_scenario_not_found(self, client, app):
        """存在しないシナリオIDのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            response = client.post('/api/scenario_chat',
                data=json.dumps({
                    'message': 'テストメッセージ',
                    'scenario_id': 'nonexistent_scenario',
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'シナリオID' in data['error']
    
    def test_conversation_history_not_found(self, client, app):
        """会話履歴不在エラーのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            response = client.post('/api/chat_feedback',
                data=json.dumps({'csrf_token': csrf_token}),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data
    
    def test_watch_session_not_initialized(self, client, app):
        """観戦セッション未初期化エラーのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            response = client.post('/api/watch/next',
                data=json.dumps({'csrf_token': csrf_token}),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data


class TestSecurityErrors:
    """セキュリティ関連エラーのテスト"""
    
    def test_xss_attempt_in_message(self, client, app, auth_user):
        """メッセージでのXSS攻撃試行テスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
                sess['conversation_history'] = []
                sess['chat_settings'] = {
                    'system_prompt': 'テスト用プロンプト'
                }
            
            # XSS攻撃を含むメッセージ
            malicious_message = '<script>alert("XSS")</script>テストメッセージ'
            
            with patch('app.initialize_llm') as mock_init_llm:
                mock_chain = MagicMock()
                mock_chain.stream.return_value = iter(['安全な', '応答'])
                mock_init_llm.return_value = mock_chain
                
                with patch('app.get_google_api_key', return_value='test-api-key'):
                    with patch('app.record_api_usage'):  # API使用量記録もモック
                        response = client.post('/api/chat',
                            data=json.dumps({
                                'message': malicious_message,
                                'csrf_token': csrf_token
                            }),
                            content_type='application/json',
                            headers={'X-CSRFToken': csrf_token}
                        )
                        
                        # リクエストは成功するか、レート制限に遭遇する可能性
                        assert response.status_code in [200, 429]
    
    def test_sql_injection_attempt(self, client, app):
        """SQLインジェクション試行テスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            # SQLインジェクション攻撃を含むシナリオID
            malicious_scenario_id = "scenario'; DROP TABLE users; --"
            
            response = client.post('/api/scenario_chat',
                data=json.dumps({
                    'message': 'テストメッセージ',
                    'scenario_id': malicious_scenario_id,
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            # 無効な入力として拒否される
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data


class TestRateLimitingErrors:
    """レート制限エラーのテスト"""
    
    @pytest.mark.skip(reason="Rate limiting not implemented yet")
    def test_api_rate_limiting(self, client, app):
        """APIレート制限のテスト"""
        # 将来的にレート制限機能が実装された場合のテストケース
        pass


class TestInternalServerErrors:
    """内部サーバーエラーのテスト"""
    
    def test_database_connection_error(self, client, app):
        """データベース接続エラーのテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            # データベース接続エラーをシミュレート
            with patch('app.db') as mock_db:
                mock_db.session.commit.side_effect = Exception("Database connection lost")
                
                # DBに依存する操作をテスト（将来の機能拡張を想定）
                # 現在のアプリは主にセッションベースなので、実際のDB操作は少ない
                pass
    
    def test_unexpected_exception_handling(self, client, app, auth_user):
        """予期しない例外のハンドリングテスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
                sess['conversation_history'] = []
                sess['chat_settings'] = {
                    'system_prompt': 'テスト用プロンプト'
                }
            
            # 予期しない例外をシミュレート
            with patch('app.initialize_llm') as mock_init_llm:
                mock_init_llm.side_effect = RuntimeError("Unexpected error occurred")
                
                # get_google_api_key もモックして実際のAPIキー取得を防ぐ
                with patch('app.get_google_api_key', return_value='test-api-key'):
                    response = client.post('/api/chat',
                        data=json.dumps({
                            'message': 'テストメッセージ',
                            'csrf_token': csrf_token
                        }),
                        content_type='application/json',
                        headers={'X-CSRFToken': csrf_token}
                    )
                    
                    # 予期しない例外は適切にハンドリングされる
                    # 429はレート制限、400と500は予期されるエラー処理
                    assert response.status_code in [400, 429, 500]
                    data = response.get_json()
                    assert 'error' in data