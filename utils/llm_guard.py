"""
LLM 利用量ガード（Denial of Wallet 対策）

匿名利用を維持したまま、有料 LLM API の呼び出し量に上限を設ける。

- リクエスト単位: セッション単位・IP 単位・アプリ全体の固定ウィンドウ制限
- 呼び出し単位: 入力トークン（推定）上限、出力トークン上限、アプリ全体の日次呼び出し上限
- 制限用ストア: Redis（複数ワーカーで共有）。障害時はプロセス内メモリで制限を継続するか、
  LLM_RATE_LIMIT_FAIL_MODE=closed で LLM 呼び出しを止める
"""

from __future__ import annotations

import ipaddress
import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from flask import Flask, jsonify, request, session
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)

# ========== 入力・履歴・トークンの上限 ==========

MAX_USER_MESSAGE_CHARS = 2000
MAX_ASSIST_CONTEXT_CHARS = 4000
MAX_WATCH_FIELD_CHARS = 100
MAX_SESSION_HISTORY_ENTRIES = 50
MAX_FEEDBACK_HISTORY_ENTRIES = 12
MAX_WATCH_PROMPT_HISTORY = 10
MAX_WATCH_TURNS = 40

DEFAULT_MAX_INPUT_TOKENS = 32000
DEFAULT_MAX_OUTPUT_TOKENS = 2048

_SESSION_ID_KEY = "_llm_rl_id"
_MODEL_ENV_KEYS = ("DEFAULT_MODEL", "SCENARIO_MODEL", "CHAT_MODEL", "WATCH_MODEL", "FEEDBACK_MODEL")


def _env_int(name: str, default: int) -> int:
    try:
        value = int((os.environ.get(name) or "").strip())
    except ValueError:
        return default
    return value if value > 0 else default


def max_input_tokens() -> int:
    return _env_int("LLM_MAX_INPUT_TOKENS", DEFAULT_MAX_INPUT_TOKENS)


def max_output_tokens() -> int:
    return _env_int("LLM_MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS)


def allowed_ollama_models() -> set:
    """運営者が環境変数で明示した Ollama Cloud モデルだけを許可する"""
    names = set()
    for raw in (os.environ.get("OLLAMA_ALLOWED_MODELS") or "").split(","):
        name = raw.strip()
        if name:
            names.add(name if name.startswith("ollama/") else f"ollama/{name}")
    for key in _MODEL_ENV_KEYS:
        value = (os.environ.get(key) or "").strip()
        if value.startswith("ollama/"):
            names.add(value)
    return names


def is_text_too_long(value: Any, max_chars: int) -> bool:
    return isinstance(value, str) and len(value) > max_chars


# ========== 利用量制限 ==========


@dataclass(frozen=True)
class Limit:
    name: str
    scope: str  # "session" | "ip" | "global"
    max_requests: int
    window_seconds: int
    env: str

    def resolved_max(self) -> int:
        return _env_int(self.env, self.max_requests)


TEXT_LIMITS: Tuple[Limit, ...] = (
    Limit("session_minute", "session", 20, 60, "LLM_RATE_LIMIT_SESSION_PER_MINUTE"),
    Limit("session_day", "session", 300, 86400, "LLM_RATE_LIMIT_SESSION_PER_DAY"),
    Limit("ip_minute", "ip", 40, 60, "LLM_RATE_LIMIT_IP_PER_MINUTE"),
    Limit("ip_day", "ip", 500, 86400, "LLM_RATE_LIMIT_IP_PER_DAY"),
    Limit("global_minute", "global", 60, 60, "LLM_RATE_LIMIT_GLOBAL_PER_MINUTE"),
    Limit("global_day", "global", 1000, 86400, "LLM_RATE_LIMIT_GLOBAL_PER_DAY"),
)

IMAGE_LIMITS: Tuple[Limit, ...] = (
    Limit("image_session_hour", "session", 5, 3600, "IMAGE_RATE_LIMIT_SESSION_PER_HOUR"),
    Limit("image_ip_hour", "ip", 10, 3600, "IMAGE_RATE_LIMIT_IP_PER_HOUR"),
    Limit("image_global_day", "global", 100, 86400, "IMAGE_RATE_LIMIT_GLOBAL_PER_DAY"),
)

# ルートの制限を通った後でも、1 リクエストで複数回呼ぶ経路やルート一覧に無い経路を止める最終防衛線
CALL_LIMITS: Tuple[Limit, ...] = (Limit("calls_global_day", "global", 2000, 86400, "LLM_CALL_LIMIT_GLOBAL_PER_DAY"),)

LIMIT_GROUPS: Dict[str, Tuple[Limit, ...]] = {"text": TEXT_LIMITS, "image": IMAGE_LIMITS}

# 有料 API（Gemini / Ollama Cloud）を呼び出す POST エンドポイント
LLM_ENDPOINTS: Dict[str, str] = {
    "/api/chat": "text",
    "/api/start_chat": "text",
    "/api/chat_feedback": "text",
    "/api/scenario_chat": "text",
    "/api/scenario_feedback": "text",
    "/api/get_assist": "text",
    "/api/watch/start": "text",
    "/api/watch/next": "text",
    "/api/v2/chat": "text",
    "/api/v2/chat/compare": "text",
    "/api/generate_character_image": "image",
}


class RateLimitStoreUnavailable(Exception):
    """制限用ストアが使えず、fail-closed 設定で呼び出しを止める場合"""


class LLMInputTooLargeError(ValueError):
    """LLM への入力が上限を超えた場合"""


class MemoryStore:
    """プロセス内の固定ウィンドウカウンター"""

    def __init__(self) -> None:
        self._counts: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = 0.0

    def incr(self, key: str, ttl: int) -> int:
        now = time.time()
        with self._lock:
            if now - self._last_cleanup > 60:
                self._counts = {k: v for k, v in self._counts.items() if v[1] > now}
                self._last_cleanup = now
            count, expires_at = self._counts.get(key, (0, now + ttl))
            if expires_at <= now:
                count, expires_at = 0, now + ttl
            count += 1
            self._counts[key] = (count, expires_at)
            return count


class RedisStore:
    """複数ワーカー・複数インスタンスで共有する Redis カウンター"""

    def __init__(self, client: Any) -> None:
        self._client = client

    def incr(self, key: str, ttl: int) -> int:
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        count, _ = pipe.execute()
        return int(count)


class UsageLimiter:
    def __init__(self, store: Optional[Any] = None, fail_mode: str = "local") -> None:
        self.store = store
        self.fallback = MemoryStore()
        self.fail_mode = fail_mode

    def _incr(self, key: str, ttl: int) -> int:
        if self.store is None:
            return self.fallback.incr(key, ttl)
        try:
            return self.store.incr(key, ttl)
        except Exception as e:
            logger.error("LLM rate limit store unavailable: %s", type(e).__name__)
            if self.fail_mode == "closed":
                raise RateLimitStoreUnavailable() from e
            return self.fallback.incr(key, ttl)

    def hit(self, limits: Iterable[Tuple[Limit, str]]) -> Optional[Tuple[Limit, int]]:
        """
        制限を順に消費し、超過した制限と再試行までの秒数を返す（超過なしなら None）

        セッション・IP の制限で止まったリクエストはアプリ全体の枠を消費しない
        """
        now = time.time()
        for limit, identifier in limits:
            bucket = int(now // limit.window_seconds)
            key = f"llm_rl:{limit.name}:{identifier}:{bucket}"
            count = self._incr(key, limit.window_seconds + 1)
            if count > limit.resolved_max():
                retry_after = int((bucket + 1) * limit.window_seconds - now) + 1
                return limit, retry_after
        return None


_limiter: Optional[UsageLimiter] = None


def get_usage_limiter() -> Optional[UsageLimiter]:
    return _limiter


def client_ip() -> str:
    """ProxyFix 適用後の接続元 IP。IPv6 は /64 単位でまとめる"""
    addr = request.remote_addr or "unknown"
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return addr
    if ip.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False).network_address)
    return str(ip)


def session_identifier() -> str:
    sid = session.get(_SESSION_ID_KEY)
    if not sid:
        sid = secrets.token_urlsafe(16)
        session[_SESSION_ID_KEY] = sid
        session.modified = True
    return sid


def _identifiers_for(limits: Iterable[Limit]) -> List[Tuple[Limit, str]]:
    ids = {"global": "all"}
    result = []
    for limit in sorted(limits, key=lambda lim: ("session", "ip", "global").index(lim.scope)):
        if limit.scope not in ids:
            ids[limit.scope] = session_identifier() if limit.scope == "session" else client_ip()
        result.append((limit, ids[limit.scope]))
    return result


def _build_store(app: Flask) -> Optional[Any]:
    url = (os.environ.get("LLM_RATE_LIMIT_REDIS_URL") or "").strip()
    if url:
        import redis

        return RedisStore(redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5))
    client = app.config.get("SESSION_REDIS")
    if app.config.get("SESSION_TYPE") == "redis" and client is not None:
        return RedisStore(client)
    return None


def _is_enabled(app: Flask) -> bool:
    configured = app.config.get("LLM_RATE_LIMIT_ENABLED")
    if configured is not None:
        return bool(configured)
    raw = (os.environ.get("LLM_RATE_LIMIT_ENABLED") or "").strip().lower()
    if raw:
        return raw not in ("0", "false", "no", "off")
    return not app.config.get("TESTING", False)


def register_llm_guard(app: Flask, limiter: Optional[UsageLimiter] = None) -> UsageLimiter:
    """LLM エンドポイントの利用量制限を登録する（CSRF 検証の後に実行される）"""
    global _limiter

    if limiter is None:
        fail_mode = (os.environ.get("LLM_RATE_LIMIT_FAIL_MODE") or "local").strip().lower()
        limiter = UsageLimiter(store=_build_store(app), fail_mode="closed" if fail_mode == "closed" else "local")
    _limiter = limiter
    app.extensions["llm_usage_limiter"] = limiter

    @app.before_request
    def llm_rate_limit():
        if request.method != "POST" or not _is_enabled(app):
            return None
        group = LLM_ENDPOINTS.get(request.path)
        if group is None:
            return None
        current = app.extensions.get("llm_usage_limiter")
        try:
            exceeded = current.hit(_identifiers_for(LIMIT_GROUPS[group]))
        except RateLimitStoreUnavailable:
            return jsonify({"error": "現在混み合っています。しばらくしてからお試しください。"}), 503
        if exceeded is None:
            return None
        limit, retry_after = exceeded
        logger.warning("LLM rate limit exceeded: %s %s", limit.name, request.path)
        response = jsonify(
            {
                "error": "利用回数の上限に達しました。しばらく待ってから再度お試しください。",
                "code": "LLM_RATE_LIMIT_EXCEEDED",
                "retry_after": retry_after,
            }
        )
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    return limiter


# ========== 呼び出し単位のガード ==========


def estimate_tokens(text: str) -> int:
    """日本語では概ね 1 文字 ≒ 1 トークン以下のため、文字数を保守的な推定値とする"""
    return len(text or "")


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(str(part.get("text", "")))
        return "".join(parts)
    return str(content)


class LLMCallGuard(BaseCallbackHandler):
    """LangChain の呼び出し直前に入力上限とアプリ全体の呼び出し上限を確認する"""

    raise_error = True

    def _check(self, texts: Iterable[str]) -> None:
        total = sum(estimate_tokens(t) for t in texts)
        limit = max_input_tokens()
        if total > limit:
            raise LLMInputTooLargeError(f"LLM input too large: ~{total} tokens (limit {limit})")
        limiter = get_usage_limiter()
        if limiter is None or not _call_limit_enabled():
            return
        exceeded = limiter.hit([(lim, "all") for lim in CALL_LIMITS])
        if exceeded is not None:
            raise LLMInputTooLargeError("LLM daily call budget exceeded")

    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[Any]], **kwargs: Any) -> None:
        self._check(_message_text(m) for batch in messages for m in batch)

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        self._check(prompts)


def _call_limit_enabled() -> bool:
    try:
        from flask import current_app

        return _is_enabled(current_app)
    except RuntimeError:
        raw = (os.environ.get("LLM_RATE_LIMIT_ENABLED") or "true").strip().lower()
        return raw not in ("0", "false", "no", "off")


_CALL_GUARD = LLMCallGuard()


def apply_llm_guard(llm: Any) -> Any:
    """LangChain チャットモデルに出力トークン上限と呼び出しガードを設定する"""
    fields = getattr(type(llm), "model_fields", None)
    if not isinstance(fields, dict):
        return llm

    cap = max_output_tokens()
    for field in ("max_output_tokens", "max_tokens"):
        if field in fields:
            current = getattr(llm, field, None)
            setattr(llm, field, min(current, cap) if current else cap)
            break

    callbacks = getattr(llm, "callbacks", None)
    if callbacks is None:
        llm.callbacks = [_CALL_GUARD]
    elif isinstance(callbacks, list):
        if _CALL_GUARD not in callbacks:
            callbacks.append(_CALL_GUARD)
    elif hasattr(callbacks, "add_handler"):
        callbacks.add_handler(_CALL_GUARD, inherit=True)
    return llm
