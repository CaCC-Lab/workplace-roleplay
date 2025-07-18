#!/usr/bin/env python3
"""
セキュリティユーティリティモジュール

入力検証、サニタイゼーション、レート制限機能を提供
"""
import re
import html
import json
import time
from functools import wraps
from flask import request, jsonify, session
from collections import defaultdict


class InputValidator:
    """入力検証クラス"""
    
    # 設定値
    MAX_MESSAGE_LENGTH = 5000  # メッセージの最大長
    MIN_MESSAGE_LENGTH = 1     # メッセージの最小長
    
    # 危険なパターン
    XSS_PATTERNS = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe.*?>',
        r'<object.*?>',
        r'<embed.*?>',
        r'<link.*?>',
        r'<meta.*?>',
        r'alert\s*\(',
        r'eval\s*\(',
        r'document\.',
        r'window\.',
    ]
    
    SQL_INJECTION_PATTERNS = [
        r';\s*(drop|delete|insert|update|create|alter|exec|execute)',
        r'union\s+select',
        r'--\s*$',
        r'/\*.*\*/',
        r'@@\w+',
        r'xp_\w+',
        r'sp_\w+',
    ]
    
    @staticmethod
    def sanitize_html(text):
        """HTMLエスケープによるXSS対策"""
        if not isinstance(text, str):
            return text
        
        # HTMLエスケープ
        sanitized = html.escape(text)
        
        # 危険なパターンの除去
        for pattern in InputValidator.XSS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.MULTILINE)
        
        return sanitized
    
    @staticmethod
    def sanitize_sql(text):
        """SQLインジェクション対策"""
        if not isinstance(text, str):
            return text
        
        # 危険なSQLパターンの除去
        sanitized = text
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.MULTILINE)
        
        return sanitized
    
    @staticmethod
    def validate_message_length(message):
        """メッセージ長の検証"""
        if not isinstance(message, str):
            return False, "Message must be a string"
        
        if len(message) < InputValidator.MIN_MESSAGE_LENGTH:
            return False, "Message cannot be empty"
        
        if len(message) > InputValidator.MAX_MESSAGE_LENGTH:
            return False, f"Message too long (max {InputValidator.MAX_MESSAGE_LENGTH} characters)"
        
        return True, None
    
    @staticmethod
    def validate_json_input(data):
        """JSON入力の検証"""
        try:
            if isinstance(data, str):
                parsed_data = json.loads(data)
            else:
                parsed_data = data
            
            # 必須フィールドの確認
            if 'message' not in parsed_data:
                return False, "Missing required field: message", None
            
            return True, None, parsed_data
        
        except json.JSONDecodeError:
            return False, "Invalid JSON", None
        except Exception as e:
            return False, f"Invalid input: {str(e)}", None
    
    @staticmethod
    def sanitize_input(message):
        """包括的な入力サニタイゼーション"""
        # HTMLエスケープ
        sanitized = InputValidator.sanitize_html(message)
        
        # SQLインジェクション対策
        sanitized = InputValidator.sanitize_sql(sanitized)
        
        # 余分な空白を除去
        sanitized = sanitized.strip()
        
        return sanitized


class RateLimiter:
    """レート制限クラス"""
    
    def __init__(self):
        # IPベースのレート制限追跡
        self.ip_requests = defaultdict(list)
        # ユーザーベースのレート制限追跡
        self.user_requests = defaultdict(list)
        
        # 制限値の設定
        self.IP_LIMIT = 5       # IP当たり5リクエスト/分
        self.USER_LIMIT = 10    # ユーザー当たり10リクエスト/分
        self.TIME_WINDOW = 60   # 時間窓（秒）
    
    def _cleanup_old_requests(self, request_list, time_window):
        """古いリクエスト記録をクリーンアップ"""
        current_time = time.time()
        return [req_time for req_time in request_list 
                if current_time - req_time < time_window]
    
    def check_ip_rate_limit(self, ip_address):
        """IPベースのレート制限チェック"""
        current_time = time.time()
        
        # 古いリクエストをクリーンアップ
        self.ip_requests[ip_address] = self._cleanup_old_requests(
            self.ip_requests[ip_address], self.TIME_WINDOW
        )
        
        # 制限チェック
        if len(self.ip_requests[ip_address]) >= self.IP_LIMIT:
            return False, f"Rate limit exceeded. Max {self.IP_LIMIT} requests per minute"
        
        # リクエストを記録
        self.ip_requests[ip_address].append(current_time)
        return True, None
    
    def check_user_rate_limit(self, user_id):
        """ユーザーベースのレート制限チェック"""
        if not user_id:
            return True, None  # 未認証ユーザーはIPベースのみ
        
        current_time = time.time()
        
        # 古いリクエストをクリーンアップ
        self.user_requests[user_id] = self._cleanup_old_requests(
            self.user_requests[user_id], self.TIME_WINDOW
        )
        
        # 制限チェック
        if len(self.user_requests[user_id]) >= self.USER_LIMIT:
            return False, f"User rate limit exceeded. Max {self.USER_LIMIT} requests per minute"
        
        # リクエストを記録
        self.user_requests[user_id].append(current_time)
        return True, None


# グローバルインスタンス
rate_limiter = RateLimiter()


def validate_and_sanitize_input(f):
    """入力検証とサニタイゼーションのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # リクエストデータの取得
            if request.content_type == 'application/json':
                # まずrawデータを取得してJSONパースを制御
                raw_data = request.get_data(as_text=True)
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    return jsonify({'error': 'Invalid JSON'}), 400
            else:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            # JSON形式の検証
            is_valid, error_msg, parsed_data = InputValidator.validate_json_input(data)
            if not is_valid:
                return jsonify({'error': error_msg}), 400
            
            message = parsed_data['message']
            
            # メッセージ長の検証
            is_valid, error_msg = InputValidator.validate_message_length(message)
            if not is_valid:
                return jsonify({'error': error_msg}), 400
            
            # 入力サニタイゼーション
            sanitized_message = InputValidator.sanitize_input(message)
            
            # サニタイズされたデータをリクエストに格納
            request.sanitized_data = {
                'message': sanitized_message,
                'original_message': message
            }
            
            return f(*args, **kwargs)
        
        except Exception as e:
            return jsonify({'error': f'Request processing error: {str(e)}'}), 400
    
    return decorated_function


def rate_limit_check(f):
    """レート制限チェックのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # IPアドレスの取得
        ip_address = request.environ.get('REMOTE_ADDR', 'unknown')
        
        # IPベースのレート制限チェック
        ip_allowed, ip_error = rate_limiter.check_ip_rate_limit(ip_address)
        if not ip_allowed:
            return jsonify({'error': ip_error}), 429
        
        # ユーザーベースのレート制限チェック
        user_id = session.get('user_id')
        user_allowed, user_error = rate_limiter.check_user_rate_limit(user_id)
        if not user_allowed:
            return jsonify({'error': user_error}), 429
        
        return f(*args, **kwargs)
    
    return decorated_function


def security_headers(f):
    """セキュリティヘッダーを追加するデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        # セキュリティヘッダーの追加
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'"
        
        return response
    
    return decorated_function


# セキュリティ機能を統合したデコレータ
def secure_endpoint(f):
    """すべてのセキュリティ機能を適用するデコレータ"""
    @wraps(f)
    @security_headers
    @rate_limit_check
    @validate_and_sanitize_input
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    
    return decorated_function


if __name__ == '__main__':
    # セキュリティユーティリティのテスト
    print("=== セキュリティユーティリティテスト ===")
    
    # XSS対策テスト
    xss_test = "<script>alert('XSS')</script>"
    sanitized = InputValidator.sanitize_html(xss_test)
    print(f"XSS対策: '{xss_test}' -> '{sanitized}'")
    
    # SQLインジェクション対策テスト
    sql_test = "'; DROP TABLE users; --"
    sanitized = InputValidator.sanitize_sql(sql_test)
    print(f"SQLインジェクション対策: '{sql_test}' -> '{sanitized}'")
    
    # メッセージ長検証テスト
    is_valid, error = InputValidator.validate_message_length("")
    print(f"空メッセージ検証: {is_valid}, {error}")
    
    is_valid, error = InputValidator.validate_message_length("A" * 10000)
    print(f"長いメッセージ検証: {is_valid}, {error}")
    
    print("テスト完了")