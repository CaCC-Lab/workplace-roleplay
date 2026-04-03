"""
Supabase Auth 操作（匿名サインイン対応）

匿名ユーザーは auth.users に authenticated ロールで作成される。
PIIは一切保存しない。JWTの is_anonymous クレームで匿名/恒久ユーザーを区別可能。
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class SupabaseAuthService:
    def __init__(self, client: Any) -> None:
        self._client = client

    def sign_in_anonymously(self) -> Dict[str, Any]:
        """匿名サインイン。PIIなしでauth.usersに匿名ユーザーを作成する。"""
        try:
            res = self._client.auth.sign_in_anonymously()
            user = getattr(res, "user", None)
            session = getattr(res, "session", None)
            err = getattr(res, "error", None)
            if err is not None:
                return {"user": None, "session": None, "error": str(err)}
            return {"user": user, "session": session, "error": None}
        except Exception as e:
            return {"user": None, "session": None, "error": str(e)}

    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """メール/パスワードで恒久ユーザー登録（将来拡張: 匿名→恒久リンク用）"""
        if password is None or str(password).strip() == "":
            return {"user": None, "error": "パスワードは必須です"}
        try:
            res = self._client.auth.sign_up({"email": email, "password": password})
            user = getattr(res, "user", None)
            err = getattr(res, "error", None)
            if err is not None:
                return {"user": None, "error": str(err)}
            return {"user": user, "error": None}
        except Exception as e:
            return {"user": None, "error": str(e)}

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """メール/パスワードでログイン（将来拡張用）"""
        if password is None or str(password).strip() == "":
            return {"user": None, "session": None, "error": "パスワードは必須です"}
        try:
            res = self._client.auth.sign_in_with_password({"email": email, "password": password})
            user = getattr(res, "user", None)
            session = getattr(res, "session", None)
            err = getattr(res, "error", None)
            if err is not None:
                return {"user": None, "session": None, "error": str(err)}
            return {"user": user, "session": session, "error": None}
        except Exception as e:
            return {"user": None, "session": None, "error": str(e)}

    def sign_out(self) -> Dict[str, Any]:
        try:
            self._client.auth.sign_out()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_current_user(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not token or not str(token).strip():
            return None
        try:
            res = self._client.auth.get_user(token)
            user = getattr(res, "user", None)
            if user is None:
                return None
            return {"user": user}
        except Exception:
            return None
