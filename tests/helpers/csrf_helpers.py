"""
CSRFテスト用のヘルパー関数とフィクスチャ
既存テストのCSRF対応を効率化
"""
import pytest
from typing import Any, Dict, Optional, Union


class CSRFTestClient:
    """CSRF対応のテストクライアント
    
    既存のFlaskテストクライアントをラップして、
    自動的にCSRFトークンを付与する機能を提供
    """
    
    def __init__(self, client):
        """
        Args:
            client: Flaskのテストクライアント
        """
        self.client = client
        self._csrf_token = None
    
    def _get_csrf_token(self) -> str:
        """CSRFトークンを取得または更新"""
        if self._csrf_token is None:
            response = self.client.get('/api/csrf-token')
            if response.status_code == 200:
                data = response.get_json()
                self._csrf_token = data.get('csrf_token')
            else:
                # CSRFトークンエンドポイントが利用できない場合、
                # セッションから直接生成
                from utils.security import CSRFToken
                with self.client.session_transaction() as sess:
                    self._csrf_token = CSRFToken.generate()
                    sess['csrf_token'] = self._csrf_token
        
        return self._csrf_token
    
    def _add_csrf_token(self, **kwargs) -> Dict[str, Any]:
        """リクエストにCSRFトークンを追加"""
        csrf_token = self._get_csrf_token()
        
        # JSONリクエストの場合
        if 'json' in kwargs:
            if kwargs['json'] is None:
                kwargs['json'] = {}
            # 既にcsrf_tokenが含まれている場合は上書きしない
            if 'csrf_token' not in kwargs['json']:
                kwargs['json']['csrf_token'] = csrf_token
        
        # フォームデータの場合
        elif 'data' in kwargs:
            if kwargs['data'] is None:
                kwargs['data'] = {}
            if isinstance(kwargs['data'], dict) and 'csrf_token' not in kwargs['data']:
                kwargs['data']['csrf_token'] = csrf_token
        
        # ヘッダーにも追加（デフォルトの方法）
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        if 'X-CSRFToken' not in kwargs['headers']:
            kwargs['headers']['X-CSRFToken'] = csrf_token
        
        return kwargs
    
    def post(self, url: str, **kwargs) -> Any:
        """CSRFトークン付きPOSTリクエスト"""
        kwargs = self._add_csrf_token(**kwargs)
        return self.client.post(url, **kwargs)
    
    def put(self, url: str, **kwargs) -> Any:
        """CSRFトークン付きPUTリクエスト"""
        kwargs = self._add_csrf_token(**kwargs)
        return self.client.put(url, **kwargs)
    
    def patch(self, url: str, **kwargs) -> Any:
        """CSRFトークン付きPATCHリクエスト"""
        kwargs = self._add_csrf_token(**kwargs)
        return self.client.patch(url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> Any:
        """CSRFトークン付きDELETEリクエスト"""
        kwargs = self._add_csrf_token(**kwargs)
        return self.client.delete(url, **kwargs)
    
    def get(self, url: str, **kwargs) -> Any:
        """通常のGETリクエスト（CSRFトークン不要）"""
        return self.client.get(url, **kwargs)
    
    def head(self, url: str, **kwargs) -> Any:
        """通常のHEADリクエスト（CSRFトークン不要）"""
        return self.client.head(url, **kwargs)
    
    def options(self, url: str, **kwargs) -> Any:
        """通常のOPTIONSリクエスト（CSRFトークン不要）"""
        return self.client.options(url, **kwargs)
    
    def session_transaction(self):
        """セッション操作の委譲"""
        return self.client.session_transaction()
    
    def reset_csrf_token(self):
        """CSRFトークンをリセット（テスト間での独立性確保）"""
        self._csrf_token = None


@pytest.fixture
def csrf_client(client):
    """CSRF対応テストクライアントのフィクスチャ
    
    使用例:
        def test_chat_api(csrf_client):
            response = csrf_client.post('/api/chat', json={'message': 'Hello'})
            assert response.status_code == 200
    """
    return CSRFTestClient(client)


@pytest.fixture
def csrf_exempt_client(client):
    """CSRF除外のテストクライアント
    
    CSRFトークンを意図的に含めない、
    セキュリティテスト用のクライアント
    """
    return client


def with_csrf_token(client, **request_kwargs):
    """単発のCSRF対応リクエスト
    
    Args:
        client: Flaskテストクライアント
        **request_kwargs: リクエストパラメータ
        
    Returns:
        CSRFトークンが追加されたリクエストパラメータ
        
    使用例:
        response = client.post('/api/chat', **with_csrf_token(client, json={'message': 'Hello'}))
    """
    csrf_client = CSRFTestClient(client)
    return csrf_client._add_csrf_token(**request_kwargs)


def create_test_session_with_csrf(client, additional_data: Optional[Dict[str, Any]] = None):
    """CSRFトークン付きのテストセッションを作成
    
    Args:
        client: Flaskテストクライアント
        additional_data: セッションに追加するデータ
        
    Returns:
        CSRFトークン
    """
    from utils.security import CSRFToken
    
    with client.session_transaction() as sess:
        csrf_token = CSRFToken.generate()
        sess['csrf_token'] = csrf_token
        
        if additional_data:
            for key, value in additional_data.items():
                sess[key] = value
    
    return csrf_token


# テストで使用するためのデコレータ
def requires_csrf(test_func):
    """テスト関数にCSRF要件を明示するデコレータ
    
    使用例:
        @requires_csrf
        def test_protected_endpoint(csrf_client):
            # このテストはCSRF保護されたエンドポイントをテストすることを明示
            response = csrf_client.post('/api/protected')
            assert response.status_code == 200
    """
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    
    wrapper.__name__ = test_func.__name__
    wrapper.__doc__ = f"{test_func.__doc__ or ''}\n[CSRF Required Test]"
    return wrapper


def no_csrf(test_func):
    """テスト関数がCSRF除外であることを明示するデコレータ
    
    使用例:
        @no_csrf
        def test_csrf_violation(csrf_exempt_client):
            # このテストはCSRF攻撃をシミュレート
            response = csrf_exempt_client.post('/api/protected')
            assert response.status_code == 403
    """
    def wrapper(*args, **kwargs):
        return test_func(*args, **kwargs)
    
    wrapper.__name__ = test_func.__name__
    wrapper.__doc__ = f"{test_func.__doc__ or ''}\n[CSRF Exempt Test]"
    return wrapper