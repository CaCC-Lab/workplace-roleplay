"""セキュリティユーティリティ"""
from flask import Flask, Response, request, session
from typing import Optional
import secrets
import hashlib


class SecurityHeaders:
    """セキュリティヘッダーを設定するミドルウェア"""
    
    def __init__(self, app: Optional[Flask] = None):
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Flaskアプリケーションに登録"""
        app.after_request(self.set_security_headers)
    
    def set_security_headers(self, response: Response) -> Response:
        """セキュリティヘッダーを設定"""
        # XSS対策
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HTTPS強制（本番環境）
        if not response.headers.get("Strict-Transport-Security"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP（Content Security Policy）
        if not response.headers.get("Content-Security-Policy"):
            csp = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "img-src 'self' data: https:",
                "font-src 'self' https://cdn.jsdelivr.net",
                "connect-src 'self' wss: https:",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp)
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        
        return response


class CSRFMiddleware:
    """CSRF保護ミドルウェア"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Flaskアプリケーションに登録"""
        self.app = app
        
        # セッション設定の強化
        app.config.update(
            SESSION_COOKIE_SECURE=app.config.get("SESSION_COOKIE_SECURE", True),
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax"
        )
        
        # リクエスト前の処理
        app.before_request(self._before_request)
    
    def _before_request(self) -> Optional[Response]:
        """リクエスト前の処理"""
        # CSRFトークンの生成
        if "csrf_token" not in session:
            session["csrf_token"] = self._generate_csrf_token()
        
        # CSRFチェックが無効化されている場合はスキップ
        if not self.app.config.get("WTF_CSRF_ENABLED", True):
            return None
        
        # POSTリクエストの場合はCSRFチェック
        if request.method == "POST":
            # APIエンドポイントは除外（別の認証方式を使用）
            if request.path.startswith("/api/"):
                return None
            
            # CSRFトークンの検証
            token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not token or not self._validate_csrf_token(token):
                return Response("CSRF validation failed", status=403)
        
        return None
    
    def _generate_csrf_token(self) -> str:
        """CSRFトークンを生成"""
        return secrets.token_urlsafe(32)
    
    def _validate_csrf_token(self, token: str) -> bool:
        """CSRFトークンを検証"""
        return secrets.compare_digest(
            session.get("csrf_token", ""),
            token
        )


class PasswordHasher:
    """パスワードハッシュ化ユーティリティ"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """パスワードをハッシュ化"""
        # Werkzeugの代わりに標準ライブラリを使用
        salt = secrets.token_bytes(32)
        pwdhash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100000  # iterations
        )
        return salt.hex() + pwdhash.hex()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """パスワードを検証"""
        try:
            salt = bytes.fromhex(password_hash[:64])
            stored_hash = password_hash[64:]
            
            pwdhash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                100000
            )
            
            return secrets.compare_digest(
                stored_hash,
                pwdhash.hex()
            )
        except Exception:
            return False