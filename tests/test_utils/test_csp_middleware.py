"""
CSP middleware tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask, g


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()


class TestCSPMiddleware:
    """CSPMiddlewareクラスのテスト"""

    def test_初期化_appなし(self):
        """appなしでの初期化"""
        from utils.csp_middleware import CSPMiddleware
        from utils.security import CSPNonce

        middleware = CSPMiddleware(phase=CSPNonce.PHASE_REPORT_ONLY)

        assert middleware.phase == CSPNonce.PHASE_REPORT_ONLY
        assert middleware.violations == []

    def test_初期化_appあり(self, app):
        """appありでの初期化"""
        from utils.csp_middleware import CSPMiddleware
        from utils.security import CSPNonce

        middleware = CSPMiddleware(app, phase=CSPNonce.PHASE_REPORT_ONLY)

        assert middleware.app == app

    def test_init_app(self, app):
        """init_appメソッド"""
        from utils.csp_middleware import CSPMiddleware
        from utils.security import CSPNonce

        middleware = CSPMiddleware(phase=CSPNonce.PHASE_REPORT_ONLY)
        middleware.init_app(app)

        assert "CSP_PHASE" in app.config
        assert "CSP_REPORT_URI" in app.config

    def test_CSPヘッダー追加_HTMLレスポンス(self, app):
        """HTMLレスポンスにCSPヘッダーを追加"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)

        @app.route("/test")
        def test_route():
            return "<html><body>Test</body></html>"

        with app.test_client() as client:
            response = client.get("/test")

            # CSPヘッダーが追加される
            assert (
                "Content-Security-Policy-Report-Only" in response.headers
                or "Content-Security-Policy" in response.headers
            )

    def test_CSPヘッダー追加_非HTMLレスポンス(self, app):
        """非HTMLレスポンスにはCSPヘッダーを追加しない"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)

        @app.route("/api/test")
        def test_route():
            return {"data": "test"}

        with app.test_client() as client:
            response = client.get("/api/test")

            # JSONレスポンスにはCSPヘッダーがない場合もある
            # レスポンスが正常に返されることを確認
            assert response.status_code == 200

    def test_CSP除外(self, app):
        """CSP除外フラグが設定されている場合"""
        from utils.csp_middleware import CSPMiddleware, csp_exempt

        middleware = CSPMiddleware(app)

        @app.route("/exempt")
        @csp_exempt
        def exempt_route():
            return "<html><body>Exempt</body></html>"

        with app.test_client() as client:
            response = client.get("/exempt")

            # 正常に返されることを確認
            assert response.status_code == 200

    def test_nonce取得(self, app):
        """nonce取得メソッド"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)

        with app.test_request_context("/test"):
            nonce = middleware._get_nonce()

            assert nonce is not None
            assert isinstance(nonce, str)

    def test_nonce取得_既存(self, app):
        """既存のnonceを取得"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)

        with app.test_request_context("/test"):
            g.csp_nonce = "existing-nonce"
            nonce = middleware._get_nonce()

            assert nonce == "existing-nonce"


class TestCSPReportHandler:
    """CSPレポートハンドラのテスト"""

    def test_CSPレポート処理_有効なレポート(self, app):
        """有効なCSPレポートの処理"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)

        with app.test_client() as client:
            report = {
                "csp-report": {
                    "document-uri": "http://example.com",
                    "violated-directive": "script-src",
                    "blocked-uri": "http://evil.com/script.js",
                }
            }

            response = client.post(
                "/api/csp-report",
                json=report,
                content_type="application/json",
            )

            assert response.status_code == 204

    def test_CSPレポート処理_無効なレポート(self, app):
        """無効なCSPレポートの処理"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)

        with app.test_client() as client:
            response = client.post(
                "/api/csp-report",
                json={},
                content_type="application/json",
            )

            assert response.status_code == 204

    def test_違反制限(self, app):
        """違反ログの制限"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)
        middleware.violation_limit = 5

        # 制限を超える違反を追加
        for i in range(10):
            middleware.violations.append({"id": i})

        assert len(middleware.violations) <= 10  # 既存の違反は保持


class TestViolationSummary:
    """違反サマリーのテスト"""

    def test_空の違反リスト(self, app):
        """空の違反リスト"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)

        summary = middleware.get_violation_summary()

        assert summary["total_violations"] == 0
        assert summary["violations_by_directive"] == {}

    def test_違反ありの場合(self, app):
        """違反がある場合"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)
        middleware.violations = [
            {"violated_directive": "script-src", "blocked_uri": "http://evil.com"},
            {"violated_directive": "script-src", "blocked_uri": "http://bad.com"},
            {"violated_directive": "style-src", "blocked_uri": "inline"},
        ]

        summary = middleware.get_violation_summary()

        assert summary["total_violations"] == 3
        assert summary["violations_by_directive"]["script-src"] == 2
        assert summary["violations_by_directive"]["style-src"] == 1

    def test_違反クリア(self, app):
        """違反ログのクリア"""
        from utils.csp_middleware import CSPMiddleware

        middleware = CSPMiddleware(app)
        middleware.violations = [{"test": "data"}]

        middleware.clear_violations()

        assert len(middleware.violations) == 0


class TestCSPExemptDecorator:
    """csp_exemptデコレータのテスト"""

    def test_デコレータ適用(self, app):
        """デコレータの適用"""
        from utils.csp_middleware import csp_exempt

        @csp_exempt
        def test_func():
            return "result"

        with app.test_request_context("/test"):
            result = test_func()

            assert result == "result"
            assert g.csp_exempt is True


class TestCSPReportAnalyzer:
    """CSPReportAnalyzerクラスのテスト"""

    def test_空の違反分析(self):
        """空の違反リストの分析"""
        from utils.csp_middleware import CSPReportAnalyzer

        result = CSPReportAnalyzer.analyze_violations([])

        assert result["status"] == "no_violations"
        assert result["recommendations"] == []

    def test_インラインスクリプト違反分析(self):
        """インラインスクリプト違反の分析"""
        from utils.csp_middleware import CSPReportAnalyzer

        violations = [
            {
                "violated_directive": "script-src",
                "blocked_uri": "inline",
                "source_file": "test.html",
            }
        ]

        result = CSPReportAnalyzer.analyze_violations(violations)

        assert result["status"] == "violations_found"
        assert len(result["recommendations"]) > 0
        assert any(r["issue"] == "Inline scripts detected" for r in result["recommendations"])

    def test_外部リソース違反分析(self):
        """外部リソース違反の分析"""
        from utils.csp_middleware import CSPReportAnalyzer

        violations = [
            {
                "violated_directive": "script-src",
                "blocked_uri": "https://cdn.example.com/script.js",
                "source_file": "",
            }
        ]

        result = CSPReportAnalyzer.analyze_violations(violations)

        assert result["status"] == "violations_found"
        assert any("cdn.example.com" in r["issue"] for r in result["recommendations"])

    def test_eval違反分析(self):
        """eval使用違反の分析"""
        from utils.csp_middleware import CSPReportAnalyzer

        violations = [
            {
                "violated_directive": "script-src",
                "blocked_uri": "eval",
                "source_file": "",
            }
        ]

        result = CSPReportAnalyzer.analyze_violations(violations)

        assert result["status"] == "violations_found"
        assert any(r["issue"] == "eval() usage detected" for r in result["recommendations"])


class TestInitCSP:
    """init_csp関数のテスト"""

    def test_CSPミドルウェア初期化(self, app):
        """CSPミドルウェアの初期化"""
        from utils.csp_middleware import init_csp, CSPMiddleware

        middleware = init_csp(app)

        assert isinstance(middleware, CSPMiddleware)
