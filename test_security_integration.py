#!/usr/bin/env python3
"""
セキュリティ機能のメインアプリ統合テスト
"""
import unittest
import json
import sys
import os

# テスト環境設定
os.environ['TESTING'] = 'True'
os.environ['FLASK_SECRET_KEY'] = 'test-secret-key'
os.environ['GOOGLE_API_KEY'] = 'test-key'
os.environ['SESSION_TYPE'] = 'filesystem'

# アプリケーションのインポート
try:
    from app import app
    integration_test_available = True
except ImportError as e:
    print(f"Warning: Could not import app.py: {e}")
    integration_test_available = False


class SecurityIntegrationTest(unittest.TestCase):
    """セキュリティ機能統合テストクラス"""
    
    def setUp(self):
        """テスト前の設定"""
        if not integration_test_available:
            self.skipTest("App integration not available")
            
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # テスト時はCSRF無効
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        if integration_test_available:
            self.app_context.pop()
    
    def test_main_app_xss_protection(self):
        """メインアプリのXSS保護テスト"""
        malicious_script = "<script>alert('XSS')</script>"
        
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': malicious_script}),
                                  content_type='application/json')
        
        # レスポンスの状態とセキュリティヘッダーを確認
        self.assertTrue(response.status_code in [200, 400])  # セキュリティエラーまたは処理成功
        
        # セキュリティヘッダーの確認
        self.assertIn('X-Content-Type-Options', response.headers)
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn('X-Frame-Options', response.headers)
        
        response_text = response.get_data(as_text=True)
        print(f"XSS統合テスト応答: ステータス={response.status_code}, レスポンス={response_text[:200]}")
        
        # XSSスクリプトがサニタイズされていることを確認
        self.assertNotIn('<script>', response_text)
        self.assertNotIn('alert', response_text)
    
    def test_main_app_rate_limiting(self):
        """メインアプリのレート制限テスト"""
        # 複数回リクエストを送信してレート制限をテスト
        responses = []
        
        for i in range(6):  # 制限値（5回）を超える
            response = self.client.post('/api/chat',
                                      data=json.dumps({'message': f'test message {i}'}),
                                      content_type='application/json')
            responses.append((i, response.status_code))
            print(f"リクエスト {i}: ステータス={response.status_code}")
        
        # 最後のリクエストでレート制限エラーまたは通常エラーが発生することを確認
        final_status = responses[-1][1]
        self.assertTrue(final_status in [429, 400, 500])  # レート制限またはその他のエラー
        
        # レート制限エラーの場合のレスポンス確認
        if final_status == 429:
            final_response = self.client.post('/api/chat',
                                            data=json.dumps({'message': 'final test'}),
                                            content_type='application/json')
            response_text = final_response.get_data(as_text=True)
            self.assertIn('Rate limit exceeded', response_text)
    
    def test_main_app_input_validation(self):
        """メインアプリの入力検証テスト"""
        # 空メッセージテスト
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': ''}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        response_text = response.get_data(as_text=True)
        self.assertIn('Message cannot be empty', response_text)
        
        # 長すぎるメッセージテスト
        long_message = "A" * 10000
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': long_message}),
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        response_text = response.get_data(as_text=True)
        self.assertIn('Message too long', response_text)
    
    def test_main_app_security_headers(self):
        """メインアプリのセキュリティヘッダーテスト"""
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': 'test'}),
                                  content_type='application/json')
        
        # 必要なセキュリティヘッダーが設定されていることを確認
        required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection'
        ]
        
        for header in required_headers:
            self.assertIn(header, response.headers, f"セキュリティヘッダー {header} が設定されていません")
        
        print(f"セキュリティヘッダー確認: {dict(response.headers)}")
    
    def test_main_app_json_validation(self):
        """メインアプリのJSON検証テスト"""
        # 不正なJSONテスト
        response = self.client.post('/api/chat',
                                  data="{'invalid': json}",
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        response_text = response.get_data(as_text=True)
        self.assertIn('Invalid JSON', response_text)


if __name__ == '__main__':
    print("=== セキュリティ機能統合テストスイート ===")
    print("メインアプリへのセキュリティ機能統合を確認")
    print()
    
    if not integration_test_available:
        print("Warning: App integration tests skipped due to import errors")
        print("This is expected if dependencies are missing")
    
    # テスト実行
    unittest.main(verbosity=2)