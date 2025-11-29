"""
セキュリティ修正のテストスイート
5AI議論で特定された問題の回帰テスト
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.security import SecurityUtils, CSRFProtection, RateLimiter
from app import app
import json

class TestSecurityFixes:
    """セキュリティ修正のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
    
    def test_xss_prevention(self):
        """XSS攻撃の防御テスト"""
        malicious_inputs = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror="alert(1)">',
            '<iframe src="evil.com"></iframe>',
            '"><script>alert(String.fromCharCode(88,83,83))</script>'
        ]
        
        for malicious in malicious_inputs:
            cleaned = SecurityUtils.escape_html(malicious)
            # スクリプトタグやイベントハンドラが除去されていることを確認
            assert '<script' not in cleaned.lower()
            assert 'onerror' not in cleaned.lower()
            assert '<iframe' not in cleaned.lower()
            print(f"✓ XSS防御成功: {malicious[:30]}...")
    
    def test_no_double_escaping(self):
        """二重エスケープが発生しないことを確認"""
        # 正常なHTMLコンテンツ
        normal_content = '<p>これは<strong>正常な</strong>コンテンツです</p>'
        escaped_once = SecurityUtils.escape_html(normal_content)
        
        # &lt;&gt;のような二重エスケープが発生していないことを確認
        assert '&amp;lt;' not in escaped_once
        assert '&amp;gt;' not in escaped_once
        
        # 許可されたタグは保持される
        assert '<p>' in escaped_once or '<strong>' in escaped_once
        print("✓ 二重エスケープなし")
    
    def test_csrf_token_generation(self):
        """CSRFトークン生成のテスト"""
        token1 = CSRFProtection.generate_token()
        token2 = CSRFProtection.generate_token()
        
        # トークンが十分な長さを持つ
        assert len(token1) == 64  # 32バイト = 64文字の16進数
        assert len(token2) == 64
        
        # トークンがユニーク
        assert token1 != token2
        print("✓ CSRFトークン生成成功")
    
    def test_csrf_protection_on_v2_endpoints(self):
        """V2エンドポイントでCSRF保護が有効か確認"""
        # CSRFトークンなしでPOSTリクエスト
        response = self.client.post('/api/v2/chat',
            json={'message': 'test'},
            headers={'Content-Type': 'application/json'}
        )
        
        # CSRF保護により403が返される
        assert response.status_code == 403
        data = json.loads(response.data)
        assert 'CSRF' in data.get('error', '')
        print("✓ CSRF保護が有効")
    
    def test_rate_limiting(self):
        """レート制限のテスト"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # 3回まではOK
        for i in range(3):
            assert limiter.is_allowed('test_user') == True
        
        # 4回目はブロック
        assert limiter.is_allowed('test_user') == False
        
        # 別のユーザーはOK
        assert limiter.is_allowed('another_user') == True
        print("✓ レート制限が機能")
    
    def test_input_validation(self):
        """入力検証のテスト"""
        # 正常な入力
        valid, error = SecurityUtils.validate_message("これは正常なメッセージです")
        assert valid == True
        assert error is None
        
        # 空のメッセージ
        valid, error = SecurityUtils.validate_message("")
        assert valid == False
        assert "空" in error
        
        # 長すぎるメッセージ
        long_message = "a" * 10001
        valid, error = SecurityUtils.validate_message(long_message)
        assert valid == False
        assert "長すぎ" in error
        
        # 危険なパターン
        dangerous = "<script>alert(1)</script>"
        valid, error = SecurityUtils.validate_message(dangerous)
        assert valid == False
        assert "不正" in error
        print("✓ 入力検証が機能")
    
    def test_sha256_hashing(self):
        """SHA-256ハッシュの使用確認"""
        user_id = "test_user_123"
        hashed = SecurityUtils.hash_user_id(user_id)
        
        # SHA-256は64文字の16進数
        assert len(hashed) == 64
        assert all(c in '0123456789abcdef' for c in hashed)
        
        # 同じ入力は同じハッシュ
        hashed2 = SecurityUtils.hash_user_id(user_id)
        assert hashed == hashed2
        
        # 異なる入力は異なるハッシュ
        hashed3 = SecurityUtils.hash_user_id("different_user")
        assert hashed != hashed3
        print("✓ SHA-256ハッシュが使用されている")
    
    def test_model_name_validation(self):
        """モデル名検証のテスト"""
        # 有効なモデル名
        valid_models = [
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-1.0-pro'
        ]
        
        for model in valid_models:
            assert SecurityUtils.validate_model_name(model) == True
        
        # 無効なモデル名
        invalid_models = [
            'unknown-model',
            '<script>alert(1)</script>',
            '../../../etc/passwd',
            'gemini-1.5-flash; DROP TABLE users;'
        ]
        
        for model in invalid_models:
            assert SecurityUtils.validate_model_name(model) == False
        
        print("✓ モデル名検証が機能")

def run_all_tests():
    """全てのテストを実行"""
    print("\n" + "="*60)
    print("🔒 セキュリティ修正テストを実行中...")
    print("="*60 + "\n")
    
    test_suite = TestSecurityFixes()
    test_suite.setup_method()
    
    try:
        test_suite.test_xss_prevention()
        test_suite.test_no_double_escaping()
        test_suite.test_csrf_token_generation()
        test_suite.test_csrf_protection_on_v2_endpoints()
        test_suite.test_rate_limiting()
        test_suite.test_input_validation()
        test_suite.test_sha256_hashing()
        test_suite.test_model_name_validation()
        
        print("\n" + "="*60)
        print("✅ 全てのセキュリティテストが成功しました！")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        raise
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        raise

if __name__ == "__main__":
    run_all_tests()