"""
認証（Supabase Auth 匿名サインイン）用ルート

匿名サインインでPIIなしにauth.usersにユーザー作成。
同一ブラウザのセッションで継続利用。
サインアウト・ブラウザデータ削除・別端末では原則復旧不可。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, render_template, request, session

from services.supabase_auth_service import SupabaseAuthService
from services.supabase_client import get_supabase_client_manager

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

SESSION_TOKEN_KEY = "supabase_access_token"


def _auth_service() -> Optional[SupabaseAuthService]:
    client = get_supabase_client_manager().get_client()
    if client is None:
        return None
    return SupabaseAuthService(client)


def _access_token_from_session_obj(sess: Any) -> Optional[str]:
    if sess is None:
        return None
    if isinstance(sess, dict):
        return sess.get("access_token")
    return getattr(sess, "access_token", None)


def _user_to_jsonable(user: Any) -> Optional[Dict[str, Any]]:
    if user is None:
        return None
    if isinstance(user, dict):
        return user
    if hasattr(user, "model_dump"):
        try:
            return user.model_dump()
        except Exception:
            pass
    out: Dict[str, Any] = {}
    for key in ("id", "email", "phone", "created_at", "app_metadata", "user_metadata", "is_anonymous"):
        if hasattr(user, key):
            out[key] = getattr(user, key)
    return out if out else {"repr": str(user)}


@auth_bp.route("/login", methods=["GET"])
def login_page():
    """利用開始画面（匿名サインイン）"""
    return render_template("auth.html")


@auth_bp.route("/api/anonymous", methods=["POST"])
def api_anonymous():
    """POST /auth/api/anonymous → 匿名サインイン → JSON

    PIIなしでauth.usersに匿名ユーザーを作成。
    authenticatedロールでDBにアクセス可能。
    """
    try:
        svc = _auth_service()
        if svc is None:
            return jsonify({"user": None, "error": "Supabaseが設定されていません"}), 503
        result = svc.sign_in_anonymously()
        if result.get("error"):
            return jsonify({"user": None, "error": result["error"]}), 400
        sess = result.get("session")
        token = _access_token_from_session_obj(sess)
        if token:
            session[SESSION_TOKEN_KEY] = token
        return jsonify({
            "user": _user_to_jsonable(result.get("user")),
            "is_anonymous": True,
            "error": None,
        }), 200
    except Exception as e:
        return jsonify({"user": None, "error": str(e)}), 500


@auth_bp.route("/api/register", methods=["POST"])
def api_register():
    """POST /auth/api/register → メール登録（将来拡張: 匿名→恒久リンク用）"""
    try:
        svc = _auth_service()
        if svc is None:
            return jsonify({"user": None, "error": "Supabaseが設定されていません"}), 503
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        password = data.get("password")
        result = svc.sign_up(email, password)
        if result.get("error"):
            return jsonify({"user": None, "error": result["error"]}), 400
        return jsonify({"user": _user_to_jsonable(result.get("user")), "error": None}), 200
    except Exception as e:
        return jsonify({"user": None, "error": str(e)}), 500


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    """POST /auth/api/login → メールログイン（将来拡張用）"""
    try:
        svc = _auth_service()
        if svc is None:
            return jsonify({"user": None, "session": None, "error": "Supabaseが設定されていません"}), 503
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        password = data.get("password")
        result = svc.sign_in(email, password)
        if result.get("error"):
            return jsonify({"user": None, "session": None, "error": result["error"]}), 400
        sess = result.get("session")
        token = _access_token_from_session_obj(sess)
        if token:
            session[SESSION_TOKEN_KEY] = token
        return jsonify({
            "user": _user_to_jsonable(result.get("user")),
            "session": None,
            "error": None,
        }), 200
    except Exception as e:
        return jsonify({"user": None, "session": None, "error": str(e)}), 500


@auth_bp.route("/api/logout", methods=["POST"])
def api_logout():
    """POST /auth/api/logout → サインアウト

    注意: 匿名ユーザーはサインアウト後、同じユーザーに戻れません。
    """
    try:
        svc = _auth_service()
        if svc is not None:
            try:
                svc.sign_out()
            except Exception:
                pass
        session.pop(SESSION_TOKEN_KEY, None)
        return jsonify({"success": True}), 200
    except Exception as e:
        session.pop(SESSION_TOKEN_KEY, None)
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/api/me", methods=["GET"])
def api_me():
    """GET /auth/api/me → 現在のユーザー情報"""
    try:
        svc = _auth_service()
        if svc is None:
            return jsonify({"error": "Supabaseが設定されていません"}), 503
        token = session.get(SESSION_TOKEN_KEY)
        result = svc.get_current_user(token)
        if result is None:
            return jsonify({"user": None}), 401
        return jsonify({"user": _user_to_jsonable(result.get("user"))}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
