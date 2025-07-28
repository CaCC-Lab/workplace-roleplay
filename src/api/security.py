"""セキュリティ関連API"""
from flask import jsonify, session
from typing import Dict, Any
import secrets


def get_csrf_token() -> tuple[Dict[str, Any], int]:
    """CSRFトークンを生成して返す
    
    Returns:
        レスポンスとステータスコード
    """
    # セッションにCSRFトークンがない場合は生成
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    
    return jsonify({
        "csrf_token": session['csrf_token']
    }), 200