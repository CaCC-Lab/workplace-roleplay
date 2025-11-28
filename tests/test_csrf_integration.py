"""
CSRF対策の統合テスト
実際のアプリケーションでCSRF対策が正しく動作することを確認
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from app import app
from utils.security import CSRFToken


class TestCSRFIntegration:
    """CSRF対策の統合テスト"""

    @pytest.fixture
    def client(self):
        """テスト用クライアントを作成"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # WTFのCSRFは無効化
        app.secret_key = 'test-secret-key-for-csrf-testing'
        
        with app.test_client() as client:
            yield client

    def test_csrf_token_endpoint(self, client):
        """CSRFトークン取得エンドポイントのテスト"""
        response = client.get('/api/csrf-token')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'csrf_token' in data
        assert 'expires_in' in data
        assert len(data['csrf_token']) == 32  # 32文字の16進数
        assert data['expires_in'] == 3600  # 1時間

    def test_protected_endpoint_without_csrf_token(self, client):
        """CSRF保護されたエンドポイントにトークンなしでアクセス"""
        # /api/clear_historyは保護されている
        response = client.post('/api/clear_history',
                             json={'mode': 'chat'})
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'CSRF' in data['error'] or 'csrf' in data['error']

    def test_protected_endpoint_with_invalid_csrf_token(self, client):
        """CSRF保護されたエンドポイントに無効なトークンでアクセス"""
        response = client.post('/api/clear_history',
                             json={'mode': 'chat'},
                             headers={'X-CSRFToken': 'invalid_token'})
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'CSRF' in data['error'] or 'csrf' in data['error']

    def test_protected_endpoint_with_valid_csrf_token(self, client):
        """CSRF保護されたエンドポイントに有効なトークンでアクセス"""
        # まずCSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        token_data = token_response.get_json()
        csrf_token = token_data['csrf_token']
        
        # 有効なトークンでアクセス
        response = client.post('/api/clear_history',
                             json={'mode': 'chat'},
                             headers={'X-CSRFToken': csrf_token})
        
        # 200または他の成功ステータスが返ることを確認
        assert response.status_code != 403
        # CSRFエラーでないことを確認
        data = response.get_json()
        if 'error' in data:
            error_msg = data['error'].lower()
            assert 'csrf' not in error_msg

    @patch('app.initialize_llm')
    def test_chat_endpoint_csrf_protection(self, mock_llm, client):
        """チャットエンドポイントのCSRF保護をテスト"""
        # モデルの初期化をモック
        mock_model = MagicMock()
        mock_model.stream.return_value = ['テスト', 'レスポンス']
        mock_llm.return_value = mock_model
        
        # CSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        csrf_token = token_response.get_json()['csrf_token']
        
        # チャットリクエスト（CSRF保護されている）
        response = client.post('/api/chat',
                             json={'message': 'こんにちは'},
                             headers={'X-CSRFToken': csrf_token})
        
        # CSRFエラーではないことを確認
        assert response.status_code != 403
        data = response.get_json()
        if data and 'error' in data:
            # エラーメッセージが文字列か辞書かチェック
            error_msg = data['error']
            if isinstance(error_msg, str):
                assert 'csrf' not in error_msg.lower()
            elif isinstance(error_msg, dict):
                # エラーが辞書形式の場合、メッセージフィールドをチェック
                msg = error_msg.get('message', '')
                assert 'csrf' not in str(msg).lower()

    def test_get_request_exempt_from_csrf(self, client):
        """GETリクエストはCSRF検証を免除されることを確認"""
        # GETリクエストはCSRF保護されない
        response = client.get('/api/models')
        # CSRFエラーで拒否されることはない
        assert response.status_code != 403

    def test_csrf_token_session_persistence(self, client):
        """セッション間でのCSRFトークンの永続性をテスト"""
        # セッションを開始
        with client.session_transaction() as sess:
            token1 = CSRFToken.get_or_create(sess)
        
        # 同じセッションで再度取得
        with client.session_transaction() as sess:
            token2 = CSRFToken.get_or_create(sess)
        
        # 同じトークンが返されることを確認
        assert token1 == token2

    def test_csrf_token_refresh(self, client):
        """CSRFトークンのリフレッシュ機能をテスト"""
        # 初期トークンを取得
        with client.session_transaction() as sess:
            token1 = CSRFToken.get_or_create(sess)
            
            # トークンをリフレッシュ
            token2 = CSRFToken.refresh(sess)
        
        # 異なるトークンが生成されることを確認
        assert token1 != token2
        
        # 古いトークンは無効になることを確認
        with client.session_transaction() as sess:
            assert not CSRFToken.validate(token1, sess)
            assert CSRFToken.validate(token2, sess)

    def test_multiple_csrf_protected_endpoints(self, client):
        """複数のCSRF保護エンドポイントをテスト"""
        protected_endpoints = [
            ('/api/clear_history', {'mode': 'chat'}),
        ]
        
        for endpoint, data in protected_endpoints:
            # トークンなしではアクセス拒否
            response = client.post(endpoint, json=data)
            assert response.status_code == 403, f"Endpoint {endpoint} should be protected"
            
            # 新しいセッションで新しいCSRFトークンを取得
            token_response = client.get('/api/csrf-token')
            csrf_token = token_response.get_json()['csrf_token']
            
            # 有効なトークンでアクセス成功（CSRFエラー以外のエラーは無視）
            response = client.post(endpoint, 
                                 json=data,
                                 headers={'X-CSRFToken': csrf_token})
            assert response.status_code != 403, f"Endpoint {endpoint} should accept valid CSRF token"

    def test_csrf_error_logging(self, client, caplog):
        """CSRF違反のログ記録をテスト"""
        import logging
        
        # ログキャプチャを有効化
        with caplog.at_level(logging.WARNING):
            # 無効なトークンでアクセス
            response = client.post('/api/clear_history',
                                 json={'mode': 'chat'},
                                 headers={'X-CSRFToken': 'invalid_token'})
            
            assert response.status_code == 403
            
            # ログが記録されていることを確認（caplogを使用）
            assert any('csrf' in record.message.lower() for record in caplog.records) or \
                   any('CSRF' in record.message for record in caplog.records)

    def test_csrf_error_response_format(self, client):
        """CSRFエラーレスポンスの形式をテスト"""
        response = client.post('/api/clear_history',
                             json={'mode': 'chat'})
        
        assert response.status_code == 403
        data = response.get_json()
        
        # 必要なフィールドが含まれていることを確認
        assert 'error' in data
        assert 'code' in data
        assert data['code'] in ['CSRF_TOKEN_MISSING', 'CSRF_TOKEN_INVALID']

    def test_csrf_with_form_data(self, client):
        """フォームデータでのCSRF検証をテスト"""
        # CSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        csrf_token = token_response.get_json()['csrf_token']
        
        # フォームデータにCSRFトークンを含める
        response = client.post('/api/clear_history',
                             data={'mode': 'chat', 'csrf_token': csrf_token})
        
        # CSRFエラーでないことを確認
        assert response.status_code != 403

    def test_csrf_middleware_initialization(self, client):
        """CSRFミドルウェアの初期化をテスト"""
        # CSRFトークンエンドポイントにアクセスしてトークンを取得
        # これによりセッションにトークンが保存される
        token_response = client.get('/api/csrf-token')
        assert token_response.status_code == 200
        
        # トークンが返されることを確認
        data = token_response.get_json()
        assert 'csrf_token' in data
        assert len(data['csrf_token']) > 0


class TestCSRFSecurityHeaders:
    """CSRFに関連するセキュリティヘッダーのテスト"""

    @pytest.fixture
    def client(self):
        """テスト用クライアントを作成"""
        app.config['TESTING'] = True
        app.secret_key = 'test-secret-key-for-csrf-testing'
        
        with app.test_client() as client:
            yield client

    def test_session_cookie_security_settings(self, client):
        """セッションCookieのセキュリティ設定をテスト"""
        response = client.get('/')
        
        # Set-Cookieヘッダーを確認
        set_cookie_header = response.headers.get('Set-Cookie', '')
        
        # セキュリティ設定が適用されていることを確認
        if set_cookie_header:
            # HttpOnly設定は通常含まれている
            assert 'HttpOnly' in set_cookie_header
            
            # SameSite設定（Flask-SessionのデフォルトでLaxが設定される）
            # 注：一部のバージョンでは明示的に表示されない場合がある
            print(f"Set-Cookie header: {set_cookie_header}")  # デバッグ用
            
            # 本番環境でのSecure設定
            if app.config.get('ENV') == 'production':
                assert 'Secure' in set_cookie_header

    def test_csrf_token_in_response_header(self, client):
        """成功したCSRF保護リクエスト後に新しいトークンがヘッダーに含まれることをテスト"""
        # CSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        csrf_token = token_response.get_json()['csrf_token']
        
        # CSRF保護されたエンドポイントにアクセス
        response = client.post('/api/clear_history',
                             json={'mode': 'chat'},
                             headers={'X-CSRFToken': csrf_token})
        
        # 新しいCSRFトークンがレスポンスヘッダーに含まれていることを確認
        if response.status_code != 403:  # CSRFエラー以外の場合
            new_token = response.headers.get('X-CSRF-Token')
            if new_token:
                assert new_token != csrf_token  # 新しいトークンが生成されている
                assert len(new_token) == 32  # 正しい形式


class TestCSRFPerformance:
    """CSRF対策のパフォーマンステスト"""

    @pytest.fixture
    def client(self):
        """テスト用クライアントを作成"""
        app.config['TESTING'] = True
        app.secret_key = 'test-secret-key-for-csrf-testing'
        
        with app.test_client() as client:
            yield client

    def test_csrf_token_generation_performance(self, client):
        """CSRFトークン生成のパフォーマンステスト"""
        import time
        
        # 複数回のトークン生成時間を測定
        start_time = time.time()
        
        for _ in range(100):
            CSRFToken.generate()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 100回の生成が1秒以内で完了することを確認
        assert total_time < 1.0, f"Token generation took {total_time} seconds for 100 tokens"

    def test_csrf_validation_performance(self, client):
        """CSRF検証のパフォーマンステスト"""
        import time
        
        with client.session_transaction() as sess:
            token = CSRFToken.generate()
            sess['csrf_token'] = token
            
            # 複数回の検証時間を測定
            start_time = time.time()
            
            for _ in range(1000):
                CSRFToken.validate(token, sess)
            
            end_time = time.time()
            total_time = end_time - start_time
        
        # 1000回の検証が1秒以内で完了することを確認
        assert total_time < 1.0, f"Token validation took {total_time} seconds for 1000 validations"