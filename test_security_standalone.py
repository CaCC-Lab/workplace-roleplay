#!/usr/bin/env python3
"""
スタンドアロンのセキュリティテスト
依存関係を最小限にしてテストのみ実行
"""
import unittest
import json
from flask import Flask


def create_test_app():
    """テスト用の最小限のFlaskアプリケーション"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.secret_key = 'test-secret-key'
    
    # セキュリティ機能をインポート
    from security_utils import secure_endpoint
    
    # テスト用のチャットエンドポイント（セキュリティ機能付き）
    @app.route('/api/chat', methods=['POST'])
    @secure_endpoint
    def chat():
        """セキュリティ強化後のチャットエンドポイント"""
        # サニタイズされたデータを使用
        sanitized_message = request.sanitized_data['message']
        return json.dumps({'response': f'Echo: {sanitized_message}'})
    
    return app


class SecurityTestCase(unittest.TestCase):
    """セキュリティ機能のテストケース"""
    
    def setUp(self):
        """テスト前の設定"""
        self.app = create_test_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.app_context.pop()


class InputValidationTest(SecurityTestCase):
    """入力検証のテストクラス"""
    
    def test_xss_prevention_in_chat_message(self):
        """チャットメッセージのXSS攻撃防止テスト（失敗するテスト）"""
        malicious_script = "<script>alert('XSS')</script>"
        
        response = self.client.post('/api/chat', 
                                  data=json.dumps({'message': malicious_script}),
                                  content_type='application/json')
        
        response_text = response.get_data(as_text=True)
        print(f"XSSテスト応答: {response_text}")
        
        # XSSスクリプトがサニタイズされていることを確認（現状は失敗する）
        self.assertNotIn('<script>', response_text, "XSSスクリプトがサニタイズされていません")
        self.assertNotIn('alert', response_text, "alertが含まれています")
    
    def test_sql_injection_prevention(self):
        """SQLインジェクション攻撃防止テスト（失敗するテスト）"""
        malicious_query = "'; DROP TABLE users; --"
        
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': malicious_query}),
                                  content_type='application/json')
        
        response_text = response.get_data(as_text=True)
        print(f"SQLインジェクションテスト応答: {response_text}")
        
        # レスポンスが適切にサニタイズされていることを確認（現状は失敗する）
        self.assertNotIn('DROP TABLE', response_text, "DROP TABLEが含まれています")
        self.assertNotIn('--;', response_text, "SQLコメントが含まれています")
    
    def test_invalid_json_handling(self):
        """不正なJSONデータの処理テスト（失敗するテスト）"""
        invalid_json = "{'invalid': json}"
        
        response = self.client.post('/api/chat',
                                  data=invalid_json,
                                  content_type='application/json')
        
        print(f"不正JSONテスト応答: ステータス={response.status_code}")
        
        # 不正なJSONで400エラーを返すことを確認（現状は実装されていない）
        self.assertEqual(response.status_code, 400, "不正なJSONに対して400エラーが返されていません")
        
        response_text = response.get_data(as_text=True)
        self.assertIn('Invalid JSON', response_text, "適切なエラーメッセージが表示されていません")
    
    def test_message_length_validation(self):
        """メッセージ長の検証テスト（失敗するテスト）"""
        long_message = "A" * 10000  # 10KB のメッセージ
        
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': long_message}),
                                  content_type='application/json')
        
        print(f"長いメッセージテスト応答: ステータス={response.status_code}")
        
        # 長すぎるメッセージで400エラーを返すことを確認（現状は実装されていない）
        self.assertEqual(response.status_code, 400, "長すぎるメッセージに対して400エラーが返されていません")
        
        response_text = response.get_data(as_text=True)
        self.assertIn('Message too long', response_text, "適切なエラーメッセージが表示されていません")
    
    def test_empty_message_validation(self):
        """空メッセージの検証テスト（失敗するテスト）"""
        response = self.client.post('/api/chat',
                                  data=json.dumps({'message': ''}),
                                  content_type='application/json')
        
        print(f"空メッセージテスト応答: ステータス={response.status_code}")
        
        # 空メッセージで400エラーを返すことを確認（現状は実装されていない）
        self.assertEqual(response.status_code, 400, "空メッセージに対して400エラーが返されていません")
        
        response_text = response.get_data(as_text=True)
        self.assertIn('Message cannot be empty', response_text, "適切なエラーメッセージが表示されていません")


if __name__ == '__main__':
    print("=== スタンドアロンセキュリティテストスイート ===")
    print("TDD REDフェーズ: これらのテストは現在失敗します")
    print("次に実装を行ってテストをパスさせます")
    print()
    
    # requestをインポート（Flaskアプリケーション内で使用）
    from flask import request
    
    unittest.main(verbosity=2)