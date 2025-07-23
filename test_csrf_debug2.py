#!/usr/bin/env python3
"""
CSRFトークンの動作をデバッグ - より詳細なチェック
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app import app
from tests.helpers.csrf_helpers import CSRFTestClient
from utils.security import CSRFToken
import json

def debug_csrf_flow():
    """CSRFトークンフローを詳細にデバッグ"""
    print("=== CSRF デバッグ開始 ===")
    
    with app.test_client() as client:
        csrf_client = CSRFTestClient(client)
        
        # Step 1: セッション状態の確認
        print("\nStep 1: 初期セッション状態")
        with csrf_client.session_transaction() as sess:
            print(f"初期セッション: {dict(sess)}")
        
        # Step 2: CSRFトークンを手動で取得
        print("\nStep 2: CSRFトークン手動取得")
        token1 = csrf_client._get_csrf_token()
        print(f"取得したトークン: {token1}")
        
        # Step 3: セッション内のトークンを確認
        print("\nStep 3: セッション内トークン確認")
        with csrf_client.session_transaction() as sess:
            session_token = sess.get('csrf_token')
            print(f"セッショントークン: {session_token}")
            print(f"トークン一致: {token1 == session_token}")
        
        # Step 4: リクエストパラメータの確認
        print("\nStep 4: リクエストパラメータ生成")
        test_json = {"message": "test", "model": "gemini-1.5-flash"}
        kwargs = csrf_client._add_csrf_token(json=test_json)
        print(f"生成されたkwargs: {kwargs}")
        
        # Step 5: トークン検証のテスト
        print("\nStep 5: トークン検証テスト")
        with csrf_client.session_transaction() as sess:
            is_valid = CSRFToken.validate(token1, sess)
            print(f"トークンバリデーション結果: {is_valid}")
        
        # Step 6: 実際のリクエスト送信
        print("\nStep 6: 実際のリクエスト送信")
        
        # セッション設定（テストで使用される形式）
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト用プロンプト",
                "model": "gemini-1.5-flash"
            }
            print(f"設定後のセッション: {dict(sess)}")
        
        # リクエスト実行
        response = csrf_client.post('/api/chat', json={
            "message": "デバッグテスト",
            "model": "gemini-1.5-flash"
        })
        
        print(f"レスポンスステータス: {response.status_code}")
        print(f"レスポンス内容: {response.get_data(as_text=True)}")
        
        # Step 7: CSRF-Tokenエンドポイントのテスト
        print("\nStep 7: /api/csrf-token エンドポイントテスト")
        token_response = client.get('/api/csrf-token')
        print(f"トークンエンドポイント ステータス: {token_response.status_code}")
        if token_response.status_code == 200:
            token_data = token_response.get_json()
            print(f"エンドポイントからのトークン: {token_data}")
        
        # Step 8: セッションの最終状態
        print("\nStep 8: 最終セッション状態")
        with csrf_client.session_transaction() as sess:
            print(f"最終セッション: {dict(sess)}")

if __name__ == "__main__":
    debug_csrf_flow()