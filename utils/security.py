"""
セキュリティ関連のユーティリティ関数
XSS対策、入力検証、出力エスケープ、CSRF対策など
"""
import html
import hmac
import json
import logging
import re
import secrets
import time
from functools import wraps
from typing import Any, Dict

from flask import request, session, jsonify, g
from markupsafe import escape

# ログ設定
logger = logging.getLogger(__name__)


class SecurityUtils:
    """セキュリティ関連のユーティリティクラス"""
    
    # 危険なHTMLタグのパターン
    DANGEROUS_TAGS = re.compile(
        r'<(?:script|iframe|object|embed|form|input|button|select|textarea|style|link|meta|svg|math)',
        re.IGNORECASE
    )
    
    # イベントハンドラーのパターン
    EVENT_HANDLERS = re.compile(
        r'\s*(?:on\w+|xmlns)\s*=',
        re.IGNORECASE
    )
    
    # 危険なプロトコル
    DANGEROUS_PROTOCOLS = re.compile(
        r'(?:javascript|data|vbscript|about|file):\s*',
        re.IGNORECASE
    )
    
    @staticmethod
    def escape_html(text: str) -> str:
        """HTMLエスケープを行う
        
        Args:
            text: エスケープする文字列
            
        Returns:
            エスケープされた文字列
        """
        if not isinstance(text, str):
            text = str(text)
        
        # 基本的なHTMLエスケープ
        escaped = html.escape(text, quote=True)
        
        # 追加のエスケープ（シングルクォート）
        escaped = escaped.replace("'", "&#x27;")
        
        # Unicode文字のエスケープ
        escaped = escaped.replace("\u003c", "&lt;")
        escaped = escaped.replace("\u003e", "&gt;")
        
        return escaped
    
    @staticmethod
    def sanitize_input(text: str, allow_basic_html: bool = False) -> str:
        """入力をサニタイズする
        
        Args:
            text: サニタイズする文字列
            allow_basic_html: 基本的なHTMLタグを許可するか
            
        Returns:
            サニタイズされた文字列
        """
        if not isinstance(text, str):
            return ""
        
        # 基本的なサニタイゼーション
        text = text.strip()
        
        # Null文字を除去
        text = text.replace('\x00', '')
        
        # 危険なタグを除去
        text = SecurityUtils.DANGEROUS_TAGS.sub('', text)
        
        # イベントハンドラーを除去
        text = SecurityUtils.EVENT_HANDLERS.sub('', text)
        
        # 危険なプロトコルを除去
        text = SecurityUtils.DANGEROUS_PROTOCOLS.sub('', text)
        
        if not allow_basic_html:
            # すべてのHTMLをエスケープ
            text = SecurityUtils.escape_html(text)
        
        return text
    
    @staticmethod
    def escape_json(data: Any) -> str:
        """JSON用の安全なエスケープ
        
        Args:
            data: JSONに変換するデータ
            
        Returns:
            安全にエスケープされたJSON文字列
        """
        # ensure_asciiをTrueにしてUnicode文字をエスケープ
        json_str = json.dumps(data, ensure_ascii=True)
        
        # HTMLコンテキストで使用する場合の追加エスケープ
        json_str = json_str.replace('</', '<\\/')
        json_str = json_str.replace('<script', '<\\script')
        json_str = json_str.replace('</script', '<\\/script')
        
        return json_str
    
    @staticmethod
    def validate_model_name(model_name: str) -> bool:
        """モデル名の検証
        
        Args:
            model_name: 検証するモデル名
            
        Returns:
            有効な場合True
        """
        # 許可されるモデル名のパターン（/も許可してGeminiのモデル名に対応）
        valid_pattern = re.compile(r'^[a-zA-Z0-9\-_./]+$')
        
        if not model_name or len(model_name) > 100:
            return False
        
        return bool(valid_pattern.match(model_name))
    
    @staticmethod
    def validate_scenario_id(scenario_id: str) -> bool:
        """シナリオIDの検証
        
        Args:
            scenario_id: 検証するシナリオID
            
        Returns:
            有効な場合True
        """
        # 英数字とアンダースコアのみ許可
        valid_pattern = re.compile(r'^[a-zA-Z0-9_]+$')
        
        if not scenario_id or len(scenario_id) > 50:
            return False
        
        return bool(valid_pattern.match(scenario_id))
    
    @staticmethod
    def sanitize_sse_data(content: str) -> str:
        """Server-Sent Events用のデータサニタイズ
        
        Args:
            content: サニタイズするコンテンツ
            
        Returns:
            SSE用にサニタイズされた文字列
        """
        # 改行をエスケープ
        content = content.replace('\r', '\\r')
        content = content.replace('\n', '\\n')
        
        # SSEのデータ区切り文字をエスケープ
        content = content.replace('\n\n', '\\n\\n')
        
        return content
    
    @staticmethod
    def get_safe_error_message(error: Exception) -> str:
        """エラーメッセージの安全な取得
        
        Args:
            error: エラーオブジェクト
            
        Returns:
            安全なエラーメッセージ
        """
        # エラーメッセージから機密情報を除去
        error_str = str(error)
        
        # APIキーやトークンのパターンを除去
        error_str = re.sub(r'(api[_-]?key|token|secret|password)[\s:=]*["\']?[\w\-]+["\']?', 
                          '[REDACTED]', error_str, flags=re.IGNORECASE)
        
        # ファイルパスを除去
        error_str = re.sub(r'[/\\][\w\-/\\]+\.(py|js|json|yaml|yml)', '[FILE]', error_str)
        
        # IPアドレスを除去
        error_str = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', error_str)
        
        return SecurityUtils.escape_html(error_str)


class CSPNonce:
    """Content Security Policy用のnonce生成とヘッダー作成"""
    
    # CSP実装フェーズ
    PHASE_REPORT_ONLY = 1  # Report-Onlyモード（違反を記録のみ）
    PHASE_MIXED = 2       # 部分的に厳格（移行期間）
    PHASE_STRICT = 3      # 完全に厳格
    
    @staticmethod
    def generate() -> str:
        """CSP用のnonceを生成
        
        Returns:
            str: 16バイトのランダムな16進数文字列
        """
        import secrets
        return secrets.token_hex(16)
    
    @staticmethod
    def create_csp_header(nonce: str, phase: int = 1, report_only: bool = True) -> str:
        """CSPヘッダーを作成
        
        Args:
            nonce: スクリプトとスタイル用のnonce値
            phase: CSP実装フェーズ（1-3）
            report_only: Report-Onlyモードかどうか
            
        Returns:
            str: Content-Security-Policyヘッダーの値
        """
        if phase == CSPNonce.PHASE_REPORT_ONLY:
            # Phase 1: 緩いポリシー（既存コードへの影響を最小化）
            return (
                f"default-src 'self'; "
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval' 'nonce-{nonce}' "
                f"https://cdn.jsdelivr.net https://www.googletagmanager.com https://www.google-analytics.com; "
                f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
                f"font-src 'self' https://fonts.gstatic.com data:; "
                f"img-src 'self' data: https:; "
                f"connect-src 'self' https://generativelanguage.googleapis.com https://www.google-analytics.com wss: ws:; "
                f"media-src 'self'; "
                f"object-src 'none'; "
                f"frame-ancestors 'none'; "
                f"base-uri 'self'; "
                f"form-action 'self'; "
                f"report-uri /api/csp-report"
            )
        
        elif phase == CSPNonce.PHASE_MIXED:
            # Phase 2: 中間的なポリシー（unsafe-evalを削除、unsafe-inlineは段階的に）
            return (
                f"default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' "
                f"https://cdn.jsdelivr.net https://www.googletagmanager.com https://www.google-analytics.com; "
                f"style-src 'self' 'unsafe-inline' 'nonce-{nonce}' "
                f"https://fonts.googleapis.com https://cdn.jsdelivr.net; "
                f"font-src 'self' https://fonts.gstatic.com data:; "
                f"img-src 'self' data: https:; "
                f"connect-src 'self' https://generativelanguage.googleapis.com https://www.google-analytics.com wss: ws:; "
                f"media-src 'self'; "
                f"object-src 'none'; "
                f"frame-ancestors 'none'; "
                f"base-uri 'self'; "
                f"form-action 'self'; "
                f"upgrade-insecure-requests; "
                f"report-uri /api/csp-report"
            )
        
        else:  # PHASE_STRICT
            # Phase 3: 厳格なポリシー
            return (
                f"default-src 'none'; "
                f"script-src 'self' 'nonce-{nonce}' 'strict-dynamic' "
                f"https://cdn.jsdelivr.net; "
                f"style-src 'self' 'nonce-{nonce}' "
                f"https://fonts.googleapis.com https://cdn.jsdelivr.net; "
                f"font-src 'self' https://fonts.gstatic.com; "
                f"img-src 'self' data:; "
                f"connect-src 'self' https://generativelanguage.googleapis.com; "
                f"media-src 'self'; "
                f"object-src 'none'; "
                f"frame-ancestors 'none'; "
                f"base-uri 'self'; "
                f"form-action 'self'; "
                f"upgrade-insecure-requests; "
                f"block-all-mixed-content; "
                f"report-uri /api/csp-report"
            )
    
    @staticmethod
    def inject_nonce_to_html(html: str, nonce: str) -> str:
        """HTMLにnonceを注入する
        
        Args:
            html: 元のHTML
            nonce: 注入するnonce値
            
        Returns:
            str: nonce属性が追加されたHTML
        """
        # <script>タグにnonceを追加
        html = re.sub(r'<script(?![^>]*\snonce=)', f'<script nonce="{nonce}"', html, flags=re.IGNORECASE)
        
        # インラインstyleタグにもnonceを追加（Phase 3で必要）
        html = re.sub(r'<style(?![^>]*\snonce=)', f'<style nonce="{nonce}"', html, flags=re.IGNORECASE)
        
        return html


class CSRFToken:
    """CSRF（Cross-Site Request Forgery）対策トークン管理クラス"""
    
    # CSRFトークンの設定
    TOKEN_LENGTH = 32  # 16バイト = 32文字の16進数
    TOKEN_LIFETIME = 3600  # 1時間（秒）
    SESSION_KEY = 'csrf_token'
    HEADER_NAME = 'X-CSRFToken'
    FORM_FIELD = 'csrf_token'
    
    @staticmethod
    def generate() -> str:
        """
        暗号学的に安全なCSRFトークンを生成
        
        Returns:
            str: 32文字の16進数文字列
        """
        return secrets.token_hex(CSRFToken.TOKEN_LENGTH // 2)
    
    @staticmethod
    def validate(token: str, session_data: Dict) -> bool:
        """
        CSRFトークンを検証
        
        Args:
            token: 検証するトークン
            session_data: セッションデータ
            
        Returns:
            bool: 有効な場合True
        """
        if not token or not isinstance(token, str):
            return False
        
        # トークンの形式検証
        if not CSRFToken._is_valid_format(token):
            return False
        
        # セッションからトークンを取得
        session_token_data = session_data.get(CSRFToken.SESSION_KEY)
        if not session_token_data:
            return False
        
        # 旧形式（文字列）との後方互換性
        if isinstance(session_token_data, str):
            # 旧形式の場合は期限チェックなし（後方互換性のため）
            return CSRFToken._secure_compare(token, session_token_data)
        
        # 新形式（辞書）の場合
        if isinstance(session_token_data, dict):
            stored_token = session_token_data.get('token')
            created_at = session_token_data.get('created_at')
            
            if not stored_token or created_at is None:
                return False
            
            # 有効期限チェック
            current_time = time.time()
            if current_time - created_at > CSRFToken.TOKEN_LIFETIME:
                return False
            
            # タイミング攻撃を防ぐため、必ず固定時間で比較
            return CSRFToken._secure_compare(token, stored_token)
        
        return False
    
    @staticmethod
    def _is_valid_format(token: str) -> bool:
        """
        トークンの形式が有効かチェック
        
        Args:
            token: チェックするトークン
            
        Returns:
            bool: 有効な形式の場合True
        """
        if len(token) != CSRFToken.TOKEN_LENGTH:
            return False
        
        # 16進数文字のみかチェック
        try:
            int(token, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def _secure_compare(a: str, b: str) -> bool:
        """
        タイミング攻撃を防ぐ安全な文字列比較
        
        Args:
            a: 比較する文字列1
            b: 比較する文字列2
            
        Returns:
            bool: 一致する場合True
        """
        # hmac.compare_digestを使用してタイミング攻撃を防ぐ
        return hmac.compare_digest(a, b)
    
    @staticmethod
    def refresh(session_data: Dict) -> str:
        """
        CSRFトークンを新しく生成してセッションに保存
        
        Args:
            session_data: セッションデータ
            
        Returns:
            str: 新しいCSRFトークン
        """
        new_token = CSRFToken.generate()
        # トークンと生成時刻を保存
        session_data[CSRFToken.SESSION_KEY] = {
            'token': new_token,
            'created_at': time.time()
        }
        return new_token
    
    @staticmethod
    def get_or_create(session_data: Dict) -> str:
        """
        セッションからCSRFトークンを取得、なければ作成
        
        Args:
            session_data: セッションデータ
            
        Returns:
            str: CSRFトークン
        """
        token_data = session_data.get(CSRFToken.SESSION_KEY)
        
        if not token_data:
            # トークンが存在しない場合は新規作成
            return CSRFToken.refresh(session_data)
        
        # 旧形式（文字列）の場合
        if isinstance(token_data, str):
            # 旧形式を新形式に移行
            return CSRFToken.refresh(session_data)
        
        # 新形式（辞書）の場合
        if isinstance(token_data, dict):
            token = token_data.get('token')
            created_at = token_data.get('created_at')
            
            if not token or created_at is None:
                return CSRFToken.refresh(session_data)
            
            # 有効期限チェック
            current_time = time.time()
            if current_time - created_at > CSRFToken.TOKEN_LIFETIME:
                # 期限切れの場合は再生成
                return CSRFToken.refresh(session_data)
            
            # トークンの形式チェック
            if not CSRFToken._is_valid_format(token):
                return CSRFToken.refresh(session_data)
            
            return token
        
        # 予期しない形式の場合は再生成
        return CSRFToken.refresh(session_data)
    
    @staticmethod
    def require_csrf(f):
        """
        CSRFトークン検証を必須とするデコレータ
        
        Args:
            f: デコレートする関数
            
        Returns:
            デコレートされた関数
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # GETリクエストとOPTIONSリクエストはCSRF検証を免除
            if request.method in ['GET', 'HEAD', 'OPTIONS']:
                return f(*args, **kwargs)
            
            # CSRFトークンを取得（ヘッダーまたはフォームから）
            token = request.headers.get(CSRFToken.HEADER_NAME)
            
            if not token:
                # フォームデータから取得を試行
                token = request.form.get(CSRFToken.FORM_FIELD)
            
            if not token:
                # JSONデータから取得を試行
                json_data = request.get_json(silent=True, force=True)
                if json_data and isinstance(json_data, dict):
                    token = json_data.get(CSRFToken.FORM_FIELD)
            
            # トークンが提供されていない場合
            if not token:
                logger.warning(
                    f"CSRF token missing for {request.method} {request.path} "
                    f"from IP {request.remote_addr}"
                )
                return jsonify({
                    'error': 'CSRFトークンが必要です',
                    'code': 'CSRF_TOKEN_MISSING'
                }), 403
            
            # トークンを検証
            if not CSRFToken.validate(token, session):
                logger.warning(
                    f"Invalid CSRF token for {request.method} {request.path} "
                    f"from IP {request.remote_addr}. Token: {token[:8]}..."
                )
                return jsonify({
                    'error': 'CSRFトークンが無効です',
                    'code': 'CSRF_TOKEN_INVALID'
                }), 403
            
            # 検証成功、リクエストをCSRF保護済みとしてマーク
            g.csrf_validated = True
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    @staticmethod
    def csrf_exempt(f):
        """
        CSRF検証を免除するデコレータ
        
        Args:
            f: デコレートする関数
            
        Returns:
            デコレートされた関数
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # CSRFチェックを免除としてマーク
            g.csrf_exempt = True
            return f(*args, **kwargs)
        
        return decorated_function


class CSRFMiddleware:
    """CSRF対策ミドルウェア"""
    
    def __init__(self, app=None):
        """
        CSRFミドルウェアを初期化
        
        Args:
            app: Flaskアプリケーションインスタンス
        """
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Flaskアプリケーションにミドルウェアを登録
        
        Args:
            app: Flaskアプリケーションインスタンス
        """
        # アプリケーション設定
        app.config.setdefault('CSRF_ENABLED', True)
        app.config.setdefault('CSRF_TIME_LIMIT', 3600)
        app.config.setdefault('CSRF_SECRET_KEY', None)
        
        # セッション設定の強化
        self._configure_session_security(app)
        
        # リクエスト前の処理
        app.before_request(self._before_request)
        
        # レスポンス後の処理
        app.after_request(self._after_request)
        
        # CSRFトークン取得エンドポイントを追加
        app.add_url_rule('/api/csrf-token', 'csrf_token', self._get_csrf_token, methods=['GET'])
    
    def _configure_session_security(self, app):
        """
        セッションのセキュリティ設定を強化
        
        Args:
            app: Flaskアプリケーションインスタンス
        """
        # SameSite Cookieの設定
        app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
        
        # HTTPSでのみCookieを送信（本番環境）
        if app.config.get('ENV') == 'production':
            app.config.setdefault('SESSION_COOKIE_SECURE', True)
        
        # XSS対策：JavaScriptからのCookieアクセスを防止
        app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
        
        # セッションの有効期限
        app.config.setdefault('PERMANENT_SESSION_LIFETIME', 1800)  # 30分
    
    def _before_request(self):
        """
        リクエスト前の処理
        """
        # CSRFトークンをセッションに追加（必要に応じて）
        if 'csrf_token' not in session:
            CSRFToken.get_or_create(session)
        
        # リクエスト情報をログに記録
        if request.method == 'POST':
            logger.debug(
                f"POST request to {request.path} from IP {request.remote_addr}"
            )
    
    def _after_request(self, response):
        """
        レスポンス後の処理
        
        Args:
            response: レスポンスオブジェクト
            
        Returns:
            レスポンスオブジェクト
        """
        # CSRFトークンをレスポンスヘッダーに追加
        if hasattr(g, 'csrf_validated') and g.csrf_validated:
            # 新しいトークンを生成してローテーション
            new_token = CSRFToken.refresh(session)
            response.headers['X-CSRF-Token'] = new_token
        
        return response
    
    def _get_csrf_token(self):
        """
        CSRFトークンを取得するAPIエンドポイント
        
        Returns:
            JSONレスポンス
        """
        token = CSRFToken.get_or_create(session)
        return jsonify({
            'csrf_token': token,
            'expires_in': CSRFToken.TOKEN_LIFETIME
        })