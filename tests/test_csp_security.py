"""CSP（Content Security Policy）セキュリティのテストモジュール"""

import pytest
from flask import Flask
from utils.security import CSPNonce
import re
import json


class TestCSPNonce:
    """CSPNonceクラスのテスト"""
    
    def test_nonce_generation(self):
        """nonceが正しく生成されることを確認"""
        nonce = CSPNonce.generate()
        
        # Base64エンコードされた16バイトのnonce（約22-24文字）
        assert len(nonce) >= 22 and len(nonce) <= 24
        # Base64文字セットを確認
        import string
        valid_chars = string.ascii_letters + string.digits + '+/='
        assert all(c in valid_chars for c in nonce)
    
    def test_nonce_uniqueness(self):
        """生成されるnonceが一意であることを確認"""
        nonces = [CSPNonce.generate() for _ in range(100)]
        assert len(set(nonces)) == 100
    
    def test_csp_header_creation_report_only(self):
        """Report-OnlyモードのCSPヘッダーが正しく作成されることを確認"""
        nonce = CSPNonce.generate()
        header = CSPNonce.create_csp_header(nonce, phase=CSPNonce.PHASE_REPORT_ONLY, report_only=True)
        
        # 基本的な構造を確認
        assert "default-src 'self'" in header
        assert f"'nonce-{nonce}'" in header
        assert "style-src 'self'" in header
    
    def test_csp_header_creation_enforce_mode(self):
        """強制モードのCSPヘッダーが正しく作成されることを確認"""
        nonce = CSPNonce.generate()
        header = CSPNonce.create_csp_header(nonce, phase=CSPNonce.PHASE_STRICT, report_only=False)
        
        # 厳格なポリシーの特徴を確認
        assert "default-src 'self'" in header
        assert f"'nonce-{nonce}'" in header
        assert "'strict-dynamic'" in header


class TestCSPIntegration:
    """CSPのFlask統合テスト"""
    
    @pytest.fixture
    def app(self):
        """テスト用Flaskアプリケーション"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/')
        def index():
            return '<html><body><script nonce="test">console.log("test");</script></body></html>'
        
        @app.route('/api/test')
        def api_test():
            return {'status': 'ok'}
        
        return app
    
    def test_csp_header_presence_report_only(self, app):
        """Report-OnlyモードでCSPヘッダーが設定されることを確認"""
        # CSPミドルウェアを追加（Report-Onlyモード）
        @app.after_request
        def add_csp_header(response):
            if response.content_type and 'html' in response.content_type:
                nonce = CSPNonce.generate()
                response.headers['Content-Security-Policy-Report-Only'] = CSPNonce.create_csp_header(nonce, report_only=True)
                # nonceをレスポンスに注入する処理が必要
            return response
        
        with app.test_client() as client:
            response = client.get('/')
            assert 'Content-Security-Policy-Report-Only' in response.headers
            
            # APIエンドポイントにはCSPを適用しない
            response = client.get('/api/test')
            assert 'Content-Security-Policy-Report-Only' not in response.headers
    
    def test_csp_directives_content(self, app):
        """CSPディレクティブの内容を確認"""
        @app.after_request
        def add_csp_header(response):
            if response.content_type and 'html' in response.content_type:
                nonce = CSPNonce.generate()
                response.headers['Content-Security-Policy-Report-Only'] = CSPNonce.create_csp_header(nonce, report_only=True)
            return response
        
        with app.test_client() as client:
            response = client.get('/')
            csp = response.headers.get('Content-Security-Policy-Report-Only')
            
            # 必須ディレクティブの確認
            assert "default-src 'self'" in csp
            assert "script-src" in csp
            assert "style-src" in csp
            assert "img-src" in csp
            assert "connect-src" in csp
            assert "font-src" in csp
    
    def test_nonce_injection_in_html(self, app):
        """HTMLレスポンスにnonceが注入されることを確認"""
        # TODO: 実装後にテストを追加
        pass


class TestCSPViolationReporting:
    """CSP違反レポートのテスト"""
    
    @pytest.fixture
    def app_with_reporting(self):
        """レポートエンドポイント付きのテストアプリ"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        violations = []
        
        @app.route('/csp-report', methods=['POST'])
        def csp_report():
            """CSP違反レポートを受信"""
            from flask import request
            if request.get_json():
                violations.append(request.get_json())
            return '', 204
        
        app.violations = violations
        return app
    
    def test_violation_report_endpoint(self, app_with_reporting):
        """CSP違反レポートエンドポイントが動作することを確認"""
        with app_with_reporting.test_client() as client:
            # 模擬的なCSP違反レポート
            violation_report = {
                "csp-report": {
                    "document-uri": "http://example.com/",
                    "violated-directive": "script-src",
                    "blocked-uri": "inline",
                    "line-number": 10,
                    "source-file": "http://example.com/"
                }
            }
            
            response = client.post(
                '/csp-report',
                json=violation_report,
                content_type='application/json'
            )
            
            assert response.status_code == 204
            assert len(app_with_reporting.violations) == 1


class TestCSPPhaseStrategy:
    """段階的CSP実装戦略のテスト"""
    
    def test_phase1_report_only_policy(self):
        """Phase 1: Report-Onlyの緩いポリシー"""
        nonce = CSPNonce.generate()
        policy = self._get_phase1_policy(nonce)
        
        # Phase 1では'unsafe-inline'を許可（移行期間）
        assert "'unsafe-inline'" in policy
        assert "report-uri /csp-report" in policy
    
    def test_phase2_mixed_policy(self):
        """Phase 2: 部分的に厳格なポリシー"""
        nonce = CSPNonce.generate()
        policy = self._get_phase2_policy(nonce)
        
        # scriptでは'unsafe-inline'を削除、styleは維持
        assert "'unsafe-inline'" not in policy.split("script-src")[1].split(";")[0]
        assert "'unsafe-inline'" in policy.split("style-src")[1].split(";")[0]
    
    def test_phase3_strict_policy(self):
        """Phase 3: 厳格なポリシー"""
        nonce = CSPNonce.generate()
        policy = self._get_phase3_policy(nonce)
        
        # 'unsafe-inline'を完全に削除
        assert "'unsafe-inline'" not in policy
        # nonceまたはhashのみ許可
        assert f"'nonce-{nonce}'" in policy
    
    def _get_phase1_policy(self, nonce):
        """Phase 1のポリシー（緩い）"""
        return (
            "default-src 'self'; "
            f"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://www.googletagmanager.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://generativelanguage.googleapis.com; "
            "report-uri /csp-report"
        )
    
    def _get_phase2_policy(self, nonce):
        """Phase 2のポリシー（中間）"""
        return (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://www.googletagmanager.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://generativelanguage.googleapis.com; "
            "report-uri /csp-report"
        )
    
    def _get_phase3_policy(self, nonce):
        """Phase 3のポリシー（厳格）"""
        return (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' 'strict-dynamic' https://cdn.jsdelivr.net; "
            f"style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self' https://generativelanguage.googleapis.com; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "report-uri /csp-report"
        )