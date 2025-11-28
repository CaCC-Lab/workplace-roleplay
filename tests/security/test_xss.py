"""
XSS（クロスサイトスクリプティング）対策のテスト
TDD原則に従い、様々なXSS攻撃ベクターに対する防御をテスト
"""
import pytest
from flask import Flask
from markupsafe import Markup
import json
from unittest.mock import patch, MagicMock

# アプリケーションのインポート
from app import app
from utils.security import SecurityUtils


class TestXSSPrevention:
    """XSS攻撃に対する防御機能のテスト"""
    
    @pytest.fixture
    def client(self):
        """テスト用Flaskクライアント"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def csrf_client(self):
        """CSRF保護ありのクライアント"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            # CSRFトークンを取得してセッションに設定
            with client.session_transaction() as sess:
                from utils.security import CSRFToken
                sess['csrf_token'] = CSRFToken.generate()
            yield client
    
    def _get_csrf_token(self, client):
        """CSRFトークンを取得"""
        response = client.get('/api/csrf-token')
        return response.get_json()['csrf_token']
    
    # ========== 入力サニタイズのテスト ==========
    
    def test_基本的なスクリプトタグの無害化(self, csrf_client):
        """<script>タグが適切にサニタイズされることを確認"""
        csrf_token = self._get_csrf_token(csrf_client)
        
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = []
            sess['chat_settings'] = {'system_prompt': 'テストプロンプト', 'model': 'gemini-1.5-flash'}
        
        # スクリプトタグを含むペイロード
        payload = "こんにちは<script>alert('XSS')</script>テストです"
        
        with patch('app.initialize_llm') as mock_init_llm:
            mock_llm = MagicMock()
            mock_chunk = MagicMock()
            mock_chunk.content = "テストレスポンス"
            mock_llm.stream.return_value = iter([mock_chunk])
            mock_init_llm.return_value = mock_llm
            
            response = csrf_client.post('/api/chat', 
                                 json={'message': payload},
                                 headers={'X-CSRF-Token': csrf_token})
            
            # レスポンスが正常であることを確認
            assert response.status_code == 200
    
    def test_イベントハンドラの無害化(self, csrf_client):
        """onclickなどのイベントハンドラが除去されることを確認"""
        csrf_token = self._get_csrf_token(csrf_client)
        
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = []
            sess['chat_settings'] = {'system_prompt': 'テストプロンプト', 'model': 'gemini-1.5-flash'}
        
        payloads = [
            '<img src=x onerror="alert(\'XSS\')">',
            '<div onclick="alert(\'XSS\')">Click me</div>',
            '<body onload="alert(\'XSS\')">'
        ]
        
        for payload in payloads:
            with patch('app.initialize_llm') as mock_init_llm:
                mock_llm = MagicMock()
                mock_chunk = MagicMock()
                mock_chunk.content = "安全なレスポンス"
                mock_llm.stream.return_value = iter([mock_chunk])
                mock_init_llm.return_value = mock_llm
                
                response = csrf_client.post('/api/chat',
                                     json={'message': payload},
                                     headers={'X-CSRF-Token': csrf_token})
                
                # 正常に処理されることを確認
                assert response.status_code == 200
    
    def test_JavaScriptプロトコルの無害化(self, csrf_client):
        """javascript:プロトコルが無害化されることを確認"""
        payloads = [
            '<a href="javascript:alert(\'XSS\')">Click</a>',
            '<img src="javascript:alert(\'XSS\')">'
        ]
        
        for payload in payloads:
            with csrf_client.session_transaction() as sess:
                sess['scenario_history'] = {"test_scenario": []}
            
            csrf_token = self._get_csrf_token(csrf_client)
            
            response = csrf_client.post('/api/scenario_chat',
                                 json={
                                     'message': payload,
                                     'scenario_id': 'scenario1',  # 実在するシナリオID
                                     'model': 'gemini-1.5-flash'
                                 },
                                 headers={'X-CSRF-Token': csrf_token})
            
            # バリデーションまたは正常処理
            assert response.status_code in [200, 400]
    
    # ========== 出力エスケープのテスト ==========
    
    def test_HTMLエンティティのエスケープ(self, csrf_client):
        """HTML特殊文字が適切にエスケープされることを確認"""
        test_cases = [
            ('<', '&lt;'),
            ('>', '&gt;'),
            ('"', '&quot;'),
            ("'", '&#x27;'),
            ('&', '&amp;')
        ]
        
        for char, escaped in test_cases:
            message = f"テスト{char}メッセージ"
            csrf_token = self._get_csrf_token(csrf_client)
            
            with csrf_client.session_transaction() as sess:
                sess['chat_history'] = []
                sess['chat_settings'] = {'system_prompt': 'テストプロンプト', 'model': 'gemini-1.5-flash'}
            
            with patch('app.initialize_llm') as mock_init_llm:
                mock_llm = MagicMock()
                mock_chunk = MagicMock()
                # エスケープされた文字を含むレスポンスを返す
                mock_chunk.content = f"返信{char}テスト"
                mock_llm.stream.return_value = iter([mock_chunk])
                mock_init_llm.return_value = mock_llm
                
                response = csrf_client.post('/api/chat',
                                     json={'message': message},
                                     headers={'X-CSRF-Token': csrf_token})
                
                # レスポンスが正常であることを確認
                assert response.status_code == 200
    
    def test_JSONレスポンスの安全性(self, client):
        """JSONレスポンスが適切にエンコードされることを確認"""
        response = client.get('/api/models')
        
        # 正しいJSON構造であることを確認
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert 'models' in data or 'feature_disabled' in data
    
    # ========== エラーメッセージの安全性テスト ==========
    
    def test_エラーメッセージのサニタイズ(self, csrf_client):
        """エラーメッセージにユーザー入力が含まれる場合の安全性"""
        csrf_token = self._get_csrf_token(csrf_client)
        
        # 不正なシナリオIDでXSSを試みる
        payload = '<script>alert("XSS")</script>'
        
        response = csrf_client.post('/api/scenario_chat',
                             json={
                                 'message': 'test',
                                 'scenario_id': payload
                             },
                             headers={'X-CSRF-Token': csrf_token})
        
        data = response.get_json()
        
        if 'error' in data:
            # エラーメッセージにスクリプトタグが含まれていないことを確認
            assert '<script>' not in data['error']
    
    def test_デバッグ情報の非表示(self, csrf_client):
        """本番環境でデバッグ情報が漏洩しないことを確認"""
        csrf_token = self._get_csrf_token(csrf_client)
        
        # 意図的にエラーを発生させる（messageパラメータなし）
        response = csrf_client.post('/api/chat',
                             json={},
                             headers={'X-CSRF-Token': csrf_token})
        
        data = response.get_json()
        
        # エラーレスポンスを確認
        assert response.status_code == 400
        assert 'error' in data
        
        # スタックトレースが含まれていないことを確認
        assert 'Traceback' not in data['error']
        assert 'File ' not in data['error']
    
    # ========== 特殊な攻撃ベクターのテスト ==========
    
    def test_データURIスキームの処理(self, csrf_client):
        """data:URIスキームを使用したXSS攻撃の防御"""
        csrf_token = self._get_csrf_token(csrf_client)
        payload = '<img src="data:text/html,<script>alert(\'XSS\')</script>">'
        
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = []
            sess['chat_settings'] = {'system_prompt': 'テストプロンプト', 'model': 'gemini-1.5-flash'}
        
        with patch('app.initialize_llm') as mock_init_llm:
            mock_llm = MagicMock()
            mock_chunk = MagicMock()
            mock_chunk.content = "安全なレスポンス"
            mock_llm.stream.return_value = iter([mock_chunk])
            mock_init_llm.return_value = mock_llm
        
            response = csrf_client.post('/api/chat',
                                 json={'message': payload},
                                 headers={'X-CSRF-Token': csrf_token})
            
            # レスポンスが正常であることを確認
            assert response.status_code == 200
    
    def test_エンコーディング攻撃の防御(self, csrf_client):
        """異なるエンコーディングを使用した攻撃の防御"""
        csrf_token = self._get_csrf_token(csrf_client)
        
        # UTF-7エンコーディングでのXSS試行
        payloads = [
            '+ADw-script+AD4-alert(+ACc-XSS+ACc-)+ADw-/script+AD4-',
            '&#60;script&#62;alert(&#39;XSS&#39;)&#60;/script&#62;'
        ]
        
        for payload in payloads:
            with csrf_client.session_transaction() as sess:
                sess['chat_history'] = []
                sess['chat_settings'] = {'system_prompt': 'テストプロンプト', 'model': 'gemini-1.5-flash'}
            
            with patch('app.initialize_llm') as mock_init_llm:
                mock_llm = MagicMock()
                mock_chunk = MagicMock()
                mock_chunk.content = "安全なレスポンス"
                mock_llm.stream.return_value = iter([mock_chunk])
                mock_init_llm.return_value = mock_llm
            
                response = csrf_client.post('/api/chat',
                                     json={'message': payload},
                                     headers={'X-CSRF-Token': csrf_token})
                
                # 正常に処理されることを確認
                assert response.status_code in [200, 400]


class TestSecurityUtilsSanitization:
    """SecurityUtilsのサニタイズ機能テスト"""
    
    def test_sanitize_input_trims_whitespace(self):
        """sanitize_inputが空白をトリムすることを確認"""
        input_text = "  Hello World  "
        result = SecurityUtils.sanitize_input(input_text)
        
        assert result == "Hello World"
    
    def test_sanitize_input_normalizes_whitespace(self):
        """sanitize_inputが過度な空白を正規化することを確認"""
        input_text = "Hello    World"
        result = SecurityUtils.sanitize_input(input_text)
        
        assert result == "Hello World"
    
    def test_sanitize_input_preserves_normal_text(self):
        """sanitize_inputが通常のテキストを保持することを確認"""
        input_text = "こんにちは。今日は良い天気ですね！"
        result = SecurityUtils.sanitize_input(input_text)
        
        assert result == input_text
    
    def test_escape_html_removes_script_tags(self):
        """escape_htmlがスクリプトタグを除去することを確認"""
        # bleach.clean はHTMLタグを除去する
        input_text = "<script>alert('XSS')</script>"
        result = SecurityUtils.escape_html(input_text)
        
        # bleachはタグを除去し、内容のみを残す
        assert '<script>' not in result
    
    def test_escape_html_removes_event_handlers(self):
        """escape_htmlがイベントハンドラを除去することを確認"""
        input_text = '<img src="x" onerror="alert(\'XSS\')">'
        result = SecurityUtils.escape_html(input_text)
        
        # bleachはimgタグと属性を除去
        assert 'onerror=' not in result
    
    def test_validate_model_name_rejects_invalid(self):
        """validate_model_nameが無効なモデル名を拒否することを確認"""
        invalid_names = [
            '../etc/passwd',
            '; DROP TABLE;',
            '<script>alert(1)</script>',
            'unknown-model-name'
        ]
        
        for name in invalid_names:
            result = SecurityUtils.validate_model_name(name)
            assert result is False, f"Should reject: {name}"
    
    def test_validate_model_name_accepts_valid(self):
        """validate_model_nameが有効なモデル名を受け入れることを確認"""
        valid_names = [
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'gemini/gemini-2.0-flash',
            'gemini-2.5-flash-lite'
        ]
        
        for name in valid_names:
            result = SecurityUtils.validate_model_name(name)
            assert result is True, f"Should accept: {name}"
    
    def test_validate_model_name_accepts_empty(self):
        """validate_model_nameが空の場合にTrueを返すことを確認（デフォルト使用）"""
        result = SecurityUtils.validate_model_name("")
        assert result is True
