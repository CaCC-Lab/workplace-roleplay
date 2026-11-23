"""
Supabase の flask_sessions テーブルにセッションを保存する Flask セッションインターフェース

サーバーレス環境（Vercel）ではローカルファイルや常駐 Redis を使えないため、
会話履歴などのセッションデータを Supabase に保存する。
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from flask import Flask, Request, Response
from flask.json.tag import TaggedJSONSerializer
from flask.sessions import SessionInterface, SessionMixin
from itsdangerous import BadSignature, Signer
from werkzeug.datastructures import CallbackDict

logger = logging.getLogger(__name__)


class SupabaseSession(CallbackDict, SessionMixin):
    """セッション ID と読み込み時の内容を保持するセッション"""

    def __init__(
        self,
        initial: Optional[dict] = None,
        sid: str = "",
        new: bool = False,
        loaded: str = "",
        expires_at: Optional[datetime] = None,
    ) -> None:
        def on_update(self_: "SupabaseSession") -> None:
            self_.modified = True

        super().__init__(initial or {}, on_update)
        self.sid = sid
        self.new = new
        self.modified = False
        self.loaded = loaded
        self.expires_at = expires_at


class SupabaseSessionInterface(SessionInterface):
    """セッションデータを Supabase に、署名付きセッション ID を Cookie に保存する"""

    TABLE = "flask_sessions"
    SALT = "supabase-session"

    def __init__(self, client: Any) -> None:
        self._client = client
        self._serializer = TaggedJSONSerializer()

    def _signer(self, app: Flask) -> Signer:
        return Signer(app.secret_key, salt=self.SALT)

    def _lifetime(self, app: Flask) -> timedelta:
        return app.permanent_session_lifetime

    def _new_session(self) -> SupabaseSession:
        return SupabaseSession(sid=secrets.token_urlsafe(32), new=True)

    def open_session(self, app: Flask, request: Request) -> SupabaseSession:
        cookie = request.cookies.get(self.get_cookie_name(app))
        if not cookie:
            return self._new_session()
        try:
            sid = self._signer(app).unsign(cookie).decode()
        except BadSignature:
            return self._new_session()

        now = datetime.now(timezone.utc)
        try:
            res = (
                self._client.table(self.TABLE)
                .select("data,expires_at")
                .eq("id", sid)
                .gt("expires_at", now.isoformat())
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None) or []
        except Exception as e:
            logger.warning("Supabaseからセッションを読み込めませんでした: %s", e)
            return self._new_session()

        if not rows:
            return self._new_session()
        raw = rows[0].get("data") or ""
        try:
            data = self._serializer.loads(raw) if raw else {}
        except (ValueError, TypeError):
            data = {}
        expires_at = _parse_timestamp(rows[0].get("expires_at"))
        return SupabaseSession(data, sid=sid, loaded=raw, expires_at=expires_at)

    def save_session(self, app: Flask, session: SessionMixin, response: Response) -> None:
        if not isinstance(session, SupabaseSession):
            return
        name = self.get_cookie_name(app)
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)

        if not session:
            if not session.new:
                self._delete(session.sid)
                response.delete_cookie(name, domain=domain, path=path)
            return

        raw = self._serializer.dumps(dict(session))
        now = datetime.now(timezone.utc)
        lifetime = self._lifetime(app)
        # 内容が変わらず有効期限にも余裕があれば書き込みを省く
        needs_refresh = session.expires_at is None or session.expires_at - now < lifetime / 2
        if raw == session.loaded and not needs_refresh:
            return

        try:
            self._client.table(self.TABLE).upsert(
                {"id": session.sid, "data": raw, "expires_at": (now + lifetime).isoformat()},
                on_conflict="id",
            ).execute()
        except Exception as e:
            logger.error("Supabaseにセッションを保存できませんでした: %s", e)
            return

        if session.new:
            self._delete_expired(now)

        response.set_cookie(
            name,
            self._signer(app).sign(session.sid).decode(),
            expires=self._cookie_expires(app, now + lifetime),
            httponly=self.get_cookie_httponly(app),
            domain=domain,
            path=path,
            secure=self.get_cookie_secure(app),
            samesite=self.get_cookie_samesite(app),
        )

    def _cookie_expires(self, app: Flask, expires_at: datetime) -> Optional[datetime]:
        """Flask-Session と同じく、既定ではブラウザーを閉じても Cookie を残す"""
        return expires_at if app.config.get("SESSION_PERMANENT", True) else None

    def _delete(self, sid: str) -> None:
        try:
            self._client.table(self.TABLE).delete().eq("id", sid).execute()
        except Exception as e:
            logger.warning("Supabaseのセッションを削除できませんでした: %s", e)

    def _delete_expired(self, now: datetime) -> None:
        try:
            self._client.table(self.TABLE).delete().lt("expires_at", now.isoformat()).execute()
        except Exception as e:
            logger.warning("期限切れセッションを削除できませんでした: %s", e)


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
