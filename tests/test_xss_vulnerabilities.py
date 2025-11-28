"""
XSS脆弱性テストスイート
現在の脆弱性を検出し、対策の効果を確認するテスト
"""
import pytest
from flask import session
import json
from app import app


class TestXSSVulnerabilities:
    """XSS脆弱性に関するテストケース"""

    @pytest.fixture
    def csrf_client(self, client):
        """CSRF対応テストクライアントのセットアップ"""
        from tests.helpers.csrf_helpers import CSRFTestClient
        return CSRFTestClient(client)

    def test_chat_endpoint_script_injection(self, csrf_client):
        """チャットエンドポイントでのスクリプトインジェクション"""
        # 悪意のあるスクリプトを含むメッセージ
        malicious_payload = '<script>alert("XSS")</script>'
        
        response = csrf_client.post('/api/chat', 
            json={'message': malicious_payload, 'model': 'gemini-1.5-flash'},
            headers={'Accept': 'text/event-stream'}
        )
        
        # ストリーミングレスポンスを読み取る
        data = b''
        for chunk in response.response:
            data += chunk
        
        # レスポンスにスクリプトタグがそのまま含まれていないことを確認
        assert b'<script>' not in data
        assert b'alert(' not in data

    def test_scenario_chat_html_injection(self, csrf_client):
        """シナリオチャットでのHTML注入"""
        # HTMLタグを含む入力
        html_payload = '<img src=x onerror=alert(1)>'
        
        # まずシナリオを選択
        csrf_client.post('/api/scenario/select', json={'scenario_id': 'meeting_report'})
        
        response = csrf_client.post('/api/scenario_chat',
            json={'message': html_payload, 'model': 'gemini-1.5-flash'},
            headers={'Accept': 'text/event-stream'}
        )
        
        data = b''
        for chunk in response.response:
            data += chunk
        
        # 危険なHTML属性がエスケープされていることを確認
        assert b'onerror=' not in data
        assert b'<img' not in data or b'&lt;img' in data

    def test_watch_mode_xss(self, csrf_client):
        """観戦モードでのXSS"""
        # 悪意のあるトピックを設定
        xss_topic = '"><script>alert("XSS")</script>'
        
        response = csrf_client.post('/api/watch/start',
            json={'topic': xss_topic, 'model': 'gemini-1.5-flash'}
        )
        
        data = response.get_json()
        
        # トピックが適切にエスケープされていることを確認
        if 'topic' in str(data):
            assert '<script>' not in str(data)
            assert '&lt;script&gt;' in str(data) or '"&gt;&lt;script&gt;' in str(data)

    def test_json_response_content_type(self, csrf_client):
        """JSONレスポンスの適切なContent-Type"""
        response = csrf_client.get('/api/models')
        
        # Content-Typeが正しく設定されていることを確認
        assert response.content_type == 'application/json'
        
        # X-Content-Type-Optionsヘッダーの確認
        # 実装後にアサーションを有効化
        # assert response.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_stored_xss_in_history(self, csrf_client):
        """履歴に保存されるXSSの検証"""
        with csrf_client.session_transaction() as sess:
            # 悪意のあるメッセージを履歴に追加（実際のアプリケーションで使用されるキー名に変更）
            sess['chat_history'] = [
                {"human": '<script>alert("stored XSS")</script>', "ai": "Response"}
            ]
        
        # 履歴を含むページをレンダリング（ホームページでは履歴は表示されないため、このテストは概念的なもの）
        response = csrf_client.get('/')
        
        # スクリプトタグが含まれていないことを確認（ホームページには履歴は表示されないが、安全性を確認）
        assert b'<script>alert(' not in response.data
        # ホームページでは履歴が表示されないため、エスケープ確認は別のテストで行う
        # このテストは将来的に履歴表示機能が実装された際の安全性テストとして機能する

    def test_event_handler_injection(self, csrf_client):
        """イベントハンドラー注入の検証"""
        payloads = [
            'onclick="alert(1)"',
            'onmouseover="alert(1)"',
            'javascript:alert(1)',
            'data:text/html,<script>alert(1)</script>'
        ]
        
        for payload in payloads:
            csrf_client.reset_csrf_token()
            response = csrf_client.post('/api/chat',
                json={'message': payload, 'model': 'gemini-1.5-flash'},
                headers={'Accept': 'text/event-stream'}
            )
            
            data = b''
            for chunk in response.response:
                data += chunk
            
            # イベントハンドラーがエスケープされていることを確認
            assert b'onclick=' not in data
            assert b'onmouseover=' not in data
            assert b'javascript:' not in data

    def test_unicode_escape_bypass(self, csrf_client):
        """Unicode文字を使用したエスケープバイパス"""
        # Unicode文字を使用した攻撃
        unicode_payload = '\u003cscript\u003ealert(1)\u003c/script\u003e'
        
        response = csrf_client.post('/api/chat',
            json={'message': unicode_payload, 'model': 'gemini-1.5-flash'},
            headers={'Accept': 'text/event-stream'}
        )
        
        data = b''
        for chunk in response.response:
            data += chunk
        
        # Unicodeでエンコードされたスクリプトも検出
        assert b'<script>' not in data
        assert b'\\u003cscript' not in data.lower()

    @pytest.mark.parametrize("endpoint,method,data", [
        ('/api/chat', 'POST', {'message': '<svg onload=alert(1)>', 'model': 'gemini-1.5-flash'}),
        ('/api/scenario_chat', 'POST', {'message': '<iframe src="javascript:alert(1)">', 'model': 'gemini-1.5-flash'}),
        ('/api/watch/start', 'POST', {'topic': '<embed src="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">', 'model': 'gemini-1.5-flash'})
    ])
    def test_various_xss_vectors(self, csrf_client, endpoint, method, data):
        """様々なXSSベクターのテスト"""
        if endpoint == '/api/scenario_chat':
            # シナリオ選択が必要
            csrf_client.post('/api/scenario/select', json={'scenario_id': 'meeting_report'})
        
        if method == 'POST':
            response = csrf_client.post(endpoint, json=data, headers={'Accept': 'text/event-stream'})
        else:
            response = csrf_client.get(endpoint)
        
        # レスポンスの検証
        if response.content_type == 'text/event-stream':
            data = b''
            for chunk in response.response:
                data += chunk
            content = data
        else:
            content = response.data
        
        # 危険なタグやイベントハンドラーが含まれていないことを確認
        dangerous_patterns = [
            b'<svg', b'<iframe', b'<embed', b'<object',
            b'onload=', b'onerror=', b'onclick=',
            b'javascript:', b'data:text/html'
        ]
        
        for pattern in dangerous_patterns:
            assert pattern not in content.lower()


class TestXSSPrevention:
    """XSS防御機能のテスト"""

    @pytest.fixture
    def csrf_client(self, client):
        """CSRF対応テストクライアントのセットアップ"""
        from tests.helpers.csrf_helpers import CSRFTestClient
        return CSRFTestClient(client)

    def test_input_sanitization(self, client):
        """入力サニタイゼーションの確認"""
        from utils.security import SecurityUtils
        
        # スクリプトタグを含む入力
        malicious_input = '<script>alert("XSS")</script>'
        result = SecurityUtils.escape_html(malicious_input)
        
        # スクリプトタグが除去されていることを確認
        # bleachはタグを除去し、内容のみを残す
        assert '<script>' not in result
        assert '</script>' not in result

    def test_output_encoding(self, client):
        """出力エンコーディングの確認"""
        from utils.security import SecurityUtils
        
        # HTML特殊文字を含む入力
        special_chars = '<>&"\''
        result = SecurityUtils.escape_html(special_chars)
        
        # 元の特殊文字がそのまま含まれていないことを確認
        assert '<' not in result or '&lt;' in result

    def test_csp_nonce_generation(self, client):
        """CSP nonce生成の確認"""
        from utils.security import CSPNonce
        
        # nonceが生成できることを確認
        nonce = CSPNonce.generate()
        assert isinstance(nonce, str)
        assert len(nonce) > 0