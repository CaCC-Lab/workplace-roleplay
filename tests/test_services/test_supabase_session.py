"""
SupabaseSessionInterface のユニットテスト（Supabase クライアントはメモリ上の偽物）
"""

from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask, session

from services.supabase_session import SupabaseSessionInterface


class _Query:
    def __init__(self, store, op, payload=None):
        self._store = store
        self._op = op
        self._payload = payload
        self._filters = []

    def select(self, _cols):
        return self

    def eq(self, col, val):
        self._filters.append(lambda r: r[col] == val)
        return self

    def gt(self, col, val):
        self._filters.append(lambda r: r[col] > val)
        return self

    def lt(self, col, val):
        self._filters.append(lambda r: r[col] < val)
        return self

    def limit(self, _n):
        return self

    def execute(self):
        rows = self._store.rows
        if self._op == "upsert":
            rows[self._payload["id"]] = dict(self._payload)
            return type("Res", (), {"data": [self._payload]})()
        matched = [r for r in rows.values() if all(f(r) for f in self._filters)]
        if self._op == "delete":
            for r in matched:
                rows.pop(r["id"], None)
        return type("Res", (), {"data": [dict(r) for r in matched]})()


class _Table:
    def __init__(self, store):
        self._store = store

    def select(self, cols):
        return _Query(self._store, "select").select(cols)

    def upsert(self, payload, on_conflict=None):
        self._store.upserts += 1
        return _Query(self._store, "upsert", payload)

    def delete(self):
        return _Query(self._store, "delete")


class FakeSupabase:
    def __init__(self):
        self.rows = {}
        self.upserts = 0

    def table(self, name):
        assert name == "flask_sessions"
        return _Table(self)


@pytest.fixture
def fake():
    return FakeSupabase()


@pytest.fixture
def client(fake):
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.session_interface = SupabaseSessionInterface(fake)

    @app.route("/set/<value>")
    def set_value(value):
        session["value"] = value
        session["history"] = [{"role": "user", "content": value}]
        return "ok"

    @app.route("/append/<value>")
    def append_value(value):
        session["history"].append({"role": "user", "content": value})
        return "ok"

    @app.route("/get")
    def get_value():
        return {"value": session.get("value"), "history": session.get("history", [])}

    @app.route("/clear")
    def clear():
        session.clear()
        return "ok"

    return app.test_client()


def test_値を保存して次のリクエストで読める(client, fake):
    client.get("/set/hello")

    assert len(fake.rows) == 1
    assert client.get("/get").json == {
        "value": "hello",
        "history": [{"role": "user", "content": "hello"}],
    }


def test_入れ子のリストを書き換えても保存される(client, fake):
    client.get("/set/a")
    client.get("/append/b")

    assert [m["content"] for m in client.get("/get").json["history"]] == ["a", "b"]


def test_変更がなければ書き込まない(client, fake):
    client.get("/set/a")
    before = fake.upserts

    client.get("/get")

    assert fake.upserts == before


def test_空のセッションは保存しない(client, fake):
    client.get("/get")

    assert fake.rows == {}


def test_clearで行とCookieが消える(client, fake):
    client.get("/set/a")
    client.get("/clear")

    assert fake.rows == {}
    assert client.get("/get").json["value"] is None


def test_改ざんされたCookieは新しいセッションになる(client, fake):
    client.get("/set/a")
    client.set_cookie("session", "forged.signature")

    assert client.get("/get").json["value"] is None


def test_期限切れのセッションは読み込まない(client, fake):
    client.get("/set/a")
    for row in fake.rows.values():
        row["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()

    assert client.get("/get").json["value"] is None


def test_Supabaseの読み込み失敗時は新しいセッションで続行(client, fake):
    client.get("/set/a")

    def broken(_name):
        raise RuntimeError("down")

    fake.table = broken

    assert client.get("/get").json["value"] is None


def test_ブラウザーを閉じても残るCookieを発行する(client, fake):
    res = client.get("/set/a")

    cookie = res.headers.get("Set-Cookie", "")
    assert "Expires=" in cookie
