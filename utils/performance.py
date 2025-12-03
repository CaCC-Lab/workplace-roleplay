"""
パフォーマンス計測・最適化ユーティリティ
"""
import time
import functools
import logging
from typing import Any, Callable, Dict, Optional
from datetime import datetime, timedelta
from threading import Lock
from collections import OrderedDict

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """パフォーマンスメトリクス収集クラス"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初期化"""
        self.metrics: Dict[str, Dict] = {}
        self.start_time = datetime.now()

    def record_request(self, endpoint: str, duration_ms: float, status_code: int):
        """
        リクエストメトリクスを記録

        Args:
            endpoint: エンドポイント名
            duration_ms: 処理時間（ミリ秒）
            status_code: HTTPステータスコード
        """
        if endpoint not in self.metrics:
            self.metrics[endpoint] = {
                "count": 0,
                "total_duration_ms": 0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0,
                "success_count": 0,
                "error_count": 0,
            }

        m = self.metrics[endpoint]
        m["count"] += 1
        m["total_duration_ms"] += duration_ms
        m["min_duration_ms"] = min(m["min_duration_ms"], duration_ms)
        m["max_duration_ms"] = max(m["max_duration_ms"], duration_ms)

        if 200 <= status_code < 400:
            m["success_count"] += 1
        else:
            m["error_count"] += 1

    def get_metrics(self, endpoint: Optional[str] = None) -> Dict:
        """
        メトリクスを取得

        Args:
            endpoint: 特定エンドポイント（Noneの場合は全体）

        Returns:
            メトリクス辞書
        """
        if endpoint:
            m = self.metrics.get(endpoint, {})
            if m and m["count"] > 0:
                m["avg_duration_ms"] = m["total_duration_ms"] / m["count"]
            return m

        # 全体メトリクス
        result = {}
        for ep, m in self.metrics.items():
            result[ep] = {**m, "avg_duration_ms": m["total_duration_ms"] / m["count"] if m["count"] > 0 else 0}

        result["_summary"] = {
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "total_endpoints": len(self.metrics),
            "total_requests": sum(m["count"] for m in self.metrics.values()),
        }

        return result

    def reset(self):
        """メトリクスをリセット"""
        self.metrics = {}
        self.start_time = datetime.now()


def get_metrics() -> PerformanceMetrics:
    """パフォーマンスメトリクスインスタンスを取得"""
    return PerformanceMetrics()


def measure_time(func: Callable = None, *, name: str = None):
    """
    関数の実行時間を計測するデコレータ

    Args:
        func: デコレートする関数
        name: 計測名（省略時は関数名）

    使用例:
        @measure_time
        def my_function():
            pass

        @measure_time(name="custom_name")
        def my_function():
            pass
    """

    def decorator(fn: Callable) -> Callable:
        metric_name = name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.debug(f"[PERF] {metric_name}: {duration_ms:.2f}ms")

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


class LRUCache:
    """
    LRUキャッシュ実装（スレッドセーフ）

    使用例:
        cache = LRUCache(maxsize=100, ttl_seconds=300)
        cache.set("key", "value")
        value = cache.get("key")
    """

    def __init__(self, maxsize: int = 128, ttl_seconds: Optional[int] = None):
        """
        Args:
            maxsize: 最大キャッシュサイズ
            ttl_seconds: TTL（秒）、Noneの場合は無期限
        """
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, datetime] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str, default: Any = None) -> Any:
        """
        キャッシュから値を取得

        Args:
            key: キー
            default: キーが存在しない場合のデフォルト値

        Returns:
            キャッシュされた値またはデフォルト値
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            # TTLチェック
            if self.ttl_seconds and key in self._timestamps:
                if datetime.now() - self._timestamps[key] > timedelta(seconds=self.ttl_seconds):
                    self._cache.pop(key, None)
                    self._timestamps.pop(key, None)
                    self._misses += 1
                    return default

            # LRU更新
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """
        キャッシュに値を設定

        Args:
            key: キー
            value: 値
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    oldest_key = next(iter(self._cache))
                    self._cache.pop(oldest_key)
                    self._timestamps.pop(oldest_key, None)

            self._cache[key] = value
            self._timestamps[key] = datetime.now()

    def delete(self, key: str) -> bool:
        """
        キャッシュから値を削除

        Args:
            key: キー

        Returns:
            削除成功時True
        """
        with self._lock:
            if key in self._cache:
                self._cache.pop(key)
                self._timestamps.pop(key, None)
                return True
            return False

    def clear(self) -> None:
        """キャッシュをクリア"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """
        キャッシュ統計を取得

        Returns:
            統計情報辞書
        """
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": self._hits / total if total > 0 else 0,
            }


def cached(maxsize: int = 128, ttl_seconds: Optional[int] = None, key_func: Callable = None):
    """
    関数結果をキャッシュするデコレータ

    Args:
        maxsize: 最大キャッシュサイズ
        ttl_seconds: TTL（秒）
        key_func: キャッシュキー生成関数

    使用例:
        @cached(maxsize=100, ttl_seconds=300)
        def expensive_function(arg1, arg2):
            pass
    """

    def decorator(func: Callable) -> Callable:
        cache = LRUCache(maxsize=maxsize, ttl_seconds=ttl_seconds)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # キャッシュキーの生成
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = str((args, tuple(sorted(kwargs.items()))))

            # キャッシュチェック
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 関数実行とキャッシュ
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result

        # キャッシュ操作用メソッドを追加
        wrapper.cache = cache
        wrapper.cache_clear = cache.clear
        wrapper.cache_stats = cache.stats

        return wrapper

    return decorator


class SessionSizeOptimizer:
    """セッションサイズ最適化ユーティリティ"""

    # セッションデータの最大サイズ（バイト）
    MAX_SESSION_SIZE = 1024 * 1024  # 1MB

    # 履歴の最大件数
    MAX_HISTORY_ENTRIES = 100

    @staticmethod
    def estimate_size(data: Any) -> int:
        """
        データのサイズを推定

        Args:
            data: 推定対象データ

        Returns:
            推定サイズ（バイト）
        """
        import json

        try:
            return len(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def optimize_history(cls, history: list, max_entries: int = None) -> list:
        """
        履歴データを最適化（古いエントリを削除）

        Args:
            history: 履歴リスト
            max_entries: 最大エントリ数

        Returns:
            最適化された履歴
        """
        max_entries = max_entries or cls.MAX_HISTORY_ENTRIES
        if len(history) > max_entries:
            return history[-max_entries:]
        return history

    @classmethod
    def should_cleanup(cls, session_data: dict) -> bool:
        """
        セッションのクリーンアップが必要か判定

        Args:
            session_data: セッションデータ

        Returns:
            クリーンアップが必要な場合True
        """
        size = cls.estimate_size(session_data)
        return size > cls.MAX_SESSION_SIZE

    @classmethod
    def cleanup_session(cls, session_data: dict) -> dict:
        """
        セッションデータをクリーンアップ

        Args:
            session_data: セッションデータ

        Returns:
            クリーンアップされたセッションデータ
        """
        # 履歴キーのパターン
        history_keys = [k for k in session_data.keys() if "history" in k.lower()]

        for key in history_keys:
            if isinstance(session_data[key], list):
                session_data[key] = cls.optimize_history(session_data[key])
            elif isinstance(session_data[key], dict):
                for sub_key in session_data[key]:
                    if isinstance(session_data[key][sub_key], list):
                        session_data[key][sub_key] = cls.optimize_history(session_data[key][sub_key])

        return session_data


# グローバルキャッシュインスタンス
_scenario_cache = LRUCache(maxsize=100, ttl_seconds=3600)  # 1時間
_prompt_cache = LRUCache(maxsize=50, ttl_seconds=1800)  # 30分


def get_scenario_cache() -> LRUCache:
    """シナリオキャッシュを取得"""
    return _scenario_cache


def get_prompt_cache() -> LRUCache:
    """プロンプトキャッシュを取得"""
    return _prompt_cache


class BusinessMetrics:
    """ビジネスメトリクス収集クラス"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初期化"""
        self.counters: Dict[str, int] = {
            "chat_sessions": 0,
            "scenario_sessions": 0,
            "watch_sessions": 0,
            "scenario_completions": 0,
            "feedback_generations": 0,
            "errors": 0,
        }
        self.start_time = datetime.now()

    def increment(self, metric_name: str, value: int = 1):
        """
        メトリクスをインクリメント

        Args:
            metric_name: メトリクス名
            value: インクリメント値
        """
        with self._lock:
            if metric_name not in self.counters:
                self.counters[metric_name] = 0
            self.counters[metric_name] += value

    def get_counter(self, metric_name: str) -> int:
        """
        カウンター値を取得

        Args:
            metric_name: メトリクス名

        Returns:
            カウンター値
        """
        return self.counters.get(metric_name, 0)

    def get_all_counters(self) -> Dict[str, int]:
        """全カウンターを取得"""
        return self.counters.copy()

    def get_summary(self) -> Dict[str, Any]:
        """
        メトリクスサマリーを取得

        Returns:
            サマリー辞書
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        total_sessions = (
            self.counters["chat_sessions"] + self.counters["scenario_sessions"] + self.counters["watch_sessions"]
        )

        return {
            "counters": self.counters.copy(),
            "uptime_seconds": uptime,
            "total_sessions": total_sessions,
            "completion_rate": (
                self.counters["scenario_completions"] / self.counters["scenario_sessions"]
                if self.counters["scenario_sessions"] > 0
                else 0
            ),
            "error_rate": (self.counters["errors"] / total_sessions if total_sessions > 0 else 0),
        }

    def reset(self):
        """メトリクスをリセット"""
        with self._lock:
            for key in self.counters:
                self.counters[key] = 0
            self.start_time = datetime.now()


def get_business_metrics() -> BusinessMetrics:
    """ビジネスメトリクスインスタンスを取得"""
    return BusinessMetrics()
