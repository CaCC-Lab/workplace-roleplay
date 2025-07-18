#!/usr/bin/env python3
"""
セキュリティ機能のテストスイート（メインアプリ統合版）

TDDアプローチ：
1. 入力検証機能のテスト
2. レート制限機能のテスト
3. XSS・SQLインジェクション対策のテスト

注意: このファイルはメインアプリ（app.py）との統合テストです。
依存関係の問題がある場合は test_security_standalone.py を使用してください。

実行可能な代替テスト:
- test_security_standalone.py - スタンドアロン版（推奨）
- test_rate_limit.py - レート制限専用テスト
- test_security_integration.py - 統合テスト
"""
import unittest
import time
import json
import sys
import os
from unittest.mock import patch, MagicMock

# 環境変数設定（テスト用）
os.environ['TESTING'] = 'True'
os.environ['FLASK_SECRET_KEY'] = 'test-secret-key'
os.environ['SESSION_TYPE'] = 'filesystem'

# メインアプリのインポート（エラーハンドリング付き）
try:
    from app import app
    from models import db, User
    INTEGRATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Cannot import main app components: {e}")
    print("This is expected if dependencies are not fully installed.")
    print("Please use test_security_standalone.py instead.")
    INTEGRATION_AVAILABLE = False


class SecurityTestCase(unittest.TestCase):
    """セキュリティ機能のテストケース"""
    
    def setUp(self):
        """テスト前の設定"""
        if not INTEGRATION_AVAILABLE:
            self.skipTest("Main app integration not available")
            
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # テスト時はCSRF無効
        # セッションベースモード（データベース不要）
        self.app.config['SESSION_TYPE'] = 'filesystem'
        self.client = self.app.test_client()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        pass  # セッションベースなのでクリーンアップ不要


class InputValidationTest(SecurityTestCase):
    """入力検証のテストクラス"""
    
    def test_xss_prevention_in_chat_message(self):
        """チャットメッセージのXSS攻撃防止テスト（失敗するテスト）"""
        malicious_script = "<script>alert('XSS')</script>"
        
        response = self.client.post('/api/chat', 
                                  data=json.dumps({'message': malicious_script}),
                                  content_type='application/json')
        
        # XSSスクリプトがサニタイズされていることを確認
        self.assertNotIn('<script>', response.get_data(as_text=True))
        self.assertNotIn('alert', response.get_data(as_text=True))
    
    def test_sql_injection_prevention(self):
        """SQLインジェクション攻撃防止テスト（失敗するテスト）"""
        malicious_query = "'; DROP TABLE users; --"
        
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': malicious_query}),
                                  content_type='application/json')
        
        # レスポンスが適切にサニタイズされていることを確認
        self.assertNotIn('DROP TABLE', response.get_data(as_text=True))
        self.assertNotIn('--;', response.get_data(as_text=True))
    
    def test_invalid_json_handling(self):
        """不正なJSONデータの処理テスト（失敗するテスト）"""
        invalid_json = "{'invalid': json}"
        
        response = self.client.post('/api/chat',
                                  data=invalid_json,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid JSON', response.get_data(as_text=True))
    
    def test_message_length_validation(self):
        """メッセージ長の検証テスト（失敗するテスト）"""
        long_message = "A" * 10000  # 10KB のメッセージ
        
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': long_message}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Message too long', response.get_data(as_text=True))
    
    def test_empty_message_validation(self):
        """空メッセージの検証テスト（失敗するテスト）"""
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': ''}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Message cannot be empty', response.get_data(as_text=True))


class RateLimitTest(SecurityTestCase):
    """レート制限のテストクラス"""
    
    def test_ip_based_rate_limit(self):
        """IPベースレート制限テスト（失敗するテスト）"""
        # 短時間で複数リクエストを送信
        for i in range(6):  # 制限値（5回）を超える
            response = self.client.post('/api/chat',
                                      data=json.dumps({'message': f'test message {i}'}),
                                      content_type='application/json')
        
        # 6回目のリクエストでレート制限エラーになることを確認
        self.assertEqual(response.status_code, 429)
        self.assertIn('Rate limit exceeded', response.get_data(as_text=True))
    
    def test_user_based_rate_limit(self):
        """ユーザーベースレート制限テスト（失敗するテスト）"""
        # テストユーザーでログイン
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['_fresh'] = True
        
        # 短時間で複数リクエスト
        for i in range(11):  # ユーザー制限値（10回）を超える
            response = self.client.post('/api/chat',
                                      data=json.dumps({'message': f'user test {i}'}),
                                      content_type='application/json')
        
        # 11回目のリクエストでレート制限エラー
        self.assertEqual(response.status_code, 429)
        self.assertIn('User rate limit exceeded', response.get_data(as_text=True))
    
    def test_gemini_api_quota_tracking(self):
        """Gemini API使用量追跡テスト（失敗するテスト）"""
        # Gemini API呼び出しをモック
        with patch('app.get_gemini_response') as mock_gemini:
            mock_gemini.return_value = "Test response"
            
            # API使用量の追跡
            response = self.client.post('/api/chat',
                                      data=json.dumps({'message': 'test'}),
                                      content_type='application/json')
            
            # 使用量が記録されていることを確認
            # TODO: 実装後に具体的なアサーションを追加
            self.assertTrue(True)  # プレースホルダー


class CSRFProtectionTest(SecurityTestCase):
    """CSRF保護のテストクラス"""
    
    def test_csrf_token_required(self):
        """CSRFトークンが必要なエンドポイントのテスト（失敗するテスト）"""
        # CSRF保護を有効にしてテスト
        self.app.config['WTF_CSRF_ENABLED'] = True
        
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': 'test'}),
                                  content_type='application/json')
        
        # CSRFトークンなしでは400エラー
        self.assertEqual(response.status_code, 400)
        self.assertIn('CSRF', response.get_data(as_text=True))


if __name__ == '__main__':
    print("=== セキュリティテストスイート（メインアプリ統合版） ===")
    
    if not INTEGRATION_AVAILABLE:
        print("Warning: Main app integration not available due to dependency issues")
        print("Please use alternative test files:")
        print("  - test_security_standalone.py (standalone security tests)")
        print("  - test_rate_limit.py (rate limiting tests)")
        print("  - test_security_integration.py (integration tests)")
        print()
        print("Running tests with automatic skipping...")
    else:
        print("Main app integration available - running full test suite")
    
    print()
    unittest.main(verbosity=2)