#!/usr/bin/env python3
"""
認証システムのログイン機能テストスクリプト
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5001"

def get_csrf_token(session, url):
    """CSRFトークンを取得"""
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    token = soup.find('input', {'name': 'csrf_token'})
    if token:
        return token.get('value')
    return None

def test_login():
    """ログイン機能のテスト"""
    session = requests.Session()
    
    # 1. ログインページにアクセス
    print("1. ログインページにアクセス...")
    login_url = f"{BASE_URL}/login"
    csrf_token = get_csrf_token(session, login_url)
    if not csrf_token:
        print("❌ CSRFトークンの取得に失敗しました")
        return
    print(f"✅ CSRFトークン取得成功: {csrf_token[:20]}...")
    
    # 2. ログイン試行（正しい認証情報）
    print("\n2. 正しい認証情報でログイン試行...")
    login_data = {
        'csrf_token': csrf_token,
        'username_or_email': 'testuser1',
        'password': 'testpass123',
        'remember_me': 'y'
    }
    
    response = session.post(login_url, data=login_data, allow_redirects=False)
    if response.status_code == 302:  # リダイレクト
        print(f"✅ ログイン成功！リダイレクト先: {response.headers.get('Location')}")
        
        # ホームページにアクセスして認証状態を確認
        home_response = session.get(BASE_URL)
        if 'testuser1' in home_response.text and 'ログアウト' in home_response.text:
            print("✅ 認証状態の確認成功：ユーザー名が表示されています")
        else:
            print("❌ 認証状態の確認失敗")
    else:
        print(f"❌ ログイン失敗 (ステータスコード: {response.status_code})")
    
    # 3. 保護されたページへのアクセス
    print("\n3. 保護されたページへのアクセス...")
    protected_response = session.get(f"{BASE_URL}/protected")
    if protected_response.status_code == 200 and 'testuser1' in protected_response.text:
        print("✅ 保護されたページへのアクセス成功")
    else:
        print("❌ 保護されたページへのアクセス失敗")
    
    # 4. ログアウト
    print("\n4. ログアウト...")
    logout_response = session.get(f"{BASE_URL}/logout", allow_redirects=False)
    if logout_response.status_code == 302:
        print("✅ ログアウト成功")
        
        # ログアウト後の状態確認
        home_after_logout = session.get(BASE_URL)
        if 'ログイン' in home_after_logout.text and 'testuser1' not in home_after_logout.text:
            print("✅ ログアウト状態の確認成功")
    else:
        print("❌ ログアウト失敗")
    
    # 5. 間違った認証情報でのログイン試行
    print("\n5. 間違った認証情報でログイン試行...")
    csrf_token = get_csrf_token(session, login_url)
    wrong_login_data = {
        'csrf_token': csrf_token,
        'username_or_email': 'testuser1',
        'password': 'wrongpassword',
        'remember_me': ''
    }
    
    wrong_response = session.post(login_url, data=wrong_login_data)
    if wrong_response.status_code == 200 and 'パスワードが正しくありません' in wrong_response.text:
        print("✅ 不正なパスワードのエラー処理が正常に動作")
    else:
        print("❌ エラー処理が期待通りではありません")

if __name__ == '__main__':
    print("=== 認証システムログイン機能テスト ===\n")
    test_login()
    print("\n=== テスト完了 ===")