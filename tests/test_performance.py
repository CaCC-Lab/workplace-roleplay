"""
パフォーマンスユーティリティのテスト
"""
import pytest
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.performance import (
    LRUCache,
    PerformanceMetrics,
    SessionSizeOptimizer,
    cached,
    get_metrics,
    measure_time,
)


class TestLRUCache:
    """LRUキャッシュのテスト"""
    
    def test_basic_set_get(self):
        """基本的なset/get操作"""
        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_default_value(self):
        """存在しないキーのデフォルト値"""
        cache = LRUCache(maxsize=10)
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"
    
    def test_maxsize_eviction(self):
        """最大サイズを超えた場合の削除"""
        cache = LRUCache(maxsize=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # key1が削除されるはず
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_lru_order(self):
        """LRU順序の確認"""
        cache = LRUCache(maxsize=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # key1にアクセスして最新にする
        cache.get("key1")
        
        # 新しいキーを追加（key2が削除されるはず）
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_ttl_expiration(self):
        """TTL期限切れのテスト"""
        cache = LRUCache(maxsize=10, ttl_seconds=1)
        cache.set("key1", "value1")
        
        assert cache.get("key1") == "value1"
        
        time.sleep(1.1)  # TTLを超えて待つ
        
        assert cache.get("key1") is None
    
    def test_delete(self):
        """削除操作"""
        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("nonexistent") is False
    
    def test_clear(self):
        """クリア操作"""
        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_stats(self):
        """統計情報"""
        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.5


class TestPerformanceMetrics:
    """パフォーマンスメトリクスのテスト"""
    
    def test_singleton(self):
        """シングルトンパターン"""
        metrics1 = PerformanceMetrics()
        metrics2 = PerformanceMetrics()
        assert metrics1 is metrics2
    
    def test_record_request(self):
        """リクエスト記録"""
        metrics = get_metrics()
        metrics.reset()
        
        metrics.record_request("/api/test", 100.0, 200)
        metrics.record_request("/api/test", 200.0, 200)
        
        data = metrics.get_metrics("/api/test")
        assert data["count"] == 2
        assert data["total_duration_ms"] == 300.0
        assert data["min_duration_ms"] == 100.0
        assert data["max_duration_ms"] == 200.0
        assert data["success_count"] == 2
        assert data["error_count"] == 0
    
    def test_error_count(self):
        """エラーカウント"""
        metrics = get_metrics()
        metrics.reset()
        
        metrics.record_request("/api/error", 50.0, 500)
        
        data = metrics.get_metrics("/api/error")
        assert data["error_count"] == 1
        assert data["success_count"] == 0
    
    def test_get_all_metrics(self):
        """全メトリクス取得"""
        metrics = get_metrics()
        metrics.reset()
        
        metrics.record_request("/api/test1", 100.0, 200)
        metrics.record_request("/api/test2", 200.0, 201)
        
        all_data = metrics.get_metrics()
        assert "/api/test1" in all_data
        assert "/api/test2" in all_data
        assert "_summary" in all_data
        assert all_data["_summary"]["total_requests"] == 2


class TestCachedDecorator:
    """cachedデコレータのテスト"""
    
    def test_basic_caching(self):
        """基本的なキャッシュ動作"""
        call_count = 0
        
        @cached(maxsize=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        result1 = expensive_function(5)
        result2 = expensive_function(5)
        
        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # 2回目はキャッシュから
    
    def test_different_args(self):
        """異なる引数でのキャッシュ"""
        call_count = 0
        
        @cached(maxsize=10)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        result1 = expensive_function(5)
        result2 = expensive_function(10)
        
        assert result1 == 10
        assert result2 == 20
        assert call_count == 2
    
    def test_cache_clear(self):
        """キャッシュクリア"""
        @cached(maxsize=10)
        def expensive_function(x):
            return x * 2
        
        expensive_function(5)
        expensive_function.cache_clear()
        
        stats = expensive_function.cache_stats()
        assert stats["size"] == 0


class TestMeasureTimeDecorator:
    """measure_timeデコレータのテスト"""
    
    def test_basic_timing(self):
        """基本的な時間計測"""
        @measure_time
        def slow_function():
            time.sleep(0.01)
            return "done"
        
        result = slow_function()
        assert result == "done"
    
    def test_custom_name(self):
        """カスタム名での計測"""
        @measure_time(name="custom_metric")
        def some_function():
            return "done"
        
        result = some_function()
        assert result == "done"


class TestSessionSizeOptimizer:
    """セッションサイズ最適化のテスト"""
    
    def test_estimate_size(self):
        """サイズ推定"""
        data = {"key": "value", "number": 123}
        size = SessionSizeOptimizer.estimate_size(data)
        assert size > 0
    
    def test_optimize_history(self):
        """履歴最適化"""
        history = [{"id": i} for i in range(150)]
        optimized = SessionSizeOptimizer.optimize_history(history)
        
        assert len(optimized) == 100
        assert optimized[0]["id"] == 50  # 古いものが削除される
    
    def test_optimize_history_short(self):
        """短い履歴は変更なし"""
        history = [{"id": i} for i in range(10)]
        optimized = SessionSizeOptimizer.optimize_history(history)
        
        assert len(optimized) == 10
    
    def test_cleanup_session(self):
        """セッションクリーンアップ"""
        session_data = {
            "user_id": "test",
            "chat_history": [{"msg": i} for i in range(150)],
            "other_key": "value"
        }
        
        cleaned = SessionSizeOptimizer.cleanup_session(session_data)
        
        assert len(cleaned["chat_history"]) == 100
        assert cleaned["user_id"] == "test"
        assert cleaned["other_key"] == "value"
