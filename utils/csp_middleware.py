"""
CSP（Content Security Policy）ミドルウェア
段階的なCSP実装をサポート
"""
from flask import Flask, Response, request, g
from typing import Optional, Callable, Any, Dict, List
from functools import wraps
import logging
from utils.security import CSPNonce
import json
from collections import defaultdict
from datetime import datetime


logger = logging.getLogger(__name__)


class CSPMiddleware:
    """CSPミドルウェアクラス"""

    def __init__(self, app: Optional[Flask] = None, phase: int = CSPNonce.PHASE_REPORT_ONLY):
        """
        Args:
            app: Flaskアプリケーション
            phase: CSP実装フェーズ（1-3）
        """
        self.phase = phase
        self.violations: List[Dict[str, Any]] = []
        self.violation_limit = 1000  # メモリ保護のため

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Flaskアプリケーションに初期化"""
        app.config.setdefault("CSP_PHASE", self.phase)
        app.config.setdefault("CSP_REPORT_ONLY", self.phase == CSPNonce.PHASE_REPORT_ONLY)
        app.config.setdefault("CSP_REPORT_URI", "/api/csp-report")

        # CSPレポートエンドポイントを登録
        app.add_url_rule(app.config["CSP_REPORT_URI"], "csp_report", self._handle_csp_report, methods=["POST"])

        # レスポンス処理フックを登録
        app.after_request(self._add_csp_header)

        # テンプレート関数を登録
        app.jinja_env.globals["csp_nonce"] = self._get_nonce

        self.app = app

    def _add_csp_header(self, response: Response) -> Response:
        """CSPヘッダーを追加"""
        # CSP除外チェック
        if hasattr(g, "csp_exempt") and g.csp_exempt:
            return response

        # HTMLレスポンスのみに適用
        if not response.content_type or "html" not in response.content_type:
            return response

        # nonceを生成
        nonce = CSPNonce.generate()
        g.csp_nonce = nonce

        # CSPヘッダーを作成
        phase = self.app.config.get("CSP_PHASE", CSPNonce.PHASE_REPORT_ONLY)
        report_only = self.app.config.get("CSP_REPORT_ONLY", True)

        csp_header = CSPNonce.create_csp_header(nonce, phase, report_only)

        # ヘッダー名を決定
        header_name = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"
        response.headers[header_name] = csp_header

        # HTMLにnonceを注入（オプション）
        if response.is_streamed:
            # ストリーミングレスポンスの場合はスキップ
            return response

        try:
            # レスポンスデータを取得
            data = response.get_data(as_text=True)

            # nonceを注入
            data = CSPNonce.inject_nonce_to_html(data, nonce)

            # データを設定
            response.set_data(data)
        except Exception as e:
            logger.error(f"Failed to inject CSP nonce: {e}")

        return response

    def _get_nonce(self) -> str:
        """テンプレート用のnonce取得関数"""
        if not hasattr(g, "csp_nonce"):
            g.csp_nonce = CSPNonce.generate()
        return g.csp_nonce

    def _handle_csp_report(self):
        """CSP違反レポートを処理"""
        try:
            # レポートを解析
            report_data = request.get_json(force=True)

            if not report_data or "csp-report" not in report_data:
                return "", 204

            csp_report = report_data["csp-report"]

            # 重要な情報を抽出
            violation = {
                "timestamp": datetime.utcnow().isoformat(),
                "document_uri": csp_report.get("document-uri", ""),
                "violated_directive": csp_report.get("violated-directive", ""),
                "blocked_uri": csp_report.get("blocked-uri", ""),
                "line_number": csp_report.get("line-number", 0),
                "column_number": csp_report.get("column-number", 0),
                "source_file": csp_report.get("source-file", ""),
                "status_code": csp_report.get("status-code", 0),
                "script_sample": csp_report.get("script-sample", ""),
                "user_agent": request.headers.get("User-Agent", ""),
            }

            # メモリ保護：制限に達している場合は最古のものを削除
            if len(self.violations) >= self.violation_limit:
                # 最古の違反を削除してスペースを確保
                self.violations.pop(0)

            self.violations.append(violation)

            # ログに記録
            logger.warning(f"CSP Violation: {violation['violated_directive']} - {violation['blocked_uri']}")

            # 開発環境では詳細をログ
            if self.app.debug:
                logger.debug(f"CSP Report Details: {json.dumps(violation, indent=2)}")

            return "", 204

        except Exception as e:
            logger.error(f"Error processing CSP report: {e}")
            return "", 204

    def get_violation_summary(self) -> Dict[str, Any]:
        """違反のサマリーを取得"""
        if not self.violations:
            return {
                "total_violations": 0,
                "violations_by_directive": {},
                "common_blocked_uris": [],
                "recent_violations": [],
            }

        # ディレクティブ別の集計
        by_directive = defaultdict(int)
        blocked_uris = defaultdict(int)

        for violation in self.violations:
            by_directive[violation["violated_directive"]] += 1
            if violation["blocked_uri"]:
                blocked_uris[violation["blocked_uri"]] += 1

        # 最も多いブロックURI
        common_blocked = sorted(blocked_uris.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_violations": len(self.violations),
            "violations_by_directive": dict(by_directive),
            "common_blocked_uris": common_blocked,
            "recent_violations": self.violations[-10:],  # 最新10件
        }

    def clear_violations(self):
        """違反ログをクリア"""
        self.violations.clear()


def csp_exempt(f: Callable) -> Callable:
    """CSPを適用しないデコレータ"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.csp_exempt = True
        return f(*args, **kwargs)

    return decorated_function


class CSPReportAnalyzer:
    """CSP違反レポートの分析ツール"""

    @staticmethod
    def analyze_violations(violations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """違反を分析して改善提案を生成"""
        if not violations:
            return {"status": "no_violations", "recommendations": []}

        recommendations = []

        # インラインスクリプトの違反をチェック
        inline_violations = [
            v for v in violations if v["blocked_uri"] == "inline" and "script-src" in v["violated_directive"]
        ]

        if inline_violations:
            recommendations.append(
                {
                    "issue": "Inline scripts detected",
                    "count": len(inline_violations),
                    "recommendation": "Move inline scripts to external files or use nonce attributes",
                    "priority": "high",
                    "affected_files": list(set(v["source_file"] for v in inline_violations if v["source_file"])),
                }
            )

        # 外部リソースの違反をチェック
        external_violations = [
            v for v in violations if v["blocked_uri"] and v["blocked_uri"] != "inline" and v["blocked_uri"] != "eval"
        ]

        if external_violations:
            # ドメイン別に集計
            domains = defaultdict(int)
            for v in external_violations:
                if v["blocked_uri"].startswith(("http://", "https://")):
                    from urllib.parse import urlparse

                    domain = urlparse(v["blocked_uri"]).netloc
                    domains[domain] += 1

            for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
                recommendations.append(
                    {
                        "issue": f"External resource blocked: {domain}",
                        "count": count,
                        "recommendation": f"Add {domain} to the appropriate CSP directive",
                        "priority": "medium",
                    }
                )

        # eval使用の違反
        eval_violations = [v for v in violations if v["blocked_uri"] == "eval"]

        if eval_violations:
            recommendations.append(
                {
                    "issue": "eval() usage detected",
                    "count": len(eval_violations),
                    "recommendation": "Remove eval() usage and refactor code",
                    "priority": "high",
                }
            )

        return {"status": "violations_found", "total_violations": len(violations), "recommendations": recommendations}


# Flask拡張として使用する場合の便利な関数
def init_csp(app: Flask, phase: int = CSPNonce.PHASE_REPORT_ONLY) -> CSPMiddleware:
    """CSPミドルウェアを初期化"""
    return CSPMiddleware(app, phase)
