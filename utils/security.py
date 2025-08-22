"""
セキュリティユーティリティ
XSS、CSRF、入力検証などのセキュリティ機能を提供
"""
import hashlib
import hmac
import re
import html
import json
import time
import logging
from typing import Any, Dict, Optional, Tuple
from functools import wraps
from flask import request, jsonify, session
import bleach

# ロガーの設定
logger = logging.getLogger(__name__)

class SecurityUtils:
    """セキュリティユーティリティクラス"""
    
    # XSS対策: 許可するHTMLタグ
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'code', 'pre']
    ALLOWED_ATTRIBUTES = {'code': ['class']}
    
    # 入力検証: 最大文字数
    MAX_MESSAGE_LENGTH = 10000
    MAX_MODEL_NAME_LENGTH = 50
    
    @staticmethod
    def escape_html(content: str) -> str:
        """
        HTMLエスケープ処理
        AI出力に含まれる可能性のある危険なHTMLを無害化
        """
        if not content:
            return ""
        
        # bleachを使用してHTMLをサニタイズ（これだけで十分）
        cleaned = bleach.clean(
            content,
            tags=SecurityUtils.ALLOWED_TAGS,
            attributes=SecurityUtils.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        # 二重エスケープを削除（データ破損を防ぐ）
        # cleaned = html.escape(cleaned, quote=True)  # 削除
        
        return cleaned
    
    @staticmethod
    def escape_json(data: Dict[str, Any]) -> str:
        """
        JSON用エスケープ処理
        SSEストリーミングで安全なJSON出力を保証
        """
        # ensure_ascii=Trueで非ASCII文字をエスケープ
        # これによりXSS攻撃を防ぐ
        return json.dumps(data, ensure_ascii=True, separators=(',', ':'))
    
    @staticmethod
    def validate_message(message: str) -> Tuple[bool, Optional[str]]:
        """
        メッセージの検証
        
        Returns:
            (有効かどうか, エラーメッセージ)
        """
        if not message:
            return False, "メッセージが空です"
        
        if len(message) > SecurityUtils.MAX_MESSAGE_LENGTH:
            return False, f"メッセージが長すぎます（最大{SecurityUtils.MAX_MESSAGE_LENGTH}文字）"
        
        # 危険なパターンのチェック
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'on\w+\s*=',  # onload=, onclick=など
            r'data:text/html',
            r'vbscript:',
            r'<iframe',
            r'<embed',
            r'<object'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False, "不正な内容が含まれています"
        
        return True, None
    
    @staticmethod
    def validate_model_name(model_name: str) -> bool:
        """
        モデル名の検証
        """
        if not model_name:
            return True  # 空の場合はデフォルトを使用
        
        if len(model_name) > SecurityUtils.MAX_MODEL_NAME_LENGTH:
            return False
        
        # gemini/プレフィックスを除去
        if model_name.startswith('gemini/'):
            model_name = model_name[7:]  # 'gemini/'の7文字を除去
        
        # 許可されたモデル名のパターン（スラッシュも許可）
        allowed_pattern = r'^[a-zA-Z0-9\-\./]+$'
        if not re.match(allowed_pattern, model_name):
            return False
        
        # 既知の有効なモデル名リスト（プレフィックスなし）
        valid_models = [
            'gemini-1.5-flash',
            'gemini-1.5-flash-latest',
            'gemini-1.5-flash-002',
            'gemini-1.5-flash-8b',
            'gemini-1.5-pro',
            'gemini-1.5-pro-latest',
            'gemini-1.5-pro-002',
            'gemini-1.0-pro',
            'gemini-2.0-flash',
            'gemini-2.0-flash-exp',
            'gemini-2.5-flash',
            'gemini-2.5-pro'
        ]
        
        # プレフィックスを除去したモデル名で検証
        return model_name in valid_models
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        入力テキストのサニタイズ
        
        Args:
            text: サニタイズするテキスト
        
        Returns:
            サニタイズされたテキスト
        """
        if not text:
            return ""
        
        # 基本的なサニタイズ（XSS対策はescape_htmlで行う）
        # 改行やタブを正規化
        text = text.strip()
        # 過度な空白を削減
        text = ' '.join(text.split())
        
        return text
    
    @staticmethod
    def validate_scenario_id(scenario_id: str) -> bool:
        """
        シナリオIDの検証
        
        Args:
            scenario_id: 検証するシナリオID
        
        Returns:
            有効ならTrue
        """
        if not scenario_id:
            return False
        
        # 許可されたパターン（英数字とアンダースコア）
        allowed_pattern = r'^scenario\d+$'
        return bool(re.match(allowed_pattern, scenario_id))
    
    @staticmethod
    def hash_user_id(user_id: str, salt: str = None) -> str:
        """
        SHA-256を使用した安全なハッシュ
        MD5から移行
        """
        if not salt:
            # 環境変数から取得（本番環境では必須）
            import os
            salt = os.getenv('AB_TEST_SALT', 'default-salt-change-in-production')
        
        # HMAC-SHA256を使用
        return hmac.new(
            salt.encode(),
            user_id.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def get_safe_error_message(error: Exception) -> str:
        """
        クライアント向けの安全なエラーメッセージを生成
        内部詳細を隠蔽し、セキュリティリスクを軽減
        
        Args:
            error: 発生した例外オブジェクト
        
        Returns:
            クライアント向けの一般的なエラーメッセージ
        """
        # 詳細なエラー情報はサーバーサイドログに記録
        logger.error(f"Internal error details: {str(error)}", exc_info=True)
        
        # エラータイプに基づいた一般的なメッセージを返す
        error_str = str(error).lower()
        
        # レート制限エラーの場合
        if any(keyword in error_str for keyword in ["rate limit", "quota", "429", "レート制限"]):
            return "システムが混雑しています"
        
        # 認証エラーの場合
        if any(keyword in error_str for keyword in ["authentication", "auth", "api key", "unauthorized"]):
            return "認証エラーが発生しました"
        
        # ネットワークエラーの場合
        if any(keyword in error_str for keyword in ["connection", "network", "timeout", "unreachable"]):
            return "ネットワークエラーが発生しました"
        
        # その他の場合は一般的なメッセージ
        return "システムエラーが発生しました"


class CSRFProtection:
    """CSRF保護機能"""
    
    @staticmethod
    def generate_token() -> str:
        """CSRFトークンの生成"""
        import secrets
        return secrets.token_hex(32)
    
    @staticmethod
    def validate_token(token: str) -> bool:
        """CSRFトークンの検証"""
        if not token:
            return False
        
        expected_token = session.get('csrf_token')
        if not expected_token:
            return False
        
        # タイミング攻撃を防ぐため、hmac.compare_digestを使用
        return hmac.compare_digest(token, expected_token)
    
    @staticmethod
    def require_csrf(f):
        """CSRF保護デコレータ"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # GETリクエストは除外
            if request.method == 'GET':
                return f(*args, **kwargs)
            
            # CSRFトークンの検証
            token = request.headers.get('X-CSRF-Token')
            if not token:
                # フォームデータからも取得を試みる
                token = request.form.get('csrf_token')
            
            if not CSRFProtection.validate_token(token):
                logger.warning(f"CSRF token validation failed for {request.path}")
                return jsonify({'error': 'CSRF token validation failed'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function


class RateLimiter:
    """レート制限機能"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Args:
            max_requests: ウィンドウ内の最大リクエスト数
            window_seconds: ウィンドウサイズ（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [(timestamp, count)]}
    
    def is_allowed(self, identifier: str) -> bool:
        """
        リクエストが許可されるかチェック
        
        Args:
            identifier: IPアドレスやユーザーIDなど
        """
        import time
        current_time = time.time()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # 古いエントリを削除
        self.requests[identifier] = [
            (t, c) for t, c in self.requests[identifier]
            if current_time - t < self.window_seconds
        ]
        
        # 現在のウィンドウ内のリクエスト数を計算
        total_requests = sum(c for _, c in self.requests[identifier])
        
        if total_requests >= self.max_requests:
            return False
        
        # リクエストを記録
        self.requests[identifier].append((current_time, 1))
        return True
    
    def rate_limit(self, max_requests: int = None, window_seconds: int = None):
        """レート制限デコレータ"""
        if max_requests:
            self.max_requests = max_requests
        if window_seconds:
            self.window_seconds = window_seconds
        
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # IPアドレスを識別子として使用
                identifier = request.remote_addr
                
                if not self.is_allowed(identifier):
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': self.window_seconds
                    }), 429
                
                return f(*args, **kwargs)
            
            return decorated_function
        
        return decorator


class CSRFToken:
    """CSRFトークン管理クラス"""
    
    @staticmethod
    def generate() -> str:
        """新しいCSRFトークンを生成"""
        import secrets
        return secrets.token_hex(16)
    
    @staticmethod
    def get_or_create(session_obj) -> str:
        """
        セッションから既存のトークンを取得、なければ生成
        
        Args:
            session_obj: Flaskのセッションオブジェクト
        
        Returns:
            CSRFトークン文字列
        """
        token = session_obj.get('csrf_token')
        if not token:
            token = CSRFToken.generate()
            session_obj['csrf_token'] = token
            session_obj['csrf_token_time'] = time.time()
        return token
    
    @staticmethod
    def validate(token: str, session_obj) -> bool:
        """
        トークンの妥当性を検証
        
        Args:
            token: 検証するトークン
            session_obj: Flaskのセッションオブジェクト
        
        Returns:
            有効ならTrue
        """
        if not token:
            return False
        
        expected_token = session_obj.get('csrf_token')
        if not expected_token:
            return False
        
        # タイミング攻撃を防ぐため、hmac.compare_digestを使用
        return hmac.compare_digest(token, expected_token)
    
    @staticmethod
    def refresh(session_obj) -> str:
        """
        新しいトークンを生成してセッションを更新
        
        Args:
            session_obj: Flaskのセッションオブジェクト
        
        Returns:
            新しいCSRFトークン
        """
        token = CSRFToken.generate()
        session_obj['csrf_token'] = token
        session_obj['csrf_token_time'] = time.time()
        return token
    
    @staticmethod
    def require_csrf(f):
        """
        CSRF保護デコレータ
        CSRFProtection.require_csrfのエイリアス
        """
        return CSRFProtection.require_csrf(f)


# グローバルインスタンス
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)