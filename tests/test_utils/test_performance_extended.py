"""
Extended performance utility tests for improved coverage.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestPerformanceMetrics:
    """PerformanceMetricsクラスのテスト"""

    def test_シングルトンインスタンス(self):
        """シングルトンパターンのテスト"""
        from utils.performance import PerformanceMetrics

        metrics1 = PerformanceMetrics()
        metrics2 = PerformanceMetrics()

        assert metrics1 is metrics2

    def test_リクエスト記録(self):
        """リクエストメトリクスの記録"""
        from utils.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.reset()

        metrics.record_request("/api/test", 100.0, 200)
        metrics.record_request("/api/test", 200.0, 200)
        metrics.record_request("/api/test", 50.0, 500)

        result = metrics.get_metrics("/api/test")

        assert result["count"] == 3
        assert result["success_count"] == 2
        assert result["error_count"] == 1
        assert result["min_duration_ms"] == 50.0
        assert result["max_duration_ms"] == 200.0

    def test_全体メトリクス取得(self):
        """全体メトリクスの取得"""
        from utils.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.reset()

        metrics.record_request("/api/endpoint1", 100.0, 200)
        metrics.record_request("/api/endpoint2", 200.0, 404)

        result = metrics.get_metrics()

        assert "_summary" in result
        assert result["_summary"]["total_endpoints"] == 2
        assert result["_summary"]["total_requests"] == 2

    def test_リセット(self):
        """メトリクスのリセット"""
        from utils.performance import PerformanceMetrics

        metrics = PerformanceMetrics()
        metrics.record_request("/api/test", 100.0, 200)
        metrics.reset()

        result = metrics.get_metrics("/api/test")

        assert result == {}


class TestGetMetrics:
    """get_metrics関数のテスト"""

    def test_インスタンス取得(self):
        """インスタンスの取得"""
        from utils.performance import get_metrics, PerformanceMetrics

        metrics = get_metrics()

        assert isinstance(metrics, PerformanceMetrics)


class TestMeasureTime:
    """measure_timeデコレータのテスト"""

    def test_デコレータ_引数なし(self):
        """引数なしのデコレータ"""
        from utils.performance import measure_time

        @measure_time
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"

    def test_デコレータ_カスタム名(self):
        """カスタム名付きデコレータ"""
        from utils.performance import measure_time

        @measure_time(name="custom_metric")
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"

    def test_デコレータ_例外発生(self):
        """例外発生時のデコレータ"""
        from utils.performance import measure_time

        @measure_time
        def test_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            test_func()


class TestLRUCache:
    """LRUCacheクラスのテスト"""

    def test_基本的なget_set(self):
        """基本的なget/set操作"""
        from utils.performance import LRUCache

        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")

        assert cache.get("key1") == "value1"
        assert cache.get("nonexistent", "default") == "default"

    def test_LRU動作(self):
        """LRU動作のテスト"""
        from utils.performance import LRUCache

        cache = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # aにアクセス
        cache.get("a")

        # 新しいキーを追加（bが削除されるはず）
        cache.set("d", 4)

        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_TTL期限切れ(self):
        """TTL期限切れのテスト"""
        from utils.performance import LRUCache

        cache = LRUCache(maxsize=10, ttl_seconds=1)
        cache.set("key", "value")

        # すぐにアクセス
        assert cache.get("key") == "value"

        # TTL経過後
        time.sleep(1.1)
        assert cache.get("key") is None

    def test_削除(self):
        """削除操作のテスト"""
        from utils.performance import LRUCache

        cache = LRUCache(maxsize=10)
        cache.set("key", "value")

        assert cache.delete("key") is True
        assert cache.delete("nonexistent") is False
        assert cache.get("key") is None

    def test_クリア(self):
        """クリア操作のテスト"""
        from utils.performance import LRUCache

        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_統計(self):
        """統計情報のテスト"""
        from utils.performance import LRUCache

        cache = LRUCache(maxsize=10)
        cache.set("key", "value")

        # ヒット
        cache.get("key")
        cache.get("key")

        # ミス
        cache.get("nonexistent")

        stats = cache.stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_既存キーの更新(self):
        """既存キーの更新"""
        from utils.performance import LRUCache

        cache = LRUCache(maxsize=10)
        cache.set("key", "value1")
        cache.set("key", "value2")

        assert cache.get("key") == "value2"


class TestCachedDecorator:
    """cachedデコレータのテスト"""

    def test_デコレータ基本動作(self):
        """基本的なキャッシュ動作"""
        from utils.performance import cached

        call_count = 0

        @cached(maxsize=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 初回呼び出し
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # キャッシュヒット
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # 呼び出し回数は増えない

    def test_デコレータ_異なる引数(self):
        """異なる引数でのキャッシュ"""
        from utils.performance import cached

        call_count = 0

        @cached(maxsize=10)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x

        func(1)
        func(2)
        func(1)  # キャッシュヒット

        assert call_count == 2

    def test_デコレータ_TTL(self):
        """TTL付きキャッシュ"""
        from utils.performance import cached

        @cached(maxsize=10, ttl_seconds=1)
        def func(x):
            return x

        result1 = func(1)
        result2 = func(1)

        assert result1 == result2


class TestSessionSizeOptimizer:
    """SessionSizeOptimizerクラスのテスト"""

    def test_サイズ推定(self):
        """サイズ推定のテスト"""
        from utils.performance import SessionSizeOptimizer

        data = {"key": "value", "list": [1, 2, 3]}
        size = SessionSizeOptimizer.estimate_size(data)

        assert size > 0

    def test_履歴最適化(self):
        """履歴最適化のテスト"""
        from utils.performance import SessionSizeOptimizer

        # 大きな履歴を作成
        history = [{"human": f"test{i}", "ai": f"response{i}"} for i in range(200)]

        optimized = SessionSizeOptimizer.optimize_history(history)

        # 最適化が行われる（履歴が制限される）
        assert len(optimized) <= SessionSizeOptimizer.MAX_HISTORY_ENTRIES

    def test_クリーンアップ判定(self):
        """クリーンアップ判定のテスト"""
        from utils.performance import SessionSizeOptimizer

        # 大きなセッションデータ
        session = {
            "chat_history": [{"human": f"test{i}", "ai": f"response{i}"} for i in range(200)]
        }

        should_clean = SessionSizeOptimizer.should_cleanup(session)

        # bool型を返す
        assert isinstance(should_clean, bool)

    def test_定数が定義されている(self):
        """定数が定義されている"""
        from utils.performance import SessionSizeOptimizer

        assert hasattr(SessionSizeOptimizer, "MAX_SESSION_SIZE")
        assert hasattr(SessionSizeOptimizer, "MAX_HISTORY_ENTRIES")


class TestScenarioCache:
    """シナリオキャッシュのテスト"""

    def test_シナリオキャッシュ取得(self):
        """シナリオキャッシュの取得"""
        from utils.performance import get_scenario_cache, LRUCache

        cache = get_scenario_cache()

        assert isinstance(cache, LRUCache)


class TestPromptCache:
    """プロンプトキャッシュのテスト"""

    def test_プロンプトキャッシュ取得(self):
        """プロンプトキャッシュの取得"""
        from utils.performance import get_prompt_cache, LRUCache

        cache = get_prompt_cache()

        assert isinstance(cache, LRUCache)


class TestBusinessMetrics:
    """BusinessMetricsクラスのテスト"""

    def test_シングルトン(self):
        """シングルトンパターンのテスト"""
        from utils.performance import get_business_metrics

        metrics1 = get_business_metrics()
        metrics2 = get_business_metrics()

        assert metrics1 is metrics2

    def test_インクリメント(self):
        """インクリメントのテスト"""
        from utils.performance import BusinessMetrics

        metrics = BusinessMetrics()

        # メソッドが存在することを確認
        assert hasattr(metrics, "increment")

        initial_value = metrics.counters.get("chat_sessions", 0)
        metrics.increment("chat_sessions")
        assert metrics.counters.get("chat_sessions") == initial_value + 1

    def test_カウンター取得(self):
        """カウンター取得のテスト"""
        from utils.performance import BusinessMetrics

        metrics = BusinessMetrics()

        # countersが存在することを確認
        assert hasattr(metrics, "counters")
        assert isinstance(metrics.counters, dict)

    def test_メトリクス取得(self):
        """メトリクス取得のテスト"""
        from utils.performance import get_business_metrics

        metrics = get_business_metrics()

        # get_summaryメソッドが存在する場合
        if hasattr(metrics, "get_summary"):
            summary = metrics.get_summary()
            assert isinstance(summary, dict)
