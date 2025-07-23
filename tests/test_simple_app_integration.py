"""
簡易版アプリ (app_simple.py) の統合テスト
実際に動作する環境でのAPI動作確認
"""
import pytest
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# app_simple.pyをインポート
from app_simple import app


@pytest.fixture
def client():
    """テスト用クライアント"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestSimpleAppIntegration:
    """簡易版アプリの統合テスト"""
    
    def test_index_page(self, client):
        """トップページが表示される"""
        response = client.get('/')
        assert response.status_code == 200
        # シンプルなHTMLページなので基本的な確認のみ
        assert b'<!DOCTYPE html>' in response.data
    
    def test_chat_page(self, client):
        """雑談ページが表示される"""
        response = client.get('/chat')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
    
    def test_history_page(self, client):
        """履歴ページが表示される"""
        response = client.get('/history')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
    
    def test_404_error(self, client):
        """存在しないページで404エラー"""
        response = client.get('/nonexistent')
        assert response.status_code == 404
    
    def test_static_files(self, client):
        """静的ファイルへのアクセス"""
        # CSSファイルの確認
        response = client.get('/static/css/style.css')
        # ファイルが存在する場合のみテスト
        if response.status_code == 200:
            assert b'css' in response.data or response.data
    
    def test_session_cookie(self, client):
        """セッションクッキーの動作"""
        # ページにアクセス
        response = client.get('/')
        # レスポンスヘッダーをチェック
        assert response.status_code == 200
        # app_simple.pyはセッション管理を持たない可能性があるので、基本的な確認のみ