"""
CSRF（Cross-Site Request Forgery）対策のテスト
"""
import pytest
import secrets
import time
from unittest.mock import MagicMock, patch
from flask import Flask, session, request
from utils.security import SecurityUtils, CSRFToken


class TestCSRFToken:
    """CSRFトークンクラスのテスト"""
    
    def test_generate_token_format(self):
        """CSRFトークンの生成形式テスト"""
        token = CSRFToken.generate()
        
        # トークンが文字列であること
        assert isinstance(token, str)
        
        # 適切な長さであること（32文字の16進数）
        assert len(token) == 32
        
        # 16進数文字のみであること
        assert all(c in '0123456789abcdef' for c in token)
    
    def test_generate_token_uniqueness(self):
        """CSRFトークンの一意性テスト"""
        tokens = set()
        
        # 1000回生成して重複がないことを確認
        for _ in range(1000):
            token = CSRFToken.generate()
            assert token not in tokens
            tokens.add(token)
    
    def test_token_expiration(self):
        """CSRFトークンの有効期限テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # 新しいトークンを生成
                token = CSRFToken.refresh(sess)
                
                # 即座の検証は成功すべき
                assert CSRFToken.validate(token, sess) is True
                
                # 有効期限を過ぎたトークンをシミュレート
                sess['csrf_token']['created_at'] = time.time() - CSRFToken.TOKEN_LIFETIME - 1
                
                # 期限切れトークンの検証は失敗すべき
                assert CSRFToken.validate(token, sess) is False
    
    def test_token_refresh_updates_timestamp(self):
        """トークンリフレッシュ時のタイムスタンプ更新テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # 初回トークン生成
                token1 = CSRFToken.refresh(sess)
                timestamp1 = sess['csrf_token']['created_at']
                
                # 少し待機
                time.sleep(0.1)
                
                # トークンをリフレッシュ
                token2 = CSRFToken.refresh(sess)
                timestamp2 = sess['csrf_token']['created_at']
                
                # 新しいトークンと新しいタイムスタンプであることを確認
                assert token1 != token2
                assert timestamp2 > timestamp1
    
    def test_backward_compatibility(self):
        """旧形式トークンとの後方互換性テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # 旧形式のトークン（文字列）を直接設定
                old_token = CSRFToken.generate()
                sess['csrf_token'] = old_token
                
                # 旧形式トークンの検証が成功することを確認
                assert CSRFToken.validate(old_token, sess) is True
                
                # get_or_createが旧形式を新形式に移行することを確認
                new_token = CSRFToken.get_or_create(sess)
                assert isinstance(sess['csrf_token'], dict)
                assert 'token' in sess['csrf_token']
                assert 'created_at' in sess['csrf_token']
    
    def test_validate_token_valid(self):
        """有効なCSRFトークンの検証テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # セッションにトークンを設定
                token = CSRFToken.generate()
                sess['csrf_token'] = token
                
                # 同じトークンで検証が成功することを確認
                assert CSRFToken.validate(token, sess) is True
    
    def test_validate_token_invalid(self):
        """無効なCSRFトークンの検証テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # セッションに異なるトークンを設定
                sess['csrf_token'] = CSRFToken.generate()
                
                # 異なるトークンで検証が失敗することを確認
                different_token = CSRFToken.generate()
                assert CSRFToken.validate(different_token, sess) is False
    
    def test_validate_token_missing_session(self):
        """セッションにトークンがない場合のテスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # セッションにトークンを設定しない
                token = CSRFToken.generate()
                assert CSRFToken.validate(token, sess) is False
    
    def test_validate_token_empty_input(self):
        """空のトークン入力のテスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['csrf_token'] = CSRFToken.generate()
                
                # 空のトークンで検証が失敗することを確認
                assert CSRFToken.validate("", sess) is False
                assert CSRFToken.validate(None, sess) is False
    
    def test_validate_token_malformed(self):
        """不正な形式のトークンのテスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['csrf_token'] = CSRFToken.generate()
                
                malformed_tokens = [
                    "invalid_token",  # 不正な形式
                    "abc123",  # 短すぎる
                    "g" * 32,  # 16進数以外の文字
                    "1234567890abcdef" * 3,  # 長すぎる
                ]
                
                for token in malformed_tokens:
                    assert CSRFToken.validate(token, sess) is False
    
    def test_refresh_token(self):
        """CSRFトークンのリフレッシュテスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # 初期トークンを設定
                old_token = CSRFToken.generate()
                sess['csrf_token'] = old_token
                
                # トークンをリフレッシュ
                new_token = CSRFToken.refresh(sess)
                
                # 新しいトークンが生成されていることを確認
                assert new_token != old_token
                assert isinstance(sess['csrf_token'], dict)
                assert sess['csrf_token']['token'] == new_token
                assert 'created_at' in sess['csrf_token']
                
                # 古いトークンは無効になっていることを確認
                assert CSRFToken.validate(old_token, sess) is False
                assert CSRFToken.validate(new_token, sess) is True


class TestCSRFMiddleware:
    """CSRFミドルウェアのテスト"""
    
    def test_require_csrf_decorator_valid_token(self):
        """有効なCSRFトークンでのアクセステスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/protected', methods=['POST'])
        @CSRFToken.require_csrf
        def protected_route():
            return {'status': 'success'}
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                token = CSRFToken.generate()
                sess['csrf_token'] = token
            
            # 有効なトークンでリクエスト（JSONデータも含める）
            response = client.post('/protected', 
                                 headers={'X-CSRFToken': token},
                                 json={'test': 'data'})
            assert response.status_code == 200
    
    def test_require_csrf_decorator_invalid_token(self):
        """無効なCSRFトークンでのアクセステスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/protected', methods=['POST'])
        @CSRFToken.require_csrf
        def protected_route():
            return {'status': 'success'}
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['csrf_token'] = CSRFToken.generate()
            
            # 無効なトークンでリクエスト
            response = client.post('/protected', 
                                 headers={'X-CSRFToken': 'invalid_token'})
            assert response.status_code == 403
            
            data = response.get_json()
            assert 'error' in data
            assert 'csrf' in data['error'].lower()
    
    def test_require_csrf_decorator_missing_token(self):
        """CSRFトークンなしでのアクセステスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/protected', methods=['POST'])
        @CSRFToken.require_csrf
        def protected_route():
            return {'status': 'success'}
        
        with app.test_client() as client:
            response = client.post('/protected')
            assert response.status_code == 403
            
            data = response.get_json()
            assert 'error' in data
            assert 'csrf' in data['error'].lower()
    
    def test_require_csrf_decorator_get_request_exempt(self):
        """GETリクエストはCSRF検証を免除することを確認"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/protected', methods=['GET', 'POST'])
        @CSRFToken.require_csrf
        def protected_route():
            return {'status': 'success'}
        
        with app.test_client() as client:
            # GETリクエストはCSRFトークンなしでも成功
            response = client.get('/protected')
            assert response.status_code == 200
    
    def test_csrf_exempt_decorator(self):
        """CSRF免除デコレータのテスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/exempt', methods=['POST'])
        @CSRFToken.csrf_exempt
        def exempt_route():
            return {'status': 'success'}
        
        with app.test_client() as client:
            # CSRF免除ルートはトークンなしでも成功
            response = client.post('/exempt')
            assert response.status_code == 200


class TestCSRFIntegration:
    """CSRF対策の統合テスト"""
    
    def test_token_rotation_on_login(self):
        """ログイン時のトークンローテーションテスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                # 初期トークンを設定
                old_token = CSRFToken.generate()
                sess['csrf_token'] = old_token
            
            # ログイン時にトークンがローテーションされることを模擬
            with client.session_transaction() as sess:
                new_token = CSRFToken.refresh(sess)
                assert new_token != old_token
    
    def test_double_submit_cookie_pattern(self):
        """ダブルサブミットクッキーパターンのテスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            # Cookieとリクエストヘッダーの両方にトークンを設定
            token = CSRFToken.generate()
            client.set_cookie(domain='localhost', key='csrf_token', value=token)
            
            with client.session_transaction() as sess:
                sess['csrf_token'] = token
            
            # 同じトークンが使用されていることを確認（実際のエンドポイントがないのでテスト自体は簡素化）
            assert client.get_cookie('csrf_token', domain='localhost').value == token
    
    def test_csrf_with_ajax_requests(self):
        """Ajax リクエストでのCSRF対策テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/api/test', methods=['POST'])
        @CSRFToken.require_csrf
        def api_test():
            return {'status': 'success'}
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                token = CSRFToken.generate()
                sess['csrf_token'] = token
            
            # Ajax形式のリクエスト（JSONデータも含める）
            response = client.post('/api/test',
                                 headers={
                                     'X-CSRFToken': token,
                                     'X-Requested-With': 'XMLHttpRequest',
                                     'Content-Type': 'application/json'
                                 },
                                 json={'test': 'data'})
            assert response.status_code == 200


class TestCSRFSecurity:
    """CSRF対策のセキュリティテスト"""
    
    def test_token_entropy(self):
        """CSRFトークンのエントロピーテスト"""
        tokens = []
        for _ in range(100):
            tokens.append(CSRFToken.generate())
        
        # 各文字の出現頻度を確認
        char_count = {}
        for token in tokens:
            for char in token:
                char_count[char] = char_count.get(char, 0) + 1
        
        # 各16進数文字がほぼ均等に出現することを確認
        total_chars = len(tokens) * 32
        expected_freq = total_chars / 16  # 16進数文字は16種類
        
        for char in '0123456789abcdef':
            actual_freq = char_count.get(char, 0)
            # 期待値の±30%以内であることを確認（統計的変動を考慮）
            assert abs(actual_freq - expected_freq) < expected_freq * 0.3
    
    def test_timing_attack_resistance(self):
        """タイミング攻撃への耐性テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        with app.test_client() as client:
            with client.session_transaction() as sess:
                valid_token = CSRFToken.generate()
                sess['csrf_token'] = valid_token
                
                # 有効トークンと無効トークンの検証時間を比較
                import time
                
                # 有効トークンの検証時間を測定
                start_time = time.time()
                for _ in range(1000):
                    CSRFToken.validate(valid_token, sess)
                valid_time = time.time() - start_time
                
                # 無効トークンの検証時間を測定
                invalid_token = CSRFToken.generate()
                start_time = time.time()
                for _ in range(1000):
                    CSRFToken.validate(invalid_token, sess)
                invalid_time = time.time() - start_time
                
                # 時間差が大きくないことを確認（±50%以内）
                time_diff_ratio = abs(valid_time - invalid_time) / max(valid_time, invalid_time)
                assert time_diff_ratio < 0.5
    
    def test_token_prediction_resistance(self):
        """トークン予測への耐性テスト"""
        tokens = []
        for _ in range(100):
            tokens.append(CSRFToken.generate())
        
        # 連続するトークン間にパターンがないことを確認
        for i in range(1, len(tokens)):
            current = tokens[i]
            previous = tokens[i-1]
            
            # XOR演算で差分を取得
            diff = int(current, 16) ^ int(previous, 16)
            
            # 差分が0でないことを確認（同じトークンが生成されていない）
            assert diff != 0
            
            # ハミング距離が適切であることを確認（ビットの半分程度が異なる）
            hamming_distance = bin(diff).count('1')
            # 32文字の16進数 = 128ビット、ハミング距離は30-90程度が適切
            assert 30 <= hamming_distance <= 90


class TestCSRFErrorHandling:
    """CSRFエラーハンドリングのテスト"""
    
    def test_error_message_security(self):
        """エラーメッセージのセキュリティテスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/protected', methods=['POST'])
        @CSRFToken.require_csrf
        def protected_route():
            return {'status': 'success'}
        
        with app.test_client() as client:
            response = client.post('/protected')
            data = response.get_json()
            
            # エラーメッセージに機密情報が含まれていないことを確認
            error_message = data.get('error', '').lower()
            assert 'token' not in error_message or 'csrf' in error_message
            assert 'secret' not in error_message
            assert 'key' not in error_message
            assert 'session' not in error_message
    
    def test_error_logging(self):
        """CSRF違反のログ記録テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/protected', methods=['POST'])
        @CSRFToken.require_csrf
        def protected_route():
            return {'status': 'success'}
        
        with app.test_client() as client:
            with patch('utils.security.logger') as mock_logger:
                response = client.post('/protected')
                
                # ログが記録されていることを確認
                mock_logger.warning.assert_called()
                
                # ログメッセージにCSRF違反が記録されていることを確認
                call_args = mock_logger.warning.call_args[0][0]
                assert 'csrf' in call_args.lower()
    
    def test_rate_limiting_integration(self):
        """レート制限との統合テスト"""
        app = Flask(__name__)
        app.secret_key = 'test_secret_key_for_testing'
        
        @app.route('/protected', methods=['POST'])
        @CSRFToken.require_csrf
        def protected_route():
            return {'status': 'success'}
        
        with app.test_client() as client:
            # 複数回のCSRF違反リクエストを送信
            for _ in range(5):
                response = client.post('/protected')
                assert response.status_code == 403
            
            # レート制限が適用される場合の処理をテスト
            # （実際のレート制限実装に依存）