#!/usr/bin/env python3
"""
CSRFトークンエラーのデバッグ用スクリプト
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import app
from tests.helpers.csrf_helpers import CSRFTestClient

def test_csrf_token_debug():
    """CSRFトークンの生成と検証をデバッグ"""
    
    # テストクライアントを作成
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    client = app.test_client()
    
    print("\n=== CSRFデバッグテスト開始 ===")
    
    # 1. 直接エンドポイントからCSRFトークンを取得
    print("1. CSRFトークンエンドポイントを直接呼び出し:")
    response = client.get('/api/csrf-token')
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        direct_token = data.get('csrf_token')
        print(f"   Token: {direct_token}")
    else:
        print(f"   Error: {response.get_data(as_text=True)}")
        return
    
    # 2. セッションの内容を確認
    print("2. セッション内容確認:")
    with client.session_transaction() as sess:
        session_token = sess.get('csrf_token')
        print(f"   Session Token: {session_token}")
        print(f"   Token Match: {direct_token == session_token}")
    
    # 3. CSRFTestClientを使ってトークンを取得
    print("3. CSRFTestClientでトークン取得:")
    csrf_client = CSRFTestClient(client)
    csrf_token = csrf_client._get_csrf_token()
    print(f"   CSRFTestClient Token: {csrf_token}")
    
    # 4. 手動でCSRFトークン付きリクエストを送信
    print("4. 手動でCSRFトークン付きリクエストを送信:")
    with client.session_transaction() as sess:
        print(f"   Pre-request session: {dict(sess)}")
    
    response = client.post('/api/chat', 
                          json={
                              'message': 'Hello', 
                              'model': 'gemini-1.5-flash',
                              'csrf_token': direct_token
                          },
                          headers={'X-CSRFToken': direct_token})
    
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Error: {response.get_data(as_text=True)}")
    
    # 5. CSRFTestClientがトークンをどう追加するかをデバッグ
    print("5. CSRFTestClientトークン追加デバッグ:")
    csrf_client_2 = CSRFTestClient(client)
    
    # トークンを取得
    token_from_csrf_client = csrf_client_2._get_csrf_token()
    print(f"   CSRFTestClient Token: {token_from_csrf_client}")
    
    # セッションの状態を確認
    with client.session_transaction() as sess:
        print(f"   Session token before request: {sess.get('csrf_token')}")
        print(f"   Session data: {dict(sess)}")
    
    # どのようにトークンが追加されるかテスト
    kwargs = {'json': {'message': 'Hello', 'model': 'gemini-1.5-flash'}}
    kwargs_with_csrf = csrf_client_2._add_csrf_token(**kwargs)
    print(f"   Original kwargs: {kwargs}")
    print(f"   kwargs with CSRF: {kwargs_with_csrf}")
    
    # 6. CSRFTestClientを使ってリクエストを送信
    print("6. CSRFTestClientでリクエスト送信:")
    with client.session_transaction() as sess:
        sess['chat_settings'] = {
            'system_prompt': 'Test',
            'model': 'gemini-1.5-flash'
        }
    
    try:
        response = csrf_client.post('/api/chat', 
                                   json={
                                       'message': 'Hello CSRFTestClient', 
                                       'model': 'gemini-1.5-flash'
                                   })
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error: {response.get_data(as_text=True)}")
    except Exception as e:
        print(f"   Exception: {e}")

if __name__ == "__main__":
    test_csrf_token_debug()