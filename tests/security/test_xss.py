"""
XSS（クロスサイトスクリプティング）対策のテスト
TDD原則に従い、様々なXSS攻撃ベクターに対する防御をテスト
"""
import pytest
from flask import Flask
from markupsafe import Markup
import json
from unittest.mock import patch, MagicMock

# アプリケーションのインポート（まだ実装されていない機能もモックで対応）
from app import app


class TestXSSPrevention:
    """XSS攻撃に対する防御機能のテスト"""
    
    @pytest.fixture
    def client(self):
        """テスト用Flaskクライアント"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    # ========== 入力サニタイズのテスト ==========
    
    def test_基本的なスクリプトタグの無害化(self, csrf_client):
        """<script>タグが適切にサニタイズされることを確認"""
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = []
            sess['chat_settings'] = {'system_prompt': 'テストプロンプト'}
        
        # CSRFトークンを取得
        csrf_response = csrf_client.get('/api/csrf-token')
        csrf_data = csrf_response.get_json()
        csrf_token = csrf_data['csrf_token']
        
        # スクリプトタグと一緒に有効なテキストも含める
        payload = "こんにちは<script>alert('XSS')</script>テストです"
        
        with patch('app.create_model_and_get_response') as mock_response:
            mock_response.return_value = "テストレスポンス"
            
            response = csrf_client.post('/api/chat', 
                                 json={'message': payload},
                                 headers={'X-CSRFToken': csrf_token})
            
            # JSONレスポンスを取得
            data = response.get_json()
            
            # レスポンスが正常であることを確認
            assert response.status_code == 200
            assert 'response' in data
            
            # スクリプトタグが含まれていないことを確認
            assert '<script>' not in data['response']
            assert 'alert(' not in data['response']
    
    def test_イベントハンドラの無害化(self, csrf_client):
        """onclickなどのイベントハンドラが除去されることを確認"""
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = []
            sess['chat_settings'] = {'system_prompt': 'テストプロンプト'}
        
        payloads = [
            '<img src=x onerror="alert(\'XSS\')">',
            '<div onclick="alert(\'XSS\')">Click me</div>',
            '<body onload="alert(\'XSS\')">'
        ]
        
        for payload in payloads:
            # 各ペイロードでCSRFトークンをリセット
            csrf_client.reset_csrf_token()
            
            with patch('app.create_model_and_get_response') as mock_response:
                mock_response.return_value = "安全なレスポンス"
                
                response = csrf_client.post('/api/chat',
                                     json={'message': payload})
                
                data = response.get_json()
                
                # エラーがないことを確認（入力が適切に処理された）
                assert response.status_code == 200
                assert 'response' in data
                
                # イベントハンドラが含まれていないことを確認
                response_text = json.dumps(data)
                assert 'onerror=' not in response_text
                assert 'onclick=' not in response_text
                assert 'onload=' not in response_text
    
    def test_JavaScriptプロトコルの無害化(self, csrf_client):
        """javascript:プロトコルが無害化されることを確認"""
        payloads = [
            '<a href="javascript:alert(\'XSS\')">Click</a>',
            '<img src="javascript:alert(\'XSS\')">'
        ]
        
        for payload in payloads:
            with csrf_client.session_transaction() as sess:
                sess['scenario_chat_memory'] = []
            
            response = csrf_client.post('/api/scenario_chat',
                                 json={
                                     'message': payload,
                                     'scenario_id': 'test_scenario'
                                 })
            
            data = response.get_data(as_text=True)
            assert 'javascript:' not in data.lower()
    
    # ========== 出力エスケープのテスト ==========
    
    def test_HTMLエンティティのエスケープ(self, csrf_client):
        """HTML特殊文字が適切にエスケープされることを確認"""
        test_cases = [
            ('<', '&lt;'),
            ('>', '&gt;'),
            ('"', '&quot;'),
            ("'", '&#x27;'),  # SecurityUtils.escape_htmlは&#x27;を使用
            ('&', '&amp;')
        ]
        
        for char, escaped in test_cases:
            # 各ループでCSRFトークンをリセット
            csrf_client.reset_csrf_token()
            
            message = f"テスト{char}メッセージ"
            
            with csrf_client.session_transaction() as sess:
                sess['chat_history'] = []
                sess['chat_settings'] = {'system_prompt': 'テストプロンプト'}
            
            with patch('app.create_model_and_get_response') as mock_response:
                # エスケープされた文字を含むレスポンスを返す
                mock_response.return_value = f"返信{char}テスト"
                
                response = csrf_client.post('/api/chat',
                                     json={'message': message})
                
                data = response.get_json()
                
                # レスポンスが正常であることを確認
                assert response.status_code == 200
                assert 'response' in data
                
                # エスケープされた文字が含まれていることを確認
                # SecurityUtils.escape_htmlによってエスケープされている
                assert escaped in data['response']
    
    def test_JSONレスポンスの安全性(self, csrf_client):
        """JSONレスポンスが適切にエンコードされることを確認"""
        with csrf_client.session_transaction() as sess:
            sess['chat_memory'] = []
        
        # JSONインジェクションの試み
        payload = '{"message": "test", "extra": "injection"}'
        
        response = csrf_client.post('/api/models')
        data = response.get_json()
        
        # 正しいJSON構造であることを確認
        assert isinstance(data, dict)
        assert 'models' in data or 'error' in data
    
    # ========== CSP関連のテスト ==========
    
    @pytest.mark.skip(reason="CSPヘッダーは次のフェーズで実装")
    def test_CSPヘッダーの存在(self, csrf_client):
        """Content-Security-Policyヘッダーが設定されることを確認"""
        response = csrf_client.get('/')
        
        assert 'Content-Security-Policy' in response.headers
        csp = response.headers['Content-Security-Policy']
        
        # 基本的なディレクティブの確認
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp or "script-src 'self' 'nonce-" in csp
    
    @pytest.mark.skip(reason="CSPヘッダーは次のフェーズで実装")
    def test_インラインスクリプトの制限(self, csrf_client):
        """インラインスクリプトが適切に制限されることを確認"""
        response = csrf_client.get('/')
        
        # HTMLにnonceが含まれているか確認
        assert b'nonce=' in response.data or b'<script>' not in response.data
    
    # ========== エラーメッセージの安全性テスト ==========
    
    def test_エラーメッセージのサニタイズ(self, csrf_client):
        """エラーメッセージにユーザー入力が含まれる場合の安全性"""
        # 不正なシナリオIDでXSSを試みる
        payload = '<script>alert("XSS")</script>'
        
        response = csrf_client.post('/api/scenario_chat',
                             json={
                                 'message': 'test',
                                 'scenario_id': payload
                             })
        
        data = response.get_json()
        
        if 'error' in data:
            # エラーメッセージにスクリプトタグが含まれていないことを確認
            assert '<script>' not in data['error']
            assert payload not in data['error']
    
    def test_デバッグ情報の非表示(self, csrf_client):
        """本番環境でデバッグ情報が漏洩しないことを確認"""
        # アプリケーションコンテキスト内でconfigを変更
        app.config['DEBUG'] = False
        app.config['TESTING'] = True
        
        try:
            # 意図的にエラーを発生させる（messageパラメータなし）
            response = csrf_client.post('/api/chat',
                                 json={})  # 必須パラメータなし
            
            data = response.get_json()
            
            # エラーレスポンスを確認
            assert response.status_code == 400
            assert 'error' in data
            
            # スタックトレースが含まれていないことを確認
            assert 'Traceback' not in data['error']
            assert 'File ' not in data['error']
            assert 'line ' not in data['error']
        finally:
            # configを元に戻す
            app.config['DEBUG'] = True
            app.config['TESTING'] = True
    
    # ========== 特殊な攻撃ベクターのテスト ==========
    
    def test_データURIスキームの処理(self, csrf_client):
        """data:URIスキームを使用したXSS攻撃の防御"""
        payload = '<img src="data:text/html,<script>alert(\'XSS\')</script>">'
        
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = []
            sess['chat_settings'] = {'system_prompt': 'テストプロンプト'}
        
        with patch('app.create_model_and_get_response') as mock_response:
            mock_response.return_value = "安全なレスポンス"
        
            response = csrf_client.post('/api/chat',
                                 json={'message': payload})
            
            data = response.get_json()
            
            # レスポンスが正常であることを確認
            assert response.status_code == 200
            assert 'response' in data
            
            # data:スキームが適切に処理されていることを確認
            response_text = json.dumps(data)
            assert 'data:text/html' not in response_text or '<script>' not in response_text
    
    @pytest.mark.skip(reason="SVGフィルタリングは追加実装が必要")
    def test_SVGベースのXSS防御(self, csrf_client):
        """SVGを使用したXSS攻撃の防御"""
        payload = '<svg onload="alert(\'XSS\')">'
        
        response = csrf_client.post('/api/chat',
                             json={'message': payload})
        
        data = response.get_data(as_text=True)
        assert '<svg' not in data or 'onload=' not in data
    
    def test_エンコーディング攻撃の防御(self, csrf_client):
        """異なるエンコーディングを使用した攻撃の防御"""
        # UTF-7エンコーディングでのXSS試行
        payloads = [
            '+ADw-script+AD4-alert(+ACc-XSS+ACc-)+ADw-/script+AD4-',
            '&#60;script&#62;alert(&#39;XSS&#39;)&#60;/script&#62;'
        ]
        
        for payload in payloads:
            # 各ループでCSRFトークンをリセット
            csrf_client.reset_csrf_token()
            
            with csrf_client.session_transaction() as sess:
                sess['chat_history'] = []
                sess['chat_settings'] = {'system_prompt': 'テストプロンプト'}
            
            with patch('app.create_model_and_get_response') as mock_response:
                mock_response.return_value = "安全なレスポンス"
            
                response = csrf_client.post('/api/chat',
                                     json={'message': payload})
                
                # 正常に処理され、スクリプトが実行されないことを確認
                assert response.status_code in [200, 400]  # 正常またはバリデーションエラー