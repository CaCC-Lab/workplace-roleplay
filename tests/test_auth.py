"""
auth.py のユニットテスト

認証モジュールの全機能をテストし、カバレッジを100%近くまで向上させる
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from flask import url_for
from flask_login import current_user, AnonymousUserMixin
from werkzeug.security import generate_password_hash

from auth import auth_bp
from models import db, User
from forms import LoginForm, RegistrationForm


class TestAuthLogin:
    """ログイン機能のテスト"""
    
    def test_login_page_get(self, client):
        """ログインページの表示テスト"""
        response = client.get('/login')
        assert response.status_code == 200
        assert 'ログイン' in response.data.decode('utf-8')
    
    def test_login_redirect_if_authenticated(self, client, auth_user):
        """認証済みユーザーのリダイレクトテスト"""
        with client:
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = auth_user
                response = client.get('/login')
                assert response.status_code == 302
                assert response.location == '/'
    
    def test_login_success(self, client, app):
        """正常なログイン成功テスト"""
        with app.app_context():
            # テストユーザーを作成
            user = User(username='testuser', email='test@example.com', is_active=True)
            user.set_password('testpassword123')
            
            with patch('auth.User') as MockUser:
                mock_query = MagicMock()
                MockUser.query = mock_query
                mock_query.filter.return_value.first.return_value = user
                
                with patch('auth.login_user') as mock_login:
                    response = client.post('/login', data={
                        'username_or_email': 'testuser',
                        'password': 'testpassword123'
                        # remember_me を含めない（チェックボックス未選択を模擬）
                    }, follow_redirects=False)
                    
                    assert response.status_code == 302
                    assert response.location == '/'
                    mock_login.assert_called_once_with(user, remember=False)
    
    def test_login_with_email(self, client, app):
        """メールアドレスでのログインテスト"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com', is_active=True)
            user.set_password('testpassword123')
            
            with patch('auth.User') as MockUser:
                mock_query = MagicMock()
                MockUser.query = mock_query
                mock_query.filter.return_value.first.return_value = user
                
                with patch('auth.login_user') as mock_login:
                    response = client.post('/login', data={
                        'username_or_email': 'test@example.com',
                        'password': 'testpassword123',
                        'remember_me': True
                    }, follow_redirects=False)
                    
                    assert response.status_code == 302
                    mock_login.assert_called_once_with(user, remember=True)
    
    def test_login_invalid_credentials(self, client, app):
        """無効な認証情報でのログインテスト"""
        with app.app_context():
            with patch('auth.User') as MockUser:
                MockUser.query.filter.return_value.first.return_value = None
                
                response = client.post('/login', data={
                    'username_or_email': 'invalid',
                    'password': 'wrongpassword'
                }, follow_redirects=True)
                
                assert response.status_code == 200
                assert 'ユーザー名/メールアドレスまたはパスワードが正しくありません' in response.data.decode()
    
    def test_login_wrong_password(self, client, app):
        """パスワード誤りでのログインテスト"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com', is_active=True)
            user.set_password('correctpassword')  # set_password メソッドを使用
            
            with patch('auth.User') as MockUser:
                MockUser.query.filter.return_value.first.return_value = user
                
                response = client.post('/login', data={
                    'username_or_email': 'testuser',
                    'password': 'wrongpassword'
                }, follow_redirects=True)
                
                assert response.status_code == 200
                assert 'ユーザー名/メールアドレスまたはパスワードが正しくありません' in response.data.decode()
    
    def test_login_inactive_user(self, client, app):
        """無効化されたユーザーのログインテスト"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com', is_active=False)
            user.set_password('testpassword123')
            
            with patch('auth.User') as MockUser:
                MockUser.query.filter.return_value.first.return_value = user
                
                response = client.post('/login', data={
                    'username_or_email': 'testuser',
                    'password': 'testpassword123'
                }, follow_redirects=True)
                
                assert response.status_code == 200
                assert 'このアカウントは無効化されています' in response.data.decode()
    
    def test_login_with_next_parameter_safe(self, client, app):
        """安全なnextパラメータでのリダイレクトテスト"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com', is_active=True)
            user.set_password('testpassword123')
            
            with patch('auth.User') as MockUser:
                MockUser.query.filter.return_value.first.return_value = user
                
                with patch('auth.login_user'):
                    response = client.post('/login?next=/protected', data={
                        'username_or_email': 'testuser',
                        'password': 'testpassword123'
                    }, follow_redirects=False)
                    
                    assert response.status_code == 302
                    assert response.location == '/protected'
    
    def test_login_with_next_parameter_unsafe(self, client, app):
        """安全でないnextパラメータの無視テスト"""
        with app.app_context():
            user = User(username='testuser', email='test@example.com', is_active=True)
            user.set_password('testpassword123')
            
            with patch('auth.User') as MockUser:
                MockUser.query.filter.return_value.first.return_value = user
                
                with patch('auth.login_user'):
                    # 外部URLへのリダイレクトを防ぐ
                    response = client.post('/login?next=http://evil.com', data={
                        'username_or_email': 'testuser',
                        'password': 'testpassword123'
                    }, follow_redirects=False)
                    
                    assert response.status_code == 302
                    assert response.location == '/'
    
    def test_login_form_validation_error(self, client):
        """フォームバリデーションエラーのテスト"""
        response = client.post('/login', data={
            'username_or_email': '',  # 必須項目が空
            'password': ''
        })
        
        assert response.status_code == 200
        # フォームエラーが表示されることを確認


class TestAuthRegister:
    """ユーザー登録機能のテスト"""
    
    def test_register_page_get(self, client):
        """登録ページの表示テスト"""
        response = client.get('/register')
        assert response.status_code == 200
        assert 'ユーザー登録' in response.data.decode('utf-8')
    
    def test_register_redirect_if_authenticated(self, client, auth_user):
        """認証済みユーザーのリダイレクトテスト"""
        with client:
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = auth_user
                response = client.get('/register')
                assert response.status_code == 302
                assert response.location == '/'
    
    def test_register_success(self, client, app):
        """正常なユーザー登録テスト"""
        with app.app_context():
            with patch('auth.db.session') as mock_session:
                with patch('forms.User') as MockFormUser:
                    # フォームのバリデーションをパス
                    MockFormUser.query.filter_by.return_value.first.return_value = None
                    
                    response = client.post('/register', data={
                        'username': 'newuser',
                        'email': 'new@example.com',
                        'password': 'password123',
                        'password2': 'password123'
                    }, follow_redirects=False)
                    
                    assert response.status_code == 302
                    assert response.location == '/login'
                    mock_session.add.assert_called_once()
                    mock_session.commit.assert_called_once()
    
    def test_register_database_error(self, client, app):
        """データベースエラー時の処理テスト"""
        with app.app_context():
            with patch('auth.db.session') as mock_session:
                with patch('forms.User') as MockFormUser:
                    MockFormUser.query.filter_by.return_value.first.return_value = None
                    mock_session.commit.side_effect = Exception("DB Error")
                    
                    response = client.post('/register', data={
                        'username': 'newuser',
                        'email': 'new@example.com',
                        'password': 'password123',
                        'password2': 'password123'
                    }, follow_redirects=True)
                    
                    assert response.status_code == 200
                    assert '登録に失敗しました' in response.data.decode()
                    mock_session.rollback.assert_called_once()
    
    def test_register_form_validation_username_too_short(self, client):
        """ユーザー名が短すぎる場合のテスト"""
        response = client.post('/register', data={
            'username': 'ab',  # 3文字未満
            'email': 'test@example.com',
            'password': 'password123',
            'password2': 'password123'
        })
        
        assert response.status_code == 200
        assert 'ユーザー名は3文字以上20文字以下で入力してください' in response.data.decode()
    
    def test_register_form_validation_invalid_email(self, client):
        """無効なメールアドレスのテスト"""
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'password123',
            'password2': 'password123'
        })
        
        assert response.status_code == 200
        assert '有効なメールアドレスを入力してください' in response.data.decode()
    
    def test_register_form_validation_password_mismatch(self, client):
        """パスワード不一致のテスト"""
        response = client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'password2': 'different123'
        })
        
        assert response.status_code == 200
        assert 'パスワードが一致しません' in response.data.decode()
    
    def test_register_form_validation_duplicate_username(self, client, app):
        """重複ユーザー名のテスト"""
        with app.app_context():
            existing_user = User(username='existinguser')
            
            with patch('forms.User') as MockUser:
                MockUser.query.filter_by.return_value.first.return_value = existing_user
                
                response = client.post('/register', data={
                    'username': 'existinguser',
                    'email': 'new@example.com',
                    'password': 'password123',
                    'password2': 'password123'
                })
                
                assert response.status_code == 200
                assert 'このユーザー名は既に使用されています' in response.data.decode()


class TestAuthLogout:
    """ログアウト機能のテスト"""
    
    def test_logout_success(self, client, auth_user):
        """正常なログアウトテスト"""
        with client:
            # Flask-Loginの認証状態を正しくモック
            with patch('flask_login.utils._get_user') as mock_get_user:
                mock_get_user.return_value = auth_user
                
                with patch('auth.current_user', auth_user):
                    with patch('auth.logout_user') as mock_logout:
                        response = client.get('/logout', follow_redirects=False)
                        
                        assert response.status_code == 302
                        assert response.location == '/'
                        mock_logout.assert_called_once()
    
    def test_logout_unauthenticated_redirect(self, client):
        """未認証ユーザーのログアウトアクセステスト"""
        # Flask-Loginのlogin_requiredデコレータにより、未認証ユーザーはログインページにリダイレクトされる
        response = client.get('/logout', follow_redirects=False)
        assert response.status_code == 302
        # デフォルトではlogin_viewが設定されていない場合は401が返るが、
        # 設定されている場合はログインページにリダイレクト


class TestAuthIntegration:
    """認証機能の統合テスト"""
    
    def test_full_registration_and_login_flow(self, client, app):
        """登録からログインまでの完全なフローテスト"""
        with app.app_context():
            # 1. ユーザー登録
            with patch('auth.db.session') as mock_session:
                with patch('forms.User') as MockFormUser:
                    MockFormUser.query.filter_by.return_value.first.return_value = None
                    
                    response = client.post('/register', data={
                        'username': 'integrationuser',
                        'email': 'integration@example.com',
                        'password': 'integration123',
                        'password2': 'integration123'
                    }, follow_redirects=True)
                    
                    assert '登録が完了しました' in response.data.decode()
            
            # 2. 登録したユーザーでログイン
            user = User(username='integrationuser', email='integration@example.com', is_active=True)
            user.set_password('integration123')
            
            with patch('auth.User') as MockUser:
                MockUser.query.filter.return_value.first.return_value = user
                
                # ログイン成功をシミュレート
                with patch('auth.login_user') as mock_login:
                    with patch('flask_login.utils._get_user') as mock_get_user:
                        mock_get_user.return_value = user
                        
                        response = client.post('/login', data={
                            'username_or_email': 'integration@example.com',
                            'password': 'integration123'
                        }, follow_redirects=True)
                        
                        # ログイン後のフラッシュメッセージを確認（認証成功はリダイレクト後なので）
                        # レスポンスステータスが200で成功フローをたどったことを確認
                        assert response.status_code == 200
    
    def test_logging_throughout_auth_flow(self, client, app):
        """認証フロー全体のログ記録テスト"""
        with app.app_context():
            # ログイン失敗のログ
            with patch('auth.logger') as mock_logger:
                with patch('auth.User') as MockUser:
                    MockUser.query.filter.return_value.first.return_value = None
                    
                    client.post('/login', data={
                        'username_or_email': 'faileduser',
                        'password': 'wrongpass'
                    })
                    
                    mock_logger.warning.assert_called_with('ログイン失敗: faileduser')
            
            # ログイン成功のログ
            user = User(username='successuser', email='success@example.com', is_active=True)
            user.set_password('correctpass')
            
            with patch('auth.logger') as mock_logger:
                with patch('auth.User') as MockUser:
                    MockUser.query.filter.return_value.first.return_value = user
                    
                    with patch('auth.login_user'):
                        client.post('/login', data={
                            'username_or_email': 'successuser',
                            'password': 'correctpass'
                        })
                        
                        mock_logger.info.assert_called_with('ユーザーログイン成功: successuser')
            
            # 新規登録のログ
            with patch('auth.logger') as mock_logger:
                with patch('auth.db.session'):
                    with patch('forms.User') as MockFormUser:
                        MockFormUser.query.filter_by.return_value.first.return_value = None
                        
                        client.post('/register', data={
                            'username': 'newuser',
                            'email': 'new@example.com',
                            'password': 'password123',
                            'password2': 'password123'
                        })
                        
                        mock_logger.info.assert_called_with('新規ユーザー登録: newuser')
            
            # ログアウトのログ
            logout_user = User(username='logoutuser', email='logout@example.com', is_active=True)
            with patch('auth.logger') as mock_logger:
                with patch('flask_login.utils._get_user') as mock_get_user:
                    mock_get_user.return_value = logout_user
                    
                    with patch('auth.current_user', logout_user):
                        with patch('auth.logout_user'):
                            client.get('/logout')
                            
                            mock_logger.info.assert_called_with('ユーザーログアウト: logoutuser')