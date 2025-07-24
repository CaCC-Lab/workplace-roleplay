#!/usr/bin/env python
"""
デバッグ用のAPIテストスクリプト
"""
import json
import os
import sys
sys.path.append('.')

from app import app
from utils.security import CSRFToken

def debug_chat_api():
    """チャットAPIをデバッグ"""
    
    with app.test_client() as client:
        with app.app_context():
            # 実際のCSRFトークンを生成
            csrf_token = CSRFToken.generate()
            
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = 1  # テスト用ユーザーID
                sess['conversation_history'] = []
                sess['chat_settings'] = {
                    'system_prompt': 'あなたは職場でのコミュニケーションを支援するAIアシスタントです。テスト用なので10文字以内で短く応答してください。'
                }
            
            # 実際のAPI呼び出し
            response = client.post('/api/chat',
                data=json.dumps({
                    'message': 'こんにちは、テストです',
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            print(f'Status Code: {response.status_code}')
            print(f'Content Type: {response.content_type}')
            print(f'Response Data: {response.get_data(as_text=True)}')
            
            if response.status_code != 200:
                try:
                    error_data = response.get_json()
                    print(f'Error Data: {error_data}')
                except:
                    print('Could not parse error as JSON')

if __name__ == '__main__':
    debug_chat_api()