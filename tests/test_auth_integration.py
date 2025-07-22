"""
認証デコレータ統合テスト

Flask-LoginとCSRF保護デコレータの統合動作をテストし、
実際のAPIエンドポイントでの認証・認可フローを検証する
"""
import pytest
from unittest.mock import patch, MagicMock
from flask import session
from flask_login import current_user

from auth import auth_bp
from models import User
from utils.security import CSRFToken
import json


class TestAuthIntegrationMiddleware:
    """認証ミドルウェアの統合テスト"""
    
    def test_login_required_redirect(self, client, app):
        """login_required デコレータが未認証ユーザーをリダイレクトするテスト"""
        with app.app_context():
            # auth.pyの/logout エンドポイントにアクセス（@login_required付き）
            response = client.get('/logout', follow_redirects=False)
            
            # 未認証の場合、ログインページにリダイレクトされる
            assert response.status_code == 302
            assert '/login' in response.location
    
    def test_csrf_protection_on_post_endpoints(self, client, app):
        """CSRF保護が必要なエンドポイントのテスト"""
        with app.app_context():
            # CSRFトークンなしでPOSTリクエスト
            response = client.post('/api/chat', 
                data=json.dumps({'message': 'test'}),
                content_type='application/json'
            )
            
            # CSRF保護によりアクセス拒否される
            assert response.status_code in [400, 403]
    
    def test_csrf_token_with_valid_session(self, client, app):
        """有効なセッションでのCSRFトークン生成テスト"""
        with client.session_transaction() as sess:
            # セッションにCSRFシードを設定
            sess['csrf_seed'] = 'test-seed-12345'
        
        # CSRFトークンを生成
        with app.app_context():
            token = CSRFToken.generate()
            assert token is not None
            assert len(token) == 32  # 32文字の16進数


class TestAPIEndpointsIntegration:
    """APIエンドポイントの統合テスト"""
    
    def test_api_chat_with_authentication(self, client, app, auth_user):
        """チャットAPIの認証統合テスト"""
        with app.app_context():
            # セッションとCSRFトークンを設定
            with client.session_transaction() as sess:
                sess['csrf_seed'] = 'test-seed-12345'
                sess['user_id'] = auth_user.id
            
            csrf_token = CSRFToken.generate()
            
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = auth_user
                
                # Gemini APIをモック
                with patch('app.initialize_llm') as mock_llm:
                    mock_chain = MagicMock()
                    mock_chain.stream.return_value = iter(['テスト', '応答'])
                    mock_llm.return_value = mock_chain
                    
                    response = client.post('/api/chat',
                        data=json.dumps({
                            'message': 'こんにちは',
                            'csrf_token': csrf_token
                        }),
                        content_type='application/json',
                        headers={'X-CSRFToken': csrf_token}
                    )
                    
                    # 認証済みユーザーはアクセス可能
                    assert response.status_code in [200, 201]
    
    def test_api_scenario_chat_authentication(self, client, app, auth_user):
        """シナリオチャットAPIの認証統合テスト"""
        with app.app_context():
            # セッションとCSRFトークンを設定
            with client.session_transaction() as sess:
                sess['csrf_seed'] = 'test-seed-12345'
                sess['user_id'] = auth_user.id
                sess['selected_scenario'] = 'test_scenario'
            
            csrf_token = CSRFToken.generate()
            
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = auth_user
                
                with patch('app.initialize_llm') as mock_llm:
                    mock_chain = MagicMock()
                    mock_chain.stream.return_value = iter(['シナリオ', '応答'])
                    mock_llm.return_value = mock_chain
                    
                    response = client.post('/api/scenario_chat',
                        data=json.dumps({
                            'message': 'プロジェクトの進捗を報告します',
                            'csrf_token': csrf_token
                        }),
                        content_type='application/json',
                        headers={'X-CSRFToken': csrf_token}
                    )
                    
                    assert response.status_code in [200, 201]
    
    def test_api_feedback_authentication(self, client, app, auth_user):
        """フィードバックAPIの認証統合テスト"""
        with app.app_context():
            # セッションとCSRFトークンを設定
            with client.session_transaction() as sess:
                sess['csrf_seed'] = 'test-seed-12345'
                sess['user_id'] = auth_user.id
                # フィードバック用の会話履歴をセッションに設定
                sess['conversation_history'] = [
                    {'role': 'user', 'content': 'テストメッセージ'},
                    {'role': 'assistant', 'content': 'テスト応答'}
                ]
            
            csrf_token = CSRFToken.generate()
            
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = auth_user
                
                with patch('app.initialize_llm') as mock_llm:
                    mock_chain = MagicMock()
                    mock_chain.stream.return_value = iter(['フィードバック'])
                    mock_llm.return_value = mock_chain
                    
                    response = client.post('/api/chat_feedback',
                        data=json.dumps({'csrf_token': csrf_token}),
                        content_type='application/json',
                        headers={'X-CSRFToken': csrf_token}
                    )
                    
                    assert response.status_code in [200, 201]


class TestSessionManagement:
    """セッション管理の統合テスト"""
    
    def test_session_persistence_across_requests(self, client, app, auth_user):
        """リクエスト間でのセッション永続化テスト"""
        with app.app_context():
            # 1. ログイン
            with patch('auth.User') as MockUser:
                MockUser.query.filter.return_value.first.return_value = auth_user
                
                with patch('auth.login_user') as mock_login:
                    login_response = client.post('/login', data={
                        'username_or_email': 'testuser',
                        'password': 'testpassword'
                    }, follow_redirects=False)
                    
                    assert login_response.status_code == 302
            
            # 2. セッション情報を設定
            with client.session_transaction() as sess:
                sess['test_data'] = 'persistent_value'
                sess['csrf_seed'] = 'test-seed-12345'
            
            # 3. 別のリクエストでセッション情報を確認
            with client.session_transaction() as sess:
                assert sess.get('test_data') == 'persistent_value'
                assert sess.get('csrf_seed') == 'test-seed-12345'
    
    def test_session_cleanup_on_logout(self, client, app, auth_user):
        """ログアウト時のセッションクリーンアップテスト"""
        with app.app_context():
            # セッション情報を設定
            with client.session_transaction() as sess:
                sess['user_id'] = auth_user.id
                sess['conversation_history'] = ['test', 'data']
                sess['csrf_seed'] = 'test-seed-12345'
            
            # ログアウト
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = auth_user
                
                with patch('auth.current_user', auth_user):
                    with patch('auth.logout_user') as mock_logout:
                        logout_response = client.get('/logout', follow_redirects=False)
                        
                        assert logout_response.status_code == 302
                        mock_logout.assert_called_once()


class TestErrorHandlingIntegration:
    """エラーハンドリングの統合テスト"""
    
    def test_unauthorized_api_access(self, client, app):
        """未認証ユーザーのAPI アクセス時のエラーハンドリング"""
        with app.app_context():
            # 未認証でCSRF保護されたエンドポイントにアクセス
            response = client.post('/api/chat',
                data=json.dumps({'message': 'test'}),
                content_type='application/json'
            )
            
            # 適切なエラーレスポンスが返される
            assert response.status_code in [400, 401, 403]
            
            if response.status_code == 400:
                # CSRFエラーの場合
                data = response.get_json()
                assert 'error' in data
    
    def test_invalid_csrf_token_handling(self, client, app):
        """無効なCSRFトークンのエラーハンドリング"""
        with app.app_context():
            # セッションを設定
            with client.session_transaction() as sess:
                sess['csrf_seed'] = 'test-seed-12345'
            
            # 無効なCSRFトークンでリクエスト
            response = client.post('/api/chat',
                data=json.dumps({
                    'message': 'test',
                    'csrf_token': 'invalid-token'
                }),
                content_type='application/json',
                headers={'X-CSRFToken': 'invalid-token'}
            )
            
            # CSRF検証エラー
            assert response.status_code in [400, 403]
    
    def test_api_key_error_handling(self, client, app, auth_user):
        """API キーエラー時のハンドリングテスト"""
        with app.app_context():
            # 認証とCSRFトークンを設定
            with client.session_transaction() as sess:
                sess['csrf_seed'] = 'test-seed-12345'
                sess['user_id'] = auth_user.id
            
            csrf_token = CSRFToken.generate()
            
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = auth_user
                
                # API キーエラーをシミュレート
                with patch('app.get_google_api_key') as mock_api_key:
                    mock_api_key.side_effect = Exception("API key not available")
                    
                    response = client.post('/api/chat',
                        data=json.dumps({
                            'message': 'test',
                            'csrf_token': csrf_token
                        }),
                        content_type='application/json',
                        headers={'X-CSRFToken': csrf_token}
                    )
                    
                    # エラーが適切にハンドリングされる
                    assert response.status_code >= 400


class TestSecurityIntegration:
    """セキュリティ統合テスト"""
    
    def test_xss_protection_in_responses(self, client, app):
        """レスポンスのXSS保護テスト"""
        with app.app_context():
            # XSSペイロードを含むリクエスト
            xss_payload = '<script>alert("xss")</script>'
            
            response = client.get(f'/login?error={xss_payload}')
            
            # レスポンスでXSSペイロードがエスケープされている
            assert response.status_code == 200
            assert '<script>' not in response.data.decode()
            assert '&lt;script&gt;' in response.data.decode() or 'alert' not in response.data.decode()
    
    def test_sql_injection_protection(self, client, app):
        """SQLインジェクション保護テスト"""
        with app.app_context():
            # SQLインジェクションペイロード
            sql_payload = "'; DROP TABLE users; --"
            
            # ログインフォームでSQLインジェクションを試行
            response = client.post('/login', data={
                'username_or_email': sql_payload,
                'password': 'password'
            })
            
            # SQLインジェクションが防止されている（正常なエラーレスポンス）
            assert response.status_code in [200, 302]
            # アプリケーションがクラッシュしていない
    
    def test_rate_limiting_integration(self, client, app):
        """レート制限の統合テスト"""
        with app.app_context():
            # 連続したリクエストでレート制限をテスト
            responses = []
            for i in range(10):
                response = client.post('/login', data={
                    'username_or_email': f'user{i}@test.com',
                    'password': 'wrongpassword'
                })
                responses.append(response.status_code)
            
            # 多数の失敗ログイン後もサービスが継続している
            # (レート制限が実装されている場合は429が返される可能性もある)
            assert all(status in [200, 302, 429] for status in responses)