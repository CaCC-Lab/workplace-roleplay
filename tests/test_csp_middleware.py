"""CSPミドルウェアのテストモジュール"""

import pytest
from flask import Flask, g, render_template_string
from utils.csp_middleware import CSPMiddleware, csp_exempt, CSPReportAnalyzer, init_csp
from utils.security import CSPNonce
import json


class TestCSPMiddleware:
    """CSPミドルウェアのテスト"""
    
    @pytest.fixture
    def app(self):
        """テスト用Flaskアプリケーション"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        # ルート定義
        @app.route('/')
        def index():
            return render_template_string('''
                <html>
                <head><title>Test</title></head>
                <body>
                    <script>console.log('test');</script>
                    <h1>Test Page</h1>
                </body>
                </html>
            ''')
        
        @app.route('/api/data')
        def api_data():
            return {'status': 'ok'}
        
        @app.route('/exempt')
        @csp_exempt
        def exempt_page():
            return '<html><body>Exempt from CSP</body></html>'
        
        return app
    
    def test_middleware_initialization(self, app):
        """ミドルウェアの初期化テスト"""
        csp = CSPMiddleware(app)
        
        assert app.config['CSP_PHASE'] == CSPNonce.PHASE_REPORT_ONLY
        assert app.config['CSP_REPORT_ONLY'] is True
        assert app.config['CSP_REPORT_URI'] == '/api/csp-report'
    
    def test_csp_header_added_to_html(self, app):
        """HTMLレスポンスにCSPヘッダーが追加されることを確認"""
        csp = CSPMiddleware(app)
        
        with app.test_client() as client:
            response = client.get('/')
            
            # Report-Onlyヘッダーが存在
            assert 'Content-Security-Policy-Report-Only' in response.headers
            
            # 基本的なディレクティブを確認
            csp_header = response.headers['Content-Security-Policy-Report-Only']
            assert "default-src 'self'" in csp_header
            assert "script-src" in csp_header
            assert "nonce-" in csp_header
            assert "report-uri /api/csp-report" in csp_header
    
    def test_csp_header_not_added_to_json(self, app):
        """JSONレスポンスにはCSPヘッダーが追加されないことを確認"""
        csp = CSPMiddleware(app)
        
        with app.test_client() as client:
            response = client.get('/api/data')
            
            assert 'Content-Security-Policy-Report-Only' not in response.headers
            assert 'Content-Security-Policy' not in response.headers
    
    def test_nonce_injection(self, app):
        """HTMLにnonceが注入されることを確認"""
        csp = CSPMiddleware(app)
        
        with app.test_client() as client:
            response = client.get('/')
            data = response.get_data(as_text=True)
            
            # nonceが注入されているか確認
            assert 'nonce=' in data
            assert '<script nonce="' in data
    
    def test_csp_exempt_decorator(self, app):
        """csp_exemptデコレータが機能することを確認"""
        csp = CSPMiddleware(app)
        
        with app.test_client() as client:
            # 通常のページ
            response = client.get('/')
            assert 'Content-Security-Policy-Report-Only' in response.headers
            
            # 除外されたページ
            response = client.get('/exempt')
            # exemptデコレータによってCSPヘッダーがバイパスされることを確認
            assert 'Content-Security-Policy-Report-Only' not in response.headers
    
    def test_phase_configuration(self, app):
        """異なるフェーズの設定テスト"""
        # Phase 2
        csp = CSPMiddleware(app, phase=CSPNonce.PHASE_MIXED)
        app.config['CSP_PHASE'] = CSPNonce.PHASE_MIXED
        
        with app.test_client() as client:
            response = client.get('/')
            csp_header = response.headers.get('Content-Security-Policy-Report-Only', '')
            
            # Phase 2では'unsafe-eval'が削除されている
            assert "'unsafe-eval'" not in csp_header
            # Phase 2では upgrade-insecure-requests が追加される
            if csp_header:  # ヘッダーが存在する場合のみチェック
                assert "upgrade-insecure-requests" in csp_header
    
    def test_csp_report_endpoint(self, app):
        """CSP違反レポートエンドポイントのテスト"""
        csp = CSPMiddleware(app)
        
        with app.test_client() as client:
            # CSP違反レポートを送信
            report = {
                "csp-report": {
                    "document-uri": "http://example.com/page",
                    "violated-directive": "script-src",
                    "blocked-uri": "inline",
                    "line-number": 10,
                    "source-file": "http://example.com/page"
                }
            }
            
            response = client.post(
                '/api/csp-report',
                json=report,
                content_type='application/csp-report'
            )
            
            assert response.status_code == 204
            assert len(csp.violations) == 1
            assert csp.violations[0]['violated_directive'] == 'script-src'
    
    def test_violation_summary(self, app):
        """違反サマリーの取得テスト"""
        csp = CSPMiddleware(app)
        
        # 複数の違反を追加
        violations = [
            {
                'timestamp': '2024-01-01T00:00:00',
                'violated_directive': 'script-src',
                'blocked_uri': 'inline',
                'document_uri': '/page1'
            },
            {
                'timestamp': '2024-01-01T00:01:00',
                'violated_directive': 'script-src',
                'blocked_uri': 'https://evil.com/script.js',
                'document_uri': '/page2'
            },
            {
                'timestamp': '2024-01-01T00:02:00',
                'violated_directive': 'style-src',
                'blocked_uri': 'inline',
                'document_uri': '/page3'
            }
        ]
        
        csp.violations.extend(violations)
        
        summary = csp.get_violation_summary()
        
        assert summary['total_violations'] == 3
        assert summary['violations_by_directive']['script-src'] == 2
        assert summary['violations_by_directive']['style-src'] == 1
        assert len(summary['common_blocked_uris']) > 0
    
    def test_memory_protection(self, app):
        """メモリ保護（違反数の制限）のテスト"""
        csp = CSPMiddleware(app)
        csp.violation_limit = 10  # テスト用に小さく設定
        
        # レポートエンドポイント経由で違反を追加
        with app.test_client() as client:
            for i in range(15):
                report = {
                    "csp-report": {
                        "document-uri": f"/page{i}",
                        "violated-directive": "script-src",
                        "blocked-uri": "inline"
                    }
                }
                client.post('/api/csp-report', json=report)
        
        # 制限内に収まっているか確認
        assert len(csp.violations) <= csp.violation_limit


class TestCSPReportAnalyzer:
    """CSPレポート分析ツールのテスト"""
    
    def test_analyze_no_violations(self):
        """違反がない場合の分析"""
        result = CSPReportAnalyzer.analyze_violations([])
        
        assert result['status'] == 'no_violations'
        assert result['recommendations'] == []
    
    def test_analyze_inline_script_violations(self):
        """インラインスクリプト違反の分析"""
        violations = [
            {
                'violated_directive': 'script-src',
                'blocked_uri': 'inline',
                'source_file': '/page1.html'
            },
            {
                'violated_directive': 'script-src',
                'blocked_uri': 'inline',
                'source_file': '/page2.html'
            }
        ]
        
        result = CSPReportAnalyzer.analyze_violations(violations)
        
        assert result['status'] == 'violations_found'
        assert result['total_violations'] == 2
        
        # インラインスクリプトの推奨事項を確認
        inline_rec = next(
            (r for r in result['recommendations'] if 'Inline scripts' in r['issue']),
            None
        )
        assert inline_rec is not None
        assert inline_rec['count'] == 2
        assert inline_rec['priority'] == 'high'
    
    def test_analyze_external_resource_violations(self):
        """外部リソース違反の分析"""
        violations = [
            {
                'violated_directive': 'script-src',
                'blocked_uri': 'https://cdn.example.com/script.js',
                'source_file': '/page1.html'
            },
            {
                'violated_directive': 'style-src',
                'blocked_uri': 'https://cdn.example.com/style.css',
                'source_file': '/page1.html'
            },
            {
                'violated_directive': 'font-src',
                'blocked_uri': 'https://fonts.example.com/font.woff',
                'source_file': '/page1.html'
            }
        ]
        
        result = CSPReportAnalyzer.analyze_violations(violations)
        
        # 外部リソースの推奨事項を確認
        external_recs = [
            r for r in result['recommendations'] 
            if 'External resource blocked' in r['issue']
        ]
        assert len(external_recs) == 2  # cdn.example.comとfonts.example.com
    
    def test_analyze_eval_violations(self):
        """eval使用違反の分析"""
        violations = [
            {
                'violated_directive': 'script-src',
                'blocked_uri': 'eval',
                'source_file': '/app.js'
            }
        ]
        
        result = CSPReportAnalyzer.analyze_violations(violations)
        
        # eval使用の推奨事項を確認
        eval_rec = next(
            (r for r in result['recommendations'] if 'eval()' in r['issue']),
            None
        )
        assert eval_rec is not None
        assert eval_rec['priority'] == 'high'


class TestCSPIntegration:
    """CSP統合テスト"""
    
    def test_init_csp_function(self):
        """init_csp関数のテスト"""
        app = Flask(__name__)
        
        csp = init_csp(app, phase=CSPNonce.PHASE_MIXED)
        
        assert isinstance(csp, CSPMiddleware)
        assert app.config['CSP_PHASE'] == CSPNonce.PHASE_MIXED
    
    def test_template_nonce_function(self):
        """テンプレート内でnonce関数が使えることを確認"""
        app = Flask(__name__)
        csp = CSPMiddleware(app)
        
        @app.route('/template')
        def template_test():
            return render_template_string('''
                <script nonce="{{ csp_nonce() }}">
                    console.log('Safe script');
                </script>
            ''')
        
        with app.test_client() as client:
            response = client.get('/template')
            data = response.get_data(as_text=True)
            
            # nonce値が含まれているか
            assert 'nonce="' in data
            assert len(data.split('nonce="')[1].split('"')[0]) == 32  # 16バイトの16進数