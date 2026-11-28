"""LLM 利用量ガード（Denial of Wallet 対策）のテスト。有料 API はすべてモック化する"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, jsonify, request
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage

from utils import llm_guard
from utils.llm_guard import (
    MAX_ASSIST_CONTEXT_CHARS,
    MAX_SESSION_HISTORY_ENTRIES,
    MAX_USER_MESSAGE_CHARS,
    MAX_WATCH_FIELD_CHARS,
    MAX_WATCH_TURNS,
    Limit,
    LLMInputTooLargeError,
    MemoryStore,
    RedisStore,
    UsageLimiter,
    allowed_ollama_models,
    apply_llm_guard,
)
from utils.security import SecurityUtils

SCENARIO = {
    "id": "scenario1",
    "title": "テストシナリオ",
    "description": "テスト説明",
    "learning_points": ["ポイント1"],
}


class FakeRedis:
    """複数ワーカーが共有する Redis の代わり（INCR / EXPIRE のみ）"""

    def __init__(self, fail: bool = False) -> None:
        self.data = {}
        self.fail = fail

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, redis: FakeRedis) -> None:
        self.redis = redis
        self.ops = []

    def incr(self, key):
        self.ops.append(key)

    def expire(self, key, ttl):
        pass

    def execute(self):
        if self.redis.fail:
            raise ConnectionError("redis down")
        results = []
        for key in self.ops:
            self.redis.data[key] = self.redis.data.get(key, 0) + 1
            results.extend([self.redis.data[key], True])
        return results


@pytest.fixture
def guarded_app(app):
    """レート制限を有効化し、テストごとに独立したカウンターを使う"""
    limiter = UsageLimiter()
    original = app.extensions.get("llm_usage_limiter")
    original_global = llm_guard._limiter
    app.extensions["llm_usage_limiter"] = limiter
    llm_guard._limiter = limiter
    app.config["LLM_RATE_LIMIT_ENABLED"] = True
    yield app
    app.config.pop("LLM_RATE_LIMIT_ENABLED", None)
    app.extensions["llm_usage_limiter"] = original
    llm_guard._limiter = original_global


def _assist(csrf_client, context="上司: おはようございます。"):
    return csrf_client.post("/api/get_assist", json={"scenario_id": "scenario1", "current_context": context})


class TestUsageLimiter:
    def test_セッション_IP_全体の順に制限される(self):
        limiter = UsageLimiter(store=MemoryStore())
        limits = [
            Limit("s", "session", 2, 60, "UNUSED_S"),
            Limit("i", "ip", 3, 60, "UNUSED_I"),
            Limit("g", "global", 4, 60, "UNUSED_G"),
        ]

        def hit(sid, ip):
            return limiter.hit([(limits[0], sid), (limits[1], ip), (limits[2], "all")])

        assert hit("a", "1.1.1.1") is None
        assert hit("a", "1.1.1.1") is None
        assert hit("a", "1.1.1.1")[0].name == "s"
        # セッションを作り直しても同一 IP は止まる
        assert hit("b", "1.1.1.1") is None
        assert hit("c", "1.1.1.1")[0].name == "i"
        # 別 IP でもアプリ全体の上限で止まる
        assert hit("d", "2.2.2.2") is None
        assert hit("e", "3.3.3.3")[0].name == "g"

    def test_環境変数で上限を上書きできる(self, monkeypatch):
        monkeypatch.setenv("TEST_LIMIT_OVERRIDE", "1")
        limiter = UsageLimiter()
        limit = Limit("o", "global", 100, 60, "TEST_LIMIT_OVERRIDE")
        assert limiter.hit([(limit, "all")]) is None
        exceeded = limiter.hit([(limit, "all")])
        assert exceeded is not None and exceeded[1] > 0

    def test_Redisストアは複数ワーカーで共有される(self):
        shared = FakeRedis()
        worker1 = UsageLimiter(store=RedisStore(shared))
        worker2 = UsageLimiter(store=RedisStore(shared))
        limit = Limit("w", "global", 2, 60, "UNUSED_W")
        assert worker1.hit([(limit, "all")]) is None
        assert worker2.hit([(limit, "all")]) is None
        assert worker1.hit([(limit, "all")]) is not None

    def test_Redis障害時はローカルカウンターで制限を継続する(self):
        limiter = UsageLimiter(store=RedisStore(FakeRedis(fail=True)), fail_mode="local")
        limit = Limit("f", "session", 1, 60, "UNUSED_F")
        assert limiter.hit([(limit, "x")]) is None
        assert limiter.hit([(limit, "x")]) is not None

    def test_共有ストア未設定でfail_closedなら例外で止める(self):
        limiter = UsageLimiter(store=None, fail_mode="closed")
        with pytest.raises(llm_guard.RateLimitStoreUnavailable):
            limiter.hit([(Limit("x", "session", 5, 60, "UNUSED_ENV"), "s1")])

    def test_Redis障害時にfail_closedなら例外で止める(self):
        limiter = UsageLimiter(store=RedisStore(FakeRedis(fail=True)), fail_mode="closed")
        with pytest.raises(llm_guard.RateLimitStoreUnavailable):
            limiter.hit([(Limit("c", "global", 10, 60, "UNUSED_C"), "all")])


class TestEndpointRateLimit:
    def test_同一セッションで上限を超えると429(self, guarded_app, csrf_client, monkeypatch):
        monkeypatch.setenv("LLM_RATE_LIMIT_SESSION_PER_MINUTE", "3")
        with (
            patch("routes.scenario_routes.scenario_service") as svc,
            patch("app.create_model_and_get_response", return_value="ヒント") as llm_call,
        ):
            svc.get_scenario_by_id.return_value = SCENARIO
            statuses = [_assist(csrf_client).status_code for _ in range(4)]

        assert statuses == [200, 200, 200, 429]
        assert llm_call.call_count == 3

    def test_429にRetry_Afterが付く(self, guarded_app, csrf_client, monkeypatch):
        monkeypatch.setenv("LLM_RATE_LIMIT_SESSION_PER_MINUTE", "1")
        with (
            patch("routes.scenario_routes.scenario_service") as svc,
            patch("app.create_model_and_get_response", return_value="ヒント"),
        ):
            svc.get_scenario_by_id.return_value = SCENARIO
            _assist(csrf_client)
            response = _assist(csrf_client)

        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) > 0
        assert response.get_json()["code"] == "LLM_RATE_LIMIT_EXCEEDED"

    def test_IP単位の上限はセッションを作り直しても回避できない(self, guarded_app, monkeypatch):
        monkeypatch.setenv("LLM_RATE_LIMIT_IP_PER_MINUTE", "2")
        with (
            patch("routes.scenario_routes.scenario_service") as svc,
            patch("app.create_model_and_get_response", return_value="ヒント"),
        ):
            svc.get_scenario_by_id.return_value = SCENARIO
            from tests.helpers.csrf_helpers import CSRFTestClient

            statuses = [_assist(CSRFTestClient(guarded_app.test_client())).status_code for _ in range(3)]

        assert statuses == [200, 200, 429]

    def test_ストア障害でfail_closedなら503でLLMを呼ばない(self, guarded_app, csrf_client):
        guarded_app.extensions["llm_usage_limiter"] = UsageLimiter(
            store=RedisStore(FakeRedis(fail=True)), fail_mode="closed"
        )
        with (
            patch("routes.scenario_routes.scenario_service") as svc,
            patch("app.create_model_and_get_response", return_value="ヒント") as llm_call,
        ):
            svc.get_scenario_by_id.return_value = SCENARIO
            response = _assist(csrf_client)

        assert response.status_code == 503
        llm_call.assert_not_called()

    def test_共有ストア未設定でfail_closedなら503でLLMを呼ばない(self, guarded_app, csrf_client):
        guarded_app.extensions["llm_usage_limiter"] = UsageLimiter(store=None, fail_mode="closed")
        with (
            patch("routes.scenario_routes.scenario_service") as svc,
            patch("app.create_model_and_get_response", return_value="ヒント") as llm_call,
        ):
            svc.get_scenario_by_id.return_value = SCENARIO
            response = _assist(csrf_client)

        assert response.status_code == 503
        llm_call.assert_not_called()

    def test_LLMを呼ぶ全エンドポイントが対象(self):
        expected = {
            "/api/chat",
            "/api/start_chat",
            "/api/chat_feedback",
            "/api/scenario_chat",
            "/api/scenario_feedback",
            "/api/get_assist",
            "/api/watch/start",
            "/api/watch/next",
            "/api/v2/chat",
            "/api/v2/chat/compare",
            "/api/generate_character_image",
        }
        assert expected <= set(llm_guard.LLM_ENDPOINTS)


class TestInputCaps:
    def test_get_assistはCSRF保護対象(self, client):
        response = client.post("/api/get_assist", json={"scenario_id": "scenario1", "current_context": "x"})
        assert response.status_code == 403

    def test_長すぎるcurrent_contextは400(self, csrf_client):
        with (
            patch("routes.scenario_routes.scenario_service") as svc,
            patch("app.create_model_and_get_response") as llm_call,
        ):
            svc.get_scenario_by_id.return_value = SCENARIO
            response = _assist(csrf_client, "あ" * (MAX_ASSIST_CONTEXT_CHARS + 1))

        assert response.status_code == 400
        llm_call.assert_not_called()

    def test_ollamaの未許可モデルは400(self, csrf_client, monkeypatch):
        monkeypatch.setenv("OLLAMA_ALLOWED_MODELS", "ollama/gemma4:31b-cloud")
        with patch("app.initialize_llm") as init_llm:
            response = csrf_client.post(
                "/api/scenario_chat",
                json={"message": "こんにちは", "scenario_id": "scenario1", "model": "ollama/unknown-model"},
            )

        assert response.status_code == 400
        init_llm.assert_not_called()

    def test_長すぎるシナリオメッセージは400(self, csrf_client):
        with patch("app.initialize_llm") as init_llm:
            response = csrf_client.post(
                "/api/scenario_chat",
                json={"message": "あ" * (MAX_USER_MESSAGE_CHARS + 1), "scenario_id": "scenario1"},
            )

        assert response.status_code == 400
        init_llm.assert_not_called()

    def test_長すぎる観戦設定は400(self, csrf_client):
        with patch("app.initialize_llm") as init_llm:
            response = csrf_client.post(
                "/api/watch/start",
                json={"partner_type": "あ" * (MAX_WATCH_FIELD_CHARS + 1), "situation": "s", "topic": "t"},
            )

        assert response.status_code == 400
        init_llm.assert_not_called()

    def test_観戦は最大発言数で止まる(self, app, csrf_client):
        with csrf_client.client.session_transaction() as sess:
            sess["watch_settings"] = {"model_a": "m", "model_b": "m", "current_speaker": "A"}
            sess["watch_history"] = [{"speaker": "A", "message": "m"} for _ in range(MAX_WATCH_TURNS)]
        with patch("app.initialize_llm") as init_llm:
            response = csrf_client.post("/api/watch/next", json={})

        assert response.status_code == 400
        init_llm.assert_not_called()

    def test_観戦のLLM入力は直近の履歴だけ(self, app, csrf_client):
        with csrf_client.client.session_transaction() as sess:
            sess["watch_settings"] = {"model_a": "m", "model_b": "m", "current_speaker": "A"}
            sess["watch_history"] = [{"speaker": "A", "message": str(i)} for i in range(30)]
        with patch("app.initialize_llm"), patch("routes.watch_routes.get_watch_service") as get_svc:
            svc = MagicMock()
            svc.switch_speaker.return_value = "B"
            svc.get_speaker_display_name.return_value = "花子"
            svc.generate_next_message.return_value = "次"
            get_svc.return_value = svc
            csrf_client.post("/api/watch/next", json={})

        sent_history = svc.generate_next_message.call_args[0][1]
        assert len(sent_history) == llm_guard.MAX_WATCH_PROMPT_HISTORY

    def test_セッション履歴は上限件数で切り詰める(self, app):
        from utils.helpers import add_to_session_history

        with app.test_request_context():
            from flask import session

            for i in range(MAX_SESSION_HISTORY_ENTRIES + 5):
                add_to_session_history("chat_history", {"human": str(i), "ai": "a"})
            assert len(session["chat_history"]) == MAX_SESSION_HISTORY_ENTRIES
            assert session["chat_history"][-1]["human"] == str(MAX_SESSION_HISTORY_ENTRIES + 4)


class TestModelAllowlist:
    def test_ollamaは明示したモデルのみ許可(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_ALLOWED_MODELS", "gemma4:31b-cloud, ollama/qwen3:8b")
        assert SecurityUtils.validate_model_name("ollama/gemma4:31b-cloud")
        assert SecurityUtils.validate_model_name("ollama/qwen3:8b")
        assert not SecurityUtils.validate_model_name("ollama/unknown-model")

    def test_運営者が設定したデフォルトのollamaモデルは許可(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_ALLOWED_MODELS", raising=False)
        monkeypatch.setenv("SCENARIO_MODEL", "ollama/gemma4:31b-cloud")
        assert "ollama/gemma4:31b-cloud" in allowed_ollama_models()

    def test_運営者が設定したGeminiモデルは固定リスト外でも許可(self, monkeypatch):
        monkeypatch.setenv("CHAT_MODEL", "gemini/gemini-3-flash-preview")
        assert SecurityUtils.validate_model_name("gemini/gemini-3-flash-preview")
        assert not SecurityUtils.validate_model_name("gemini/gemini-3-pro-preview")

    def test_運営者設定のGeminiモデルは接頭辞の有無を問わず許可(self, monkeypatch):
        monkeypatch.setenv("CHAT_MODEL", "gemini-3-flash-preview")
        assert SecurityUtils.validate_model_name("gemini/gemini-3-flash-preview")
        assert SecurityUtils.validate_model_name("gemini-3-flash-preview")

    def test_register時に_envを読み込む(self, monkeypatch):
        with patch("dotenv.load_dotenv") as load:
            llm_guard.register_llm_guard(Flask(__name__), limiter=UsageLimiter())
        load.assert_called_once()
        monkeypatch.setattr(llm_guard, "_limiter", None)

    def test_モデル選択無効時はクライアント指定を無視する(self, monkeypatch):
        from services.model_selector import resolve_model

        config = MagicMock(ENABLE_MODEL_SELECTION=False, DEFAULT_MODEL="gemini/gemini-2.5-flash")
        monkeypatch.delenv("SCENARIO_MODEL", raising=False)
        with patch("services.model_selector.get_config", return_value=config):
            assert resolve_model("scenario", "ollama/expensive") == "gemini/gemini-2.5-flash"


class TestLLMCallGuard:
    def test_出力トークン上限を設定する_Gemini(self, monkeypatch):
        from langchain_google_genai import ChatGoogleGenerativeAI

        monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", "512")
        llm = apply_llm_guard(ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key="test-key"))
        assert llm.max_output_tokens == 512
        assert llm_guard._CALL_GUARD in llm.callbacks

    def test_出力トークン上限を設定する_Ollama(self):
        from langchain_openai import ChatOpenAI

        llm = apply_llm_guard(ChatOpenAI(model="gemma4:31b-cloud", api_key="test-key", base_url="http://localhost:1"))
        assert llm.max_tokens == llm_guard.max_output_tokens()

    def test_LLMServiceが生成するモデルにガードが付く(self):
        from services.llm_service import LLMService

        with patch.dict("os.environ", {"OLLAMA_API_KEY": "test-key"}):
            llm = LLMService().initialize_llm("ollama/gemma4:31b-cloud")
        assert llm.max_tokens == llm_guard.max_output_tokens()
        assert llm_guard._CALL_GUARD in llm.callbacks

    def test_入力トークン上限を超えると呼び出し前に止める(self, monkeypatch):
        monkeypatch.setenv("LLM_MAX_INPUT_TOKENS", "100")
        llm = apply_llm_guard(FakeListChatModel(responses=["ok"]))
        assert llm.invoke([HumanMessage(content="短い")]).content == "ok"
        with pytest.raises(LLMInputTooLargeError):
            llm.invoke([HumanMessage(content="あ" * 101)])

    def test_アプリ全体の日次呼び出し上限(self, monkeypatch):
        monkeypatch.setenv("LLM_CALL_LIMIT_GLOBAL_PER_DAY", "1")
        monkeypatch.setattr(llm_guard, "_limiter", UsageLimiter())
        monkeypatch.setenv("LLM_RATE_LIMIT_ENABLED", "true")
        llm = apply_llm_guard(FakeListChatModel(responses=["ok", "ok"]))
        llm.invoke("1回目")
        with pytest.raises(LLMInputTooLargeError):
            llm.invoke("2回目")


class TestProxyTrustBoundary:
    def _app(self, monkeypatch, hops):
        from app import _apply_proxy_fix

        if hops is None:
            monkeypatch.delenv("TRUSTED_PROXY_COUNT", raising=False)
        else:
            monkeypatch.setenv("TRUSTED_PROXY_COUNT", str(hops))
        test_app = Flask(__name__)
        _apply_proxy_fix(test_app)

        @test_app.route("/ip")
        def ip():
            return jsonify({"ip": llm_guard.client_ip(), "raw": request.remote_addr})

        return test_app.test_client()

    def test_信頼プロキシ以外からのX_Forwarded_Forは無視(self, monkeypatch):
        client = self._app(monkeypatch, None)
        data = client.get("/ip", headers={"X-Forwarded-For": "6.6.6.6"}, environ_base={"REMOTE_ADDR": "9.9.9.9"})
        assert data.get_json()["ip"] == "9.9.9.9"

    def test_ローカルのnginxからは末尾のIPのみ採用(self, monkeypatch):
        client = self._app(monkeypatch, None)
        data = client.get(
            "/ip",
            headers={"X-Forwarded-For": "6.6.6.6, 203.0.113.5"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        assert data.get_json()["ip"] == "203.0.113.5"

    def test_信頼段数0ならX_Forwarded_Forを使わない(self, monkeypatch):
        client = self._app(monkeypatch, 0)
        data = client.get("/ip", headers={"X-Forwarded-For": "6.6.6.6"}, environ_base={"REMOTE_ADDR": "127.0.0.1"})
        assert data.get_json()["ip"] == "127.0.0.1"

    def test_IPv6は64ビット単位で集約(self, monkeypatch):
        client = self._app(monkeypatch, None)
        data = client.get("/ip", environ_base={"REMOTE_ADDR": "2001:db8:1:2:aaaa::1"})
        assert data.get_json()["ip"] == "2001:db8:1:2::"
