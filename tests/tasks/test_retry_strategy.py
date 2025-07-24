"""
Celeryタスクリトライ戦略のテスト
"""
import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from celery import Task
from celery.exceptions import Retry
import redis

from tasks.retry_strategy import (
    RetryConfig, RetryStrategy, PartialResponseManager,
    retry_with_backoff, track_streaming_chunks, get_retry_status
)
from tasks.exceptions import (
    RateLimitError, NetworkError, ServiceUnavailableError,
    TemporaryLLMError, AuthenticationError
)


class TestRetryConfig:
    """RetryConfig データクラスのテスト"""
    
    def test_retry_config_creation(self):
        """RetryConfig作成のテスト"""
        config = RetryConfig(
            max_retries=5,
            base_delay=60,
            max_delay=600,
            backoff_factor=1.5,
            jitter=True
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 60
        assert config.max_delay == 600
        assert config.backoff_factor == 1.5
        assert config.jitter is True
    
    def test_retry_config_defaults(self):
        """RetryConfigデフォルト値のテスト"""
        config = RetryConfig(
            max_retries=3,
            base_delay=10,
            max_delay=100,
            backoff_factor=2.0
        )
        
        assert config.jitter is True  # デフォルト値


class TestRetryStrategy:
    """RetryStrategy クラスのテスト"""
    
    def test_get_retry_config_rate_limit(self):
        """レート制限エラーの設定取得テスト"""
        error = RateLimitError("rate limit exceeded")
        config = RetryStrategy.get_retry_config(error)
        
        assert config.max_retries == 5
        assert config.base_delay == 60
        assert config.max_delay == 600
        assert config.backoff_factor == 1.5
    
    def test_get_retry_config_network_error(self):
        """ネットワークエラーの設定取得テスト"""
        error = NetworkError("connection failed")
        config = RetryStrategy.get_retry_config(error)
        
        assert config.max_retries == 4
        assert config.base_delay == 1
        assert config.max_delay == 30
        assert config.backoff_factor == 2.0
    
    def test_get_retry_config_unknown_error(self):
        """未知のエラーのデフォルト設定テスト"""
        error = TemporaryLLMError("unknown temporary error")
        config = RetryStrategy.get_retry_config(error)
        
        # デフォルトはTemporaryLLMErrorの設定
        assert config.max_retries == 3
        assert config.base_delay == 2
        assert config.max_delay == 300
        assert config.backoff_factor == 2.0
    
    def test_calculate_delay_basic(self):
        """基本的な遅延計算テスト"""
        config = RetryConfig(
            max_retries=3,
            base_delay=10,
            max_delay=100,
            backoff_factor=2.0,
            jitter=False  # ジッターを無効にして予測可能にする
        )
        error = NetworkError("test error")
        
        # retry_count = 0: 10 * (2.0 ^ 0) = 10
        delay0 = RetryStrategy.calculate_delay(0, config, error)
        assert delay0 == 10
        
        # retry_count = 1: 10 * (2.0 ^ 1) = 20
        delay1 = RetryStrategy.calculate_delay(1, config, error)
        assert delay1 == 20
        
        # retry_count = 2: 10 * (2.0 ^ 2) = 40
        delay2 = RetryStrategy.calculate_delay(2, config, error)
        assert delay2 == 40
    
    def test_calculate_delay_with_max_delay(self):
        """最大遅延時間制限のテスト"""
        config = RetryConfig(
            max_retries=5,
            base_delay=50,
            max_delay=100,
            backoff_factor=3.0,
            jitter=False
        )
        error = NetworkError("test error")
        
        # retry_count = 2: 50 * (3.0 ^ 2) = 450, but max is 100
        delay = RetryStrategy.calculate_delay(2, config, error)
        assert delay == 100
    
    def test_calculate_delay_with_retry_after(self):
        """エラー固有の推奨待機時間使用テスト"""
        config = RetryConfig(
            max_retries=3,
            base_delay=10,
            max_delay=100,
            backoff_factor=2.0,
            jitter=False
        )
        error = RateLimitError("rate limit", retry_after=30)
        
        # retry_count = 0: 30 * (2.0 ^ 0) = 30 (base_delay=10は無視)
        delay = RetryStrategy.calculate_delay(0, config, error)
        assert delay == 30
    
    def test_calculate_delay_with_jitter(self):
        """ジッター有効時の遅延計算テスト"""
        config = RetryConfig(
            max_retries=3,
            base_delay=100,
            max_delay=1000,
            backoff_factor=1.0,  # 指数増加なし
            jitter=True
        )
        error = NetworkError("test error")
        
        # ジッターがあるので複数回実行して範囲をテスト
        delays = [RetryStrategy.calculate_delay(0, config, error) for _ in range(10)]
        
        # 基本は100秒、±10%のジッター = 90-110秒の範囲
        assert all(90 <= delay <= 110 for delay in delays)
        # ジッターによりすべて同じ値にはならない（高確率で）
        assert len(set(delays)) > 1
    
    def test_should_retry_temporary_error(self):
        """一時的エラーのリトライ判定テスト"""
        error = NetworkError("connection failed")
        
        # リトライ回数が上限未満の場合
        should_retry, reason = RetryStrategy.should_retry(error, 2)
        assert should_retry is True
        assert "Temporary error" in reason
        assert "3/4" in reason  # retry 3/4
    
    def test_should_retry_permanent_error(self):
        """永続的エラーのリトライ判定テスト"""
        error = AuthenticationError("invalid api key")
        
        should_retry, reason = RetryStrategy.should_retry(error, 0)
        assert should_retry is False
        assert "Permanent error" in reason
        assert "AuthenticationError" in reason
    
    def test_should_retry_max_retries_exceeded(self):
        """リトライ上限超過のテスト"""
        error = NetworkError("connection failed")
        
        # NetworkErrorの上限は4回
        should_retry, reason = RetryStrategy.should_retry(error, 4)
        assert should_retry is False
        assert "Max retries (4) exceeded" in reason


class TestPartialResponseManager:
    """PartialResponseManager クラスのテスト"""
    
    @patch('tasks.retry_strategy.redis_client')
    def test_save_partial_response(self, mock_redis):
        """部分レスポンス保存のテスト"""
        task_id = "test-task-123"
        chunks = [
            {"content": "Hello", "timestamp": 1234567890, "chunk_index": 0},
            {"content": " world", "timestamp": 1234567891, "chunk_index": 1}
        ]
        metadata = {"error_occurred": True, "error_type": "NetworkError"}
        
        PartialResponseManager.save_partial_response(task_id, chunks, metadata)
        
        # Redis呼び出しの確認
        expected_key = f"partial_response:{task_id}"
        mock_redis.setex.assert_called_once()
        
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == expected_key
        assert call_args[0][1] == PartialResponseManager.PARTIAL_RESPONSE_TTL
        
        # 保存されるデータの確認
        saved_data = json.loads(call_args[0][2])
        assert saved_data['chunks'] == chunks
        assert saved_data['metadata'] == metadata
        assert saved_data['total_chunks'] == 2
        assert 'saved_at' in saved_data
    
    @patch('tasks.retry_strategy.redis_client')
    def test_get_partial_response_exists(self, mock_redis):
        """部分レスポンス取得（存在する場合）のテスト"""
        task_id = "test-task-123"
        stored_data = {
            "chunks": [{"content": "test", "chunk_index": 0}],
            "metadata": {"test": True},
            "saved_at": 1234567890,
            "total_chunks": 1
        }
        mock_redis.get.return_value = json.dumps(stored_data)
        
        result = PartialResponseManager.get_partial_response(task_id)
        
        assert result == stored_data
        mock_redis.get.assert_called_once_with(f"partial_response:{task_id}")
    
    @patch('tasks.retry_strategy.redis_client')
    def test_get_partial_response_not_exists(self, mock_redis):
        """部分レスポンス取得（存在しない場合）のテスト"""
        task_id = "test-task-123"
        mock_redis.get.return_value = None
        
        result = PartialResponseManager.get_partial_response(task_id)
        
        assert result is None
        mock_redis.get.assert_called_once_with(f"partial_response:{task_id}")
    
    @patch('tasks.retry_strategy.redis_client')
    def test_delete_partial_response(self, mock_redis):
        """部分レスポンス削除のテスト"""
        task_id = "test-task-123"
        
        PartialResponseManager.delete_partial_response(task_id)
        
        mock_redis.delete.assert_called_once_with(f"partial_response:{task_id}")
    
    def test_reconstruct_content(self):
        """コンテンツ再構築のテスト"""
        chunks = [
            {"content": " world", "chunk_index": 1},
            {"content": "Hello", "chunk_index": 0},
            {"content": "!", "chunk_index": 2}
        ]
        
        content = PartialResponseManager.reconstruct_content(chunks)
        
        assert content == "Hello world!"
    
    def test_reconstruct_content_missing_index(self):
        """インデックス不足での再構築テスト"""
        chunks = [
            {"content": "Hello"},  # chunk_indexなし
            {"content": " world", "chunk_index": 1}
        ]
        
        content = PartialResponseManager.reconstruct_content(chunks)
        
        # インデックス0とみなされる
        assert content == "Hello world"


class TestTrackStreamingChunks:
    """track_streaming_chunks 関数のテスト"""
    
    def test_track_streaming_chunks_first_chunk(self):
        """最初のチャンク追跡テスト"""
        mock_task = Mock()
        chunk_data = {
            "content": "Hello",
            "timestamp": 1234567890
        }
        
        track_streaming_chunks(mock_task, chunk_data)
        
        assert hasattr(mock_task, '_partial_chunks')
        assert len(mock_task._partial_chunks) == 1
        
        chunk_info = mock_task._partial_chunks[0]
        assert chunk_info['content'] == "Hello"
        assert chunk_info['timestamp'] == 1234567890
        assert chunk_info['chunk_index'] == 0
    
    def test_track_streaming_chunks_multiple_chunks(self):
        """複数チャンクの追跡テスト"""
        mock_task = Mock()
        
        chunks = [
            {"content": "Hello", "timestamp": 1234567890},
            {"content": " ", "timestamp": 1234567891},
            {"content": "world", "timestamp": 1234567892}
        ]
        
        for chunk_data in chunks:
            track_streaming_chunks(mock_task, chunk_data)
        
        assert len(mock_task._partial_chunks) == 3
        
        # インデックスが正しく設定されているか確認
        for i, chunk_info in enumerate(mock_task._partial_chunks):
            assert chunk_info['chunk_index'] == i
            assert chunk_info['content'] == chunks[i]['content']
    
    def test_track_streaming_chunks_with_speaker(self):
        """話者情報付きチャンク追跡テスト"""
        mock_task = Mock()
        chunk_data = {
            "content": "Hello",
            "timestamp": 1234567890,
            "speaker": "Assistant"
        }
        
        track_streaming_chunks(mock_task, chunk_data)
        
        chunk_info = mock_task._partial_chunks[0]
        assert chunk_info['speaker'] == "Assistant"


class TestGetRetryStatus:
    """get_retry_status 関数のテスト"""
    
    @patch('tasks.retry_strategy.PartialResponseManager.get_partial_response')
    def test_get_retry_status_no_partial_response(self, mock_get_partial):
        """部分レスポンスがない場合のステータステスト"""
        task_id = "test-task-123"
        mock_get_partial.return_value = None
        
        status = get_retry_status(task_id)
        
        expected = {
            'task_id': task_id,
            'has_partial_response': False,
            'partial_chunks_count': 0,
            'last_error_type': None,
            'retry_count': 0
        }
        
        assert status == expected
    
    @patch('tasks.retry_strategy.PartialResponseManager.get_partial_response')
    def test_get_retry_status_with_partial_response(self, mock_get_partial):
        """部分レスポンスがある場合のステータステスト"""
        task_id = "test-task-123"
        partial_data = {
            'total_chunks': 5,
            'saved_at': 1234567890,
            'metadata': {
                'error_type': 'NetworkError',
                'retry_count': 2,
                'error_occurred': True
            }
        }
        mock_get_partial.return_value = partial_data
        
        status = get_retry_status(task_id)
        
        expected = {
            'task_id': task_id,
            'has_partial_response': True,
            'partial_chunks_count': 5,
            'saved_at': 1234567890,
            'metadata': partial_data['metadata'],
            'last_error_type': 'NetworkError',
            'retry_count': 2
        }
        
        assert status == expected


class TestRetryWithBackoffDecorator:
    """retry_with_backoff デコレータのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_task = Mock(spec=Task)
        self.mock_task.request = Mock()
        self.mock_task.request.id = "test-task-123"
        self.mock_task.request.retries = 0
        self.mock_task.retry = Mock(side_effect=Retry("mocked retry"))
    
    @patch('tasks.retry_strategy.redis_client')
    @patch('tasks.retry_strategy.PartialResponseManager')
    def test_successful_execution(self, mock_partial_manager, mock_redis):
        """正常実行時のテスト"""
        @retry_with_backoff
        def test_task(task_self, session_id, data):
            return {"status": "success", "data": data}
        
        result = test_task(self.mock_task, "session-123", "test-data")
        
        assert result == {"status": "success", "data": "test-data"}
        # 成功時は部分レスポンスを削除
        mock_partial_manager.delete_partial_response.assert_called_once_with("test-task-123")
    
    @patch('tasks.retry_strategy.redis_client')
    @patch('tasks.retry_strategy.PartialResponseManager')
    @patch('tasks.retry_strategy.classify_error')
    def test_permanent_error_no_retry(self, mock_classify, mock_partial_manager, mock_redis):
        """永続的エラーでリトライしない場合のテスト"""
        original_error = Exception("authentication failed")
        classified_error = AuthenticationError("invalid api key")
        
        mock_classify.return_value = classified_error
        mock_partial_manager.get_partial_response.return_value = None
        
        @retry_with_backoff
        def test_task(task_self, session_id):
            raise original_error
        
        with pytest.raises(AuthenticationError):
            test_task(self.mock_task, "session-123")
        
        # エラー通知が送信されるか確認
        mock_redis.publish.assert_called()
        
        # リトライは実行されない
        self.mock_task.retry.assert_not_called()
    
    @patch('tasks.retry_strategy.redis_client')
    @patch('tasks.retry_strategy.PartialResponseManager')
    @patch('tasks.retry_strategy.classify_error')
    def test_temporary_error_with_retry(self, mock_classify, mock_partial_manager, mock_redis):
        """一時的エラーでリトライする場合のテスト"""
        original_error = Exception("connection failed")
        classified_error = NetworkError("network error")
        
        mock_classify.return_value = classified_error
        
        @retry_with_backoff
        def test_task(task_self, session_id):
            raise original_error
        
        with pytest.raises(Retry):  # Celeryリトライ例外が発生
            test_task(self.mock_task, "session-123")
        
        # リトライ通知が送信されるか確認
        mock_redis.publish.assert_called()
        
        # Celeryリトライが実行される
        self.mock_task.retry.assert_called_once()
        
        # リトライパラメータの確認
        retry_call = self.mock_task.retry.call_args
        assert 'countdown' in retry_call[1]
        assert 'exc' in retry_call[1]
        assert 'max_retries' in retry_call[1]
        assert retry_call[1]['exc'] is classified_error
    
    @patch('tasks.retry_strategy.redis_client')
    @patch('tasks.retry_strategy.PartialResponseManager')
    @patch('tasks.retry_strategy.classify_error')
    def test_with_partial_response(self, mock_classify, mock_partial_manager, mock_redis):
        """部分レスポンスがある場合のテスト"""
        original_error = Exception("connection failed")
        classified_error = NetworkError("network error")
        
        mock_classify.return_value = classified_error
        
        # 部分レスポンスを持つタスクをシミュレート
        self.mock_task._partial_chunks = [
            {"content": "Hello", "chunk_index": 0},
            {"content": " world", "chunk_index": 1}
        ]
        
        @retry_with_backoff
        def test_task(task_self, session_id):
            raise original_error
        
        with pytest.raises(Retry):
            test_task(self.mock_task, "session-123")
        
        # 部分レスポンスが保存されるか確認
        mock_partial_manager.save_partial_response.assert_called_once()
        save_call = mock_partial_manager.save_partial_response.call_args
        assert save_call[0][0] == "test-task-123"  # task_id
        assert save_call[0][1] == self.mock_task._partial_chunks  # chunks
        assert save_call[0][2]['error_occurred'] is True  # metadata


@pytest.fixture
def mock_redis():
    """Redisクライアントのモック"""
    with patch('tasks.retry_strategy.redis_client') as mock:
        yield mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])