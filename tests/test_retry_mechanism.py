"""
リトライ機構のテスト
"""
import unittest
import time
import json
from unittest.mock import Mock, patch, MagicMock
import redis
import pytest

# テスト用のインポート
from tasks.exceptions import (
    RateLimitError, NetworkError, ServiceUnavailableError,
    InvalidRequestError, AuthenticationError, classify_gemini_error
)
from tasks.retry_strategy import RetryConfig, calculate_retry_delay, RetryableTask


class TestExceptionClassification(unittest.TestCase):
    """エラー分類のテスト"""
    
    def test_classify_rate_limit_error(self):
        """レート制限エラーの分類テスト"""
        error = Exception("Rate limit exceeded: 429")
        classified = classify_gemini_error(error)
        self.assertIsInstance(classified, RateLimitError)
    
    def test_classify_network_error(self):
        """ネットワークエラーの分類テスト"""
        error = Exception("Connection timeout")
        classified = classify_gemini_error(error)
        self.assertIsInstance(classified, NetworkError)
    
    def test_classify_authentication_error(self):
        """認証エラーの分類テスト"""
        error = Exception("401 Unauthorized: Invalid API key")
        classified = classify_gemini_error(error)
        self.assertIsInstance(classified, AuthenticationError)
    
    def test_classify_invalid_request_error(self):
        """無効リクエストエラーの分類テスト"""
        error = Exception("400 Bad Request: Invalid parameters")
        classified = classify_gemini_error(error)
        self.assertIsInstance(classified, InvalidRequestError)


class TestRetryStrategy(unittest.TestCase):
    """リトライ戦略のテスト"""
    
    def test_calculate_retry_delay_exponential_backoff(self):
        """指数バックオフの計算テスト"""
        # 基本的な指数バックオフ
        delay1 = calculate_retry_delay(0, base_delay=2, backoff_multiplier=2.0)
        delay2 = calculate_retry_delay(1, base_delay=2, backoff_multiplier=2.0)
        delay3 = calculate_retry_delay(2, base_delay=2, backoff_multiplier=2.0)
        
        # ジッターを考慮して範囲でテスト
        self.assertGreaterEqual(delay1, 1)
        self.assertLessEqual(delay1, 3)
        
        self.assertGreaterEqual(delay2, 3)
        self.assertLessEqual(delay2, 5)
        
        self.assertGreaterEqual(delay3, 6)
        self.assertLessEqual(delay3, 10)
    
    def test_calculate_retry_delay_max_limit(self):
        """最大遅延時間の制限テスト"""
        delay = calculate_retry_delay(10, base_delay=10, max_delay=30, backoff_multiplier=2.0)
        self.assertLessEqual(delay, 35)  # ジッターを考慮
    
    def test_calculate_retry_delay_rate_limit_with_retry_after(self):
        """Retry-After付きレート制限エラーのテスト"""
        rate_limit_error = RateLimitError("Rate limit", retry_after=60)
        delay = calculate_retry_delay(1, error=rate_limit_error)
        
        # Retry-Afterの値を優先
        self.assertGreaterEqual(delay, 54)  # 60秒 - ジッター
        self.assertLessEqual(delay, 66)     # 60秒 + ジッター
    
    def test_retry_config_per_error_type(self):
        """エラータイプ別設定のテスト"""
        rate_limit_config = RetryConfig.get_config(RateLimitError)
        network_config = RetryConfig.get_config(NetworkError)
        
        # レート制限エラーはより多くのリトライと長い待機時間
        self.assertGreater(rate_limit_config['max_retries'], network_config['max_retries'])
        self.assertGreater(rate_limit_config['base_delay'], network_config['base_delay'])


class TestRetryableTask(unittest.TestCase):
    """RetryableTaskのテスト"""
    
    def setUp(self):
        """テスト初期化"""
        self.task = RetryableTask()
        self.task.request = Mock()
        self.task.request.id = 'test-task-id'
        self.task.request.retries = 0
        
        # Redisのモック
        self.redis_mock = Mock()
        self.task.get_redis_client = Mock(return_value=self.redis_mock)
    
    def test_save_partial_response(self):
        """部分レスポンス保存のテスト"""
        partial_data = {
            'content': 'テスト応答の一部',
            'timestamp': time.time()
        }
        
        # 既存データなし
        self.redis_mock.get.return_value = None
        
        self.task.save_partial_response('test-task-id', partial_data)
        
        # Redis操作の確認
        self.redis_mock.get.assert_called_once()
        self.redis_mock.setex.assert_called_once()
        
        # 保存されたデータの構造確認
        call_args = self.redis_mock.setex.call_args
        saved_data = json.loads(call_args[0][2])
        
        self.assertIn('chunks', saved_data)
        self.assertIn('metadata', saved_data)
        self.assertEqual(len(saved_data['chunks']), 1)
        self.assertEqual(saved_data['chunks'][0]['content'], 'テスト応答の一部')
    
    def test_get_partial_response(self):
        """部分レスポンス取得のテスト"""
        test_data = {
            'chunks': [
                {'content': 'chunk1', 'timestamp': time.time(), 'chunk_index': 0},
                {'content': 'chunk2', 'timestamp': time.time(), 'chunk_index': 1}
            ],
            'metadata': {'error_occurred': False}
        }
        
        self.redis_mock.get.return_value = json.dumps(test_data)
        
        result = self.task.get_partial_response('test-task-id')
        
        self.assertEqual(result, test_data)
        self.assertEqual(len(result['chunks']), 2)
    
    def test_publish_progress(self):
        """進捗通知のテスト"""
        progress_message = {
            'status': 'retrying',
            'retry_count': 1,
            'error': 'Test error'
        }
        
        self.task.publish_progress('test-task-id', progress_message)
        
        # Redis pub/subの確認
        expected_channel = 'task_progress:test-task-id'
        self.redis_mock.publish.assert_called_once_with(
            expected_channel, 
            json.dumps(progress_message)
        )
    
    @patch('tasks.retry_strategy.classify_gemini_error')
    def test_retry_with_strategy_permanent_error(self, mock_classify):
        """永続的エラーでのリトライ停止テスト"""
        # 永続的エラーとして分類
        mock_classify.return_value = AuthenticationError("Invalid API key")
        
        with self.assertRaises(AuthenticationError):
            self.task.retry_with_strategy(
                Exception("Invalid API key"),
                ('arg1', 'arg2'),
                {'kwarg1': 'value1'}
            )
        
        # 進捗通知が送信されているか確認
        self.redis_mock.publish.assert_called_once()
        call_args = self.redis_mock.publish.call_args
        published_data = json.loads(call_args[0][1])
        
        self.assertEqual(published_data['status'], 'failed')
        self.assertEqual(published_data['error_type'], 'permanent')
        self.assertFalse(published_data['retry_possible'])
    
    @patch('tasks.retry_strategy.classify_gemini_error')
    def test_retry_with_strategy_max_retries(self, mock_classify):
        """最大リトライ回数到達テスト"""
        # 一時的エラーとして分類
        mock_classify.return_value = NetworkError("Connection failed")
        
        # 最大リトライ回数に設定
        self.task.request.retries = 4  # NetworkErrorの最大リトライ回数
        
        with self.assertRaises(NetworkError):
            self.task.retry_with_strategy(
                Exception("Connection failed"),
                ('arg1', 'arg2'),
                {'kwarg1': 'value1'}
            )
        
        # 進捗通知が送信されているか確認
        self.redis_mock.publish.assert_called_once()
        call_args = self.redis_mock.publish.call_args
        published_data = json.loads(call_args[0][1])
        
        self.assertEqual(published_data['status'], 'failed')
        self.assertEqual(published_data['error_type'], 'max_retries_exceeded')
    
    @patch('tasks.retry_strategy.classify_gemini_error')
    def test_retry_with_strategy_successful_retry(self, mock_classify):
        """正常なリトライのテスト"""
        # 一時的エラーとして分類
        network_error = NetworkError("Connection failed")
        mock_classify.return_value = network_error
        
        # retryメソッドをモック
        self.task.retry = Mock(side_effect=Exception("Retry called"))
        
        with self.assertRaises(Exception) as context:
            self.task.retry_with_strategy(
                Exception("Connection failed"),
                ('arg1', 'arg2'),
                {'kwarg1': 'value1'}
            )
        
        # retryが呼ばれていることを確認
        self.task.retry.assert_called_once()
        retry_call = self.task.retry.call_args
        
        self.assertEqual(retry_call[1]['exc'], network_error)
        self.assertGreater(retry_call[1]['countdown'], 0)
        self.assertEqual(retry_call[1]['max_retries'], 4)  # NetworkErrorの設定
        
        # 進捗通知の確認
        self.redis_mock.publish.assert_called_once()
        call_args = self.redis_mock.publish.call_args
        published_data = json.loads(call_args[0][1])
        
        self.assertEqual(published_data['status'], 'retrying')
        self.assertEqual(published_data['retry_count'], 1)
        self.assertGreater(published_data['retry_delay'], 0)


class TestIntegration(unittest.TestCase):
    """統合テスト"""
    
    @patch('tasks.llm.redis_client')
    @patch('tasks.llm.ChatGoogleGenerativeAI')
    def test_stream_chat_response_with_retry(self, mock_llm_class, mock_redis):
        """stream_chat_responseタスクのリトライ統合テスト"""
        from tasks.llm import stream_chat_response
        
        # LLMインスタンスをモック
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        # 初回は失敗、2回目は成功のパターン
        mock_llm.stream.side_effect = [
            Exception("Rate limit exceeded"),  # 初回エラー
            [Mock(content="テスト応答")]        # リトライ後成功
        ]
        
        # タスクインスタンスを作成
        task_instance = stream_chat_response
        task_instance.request = Mock()
        task_instance.request.id = 'test-task-id'
        task_instance.request.retries = 0
        
        # 1回目の実行（エラー）
        with self.assertRaises(Exception):
            result = stream_chat_response(
                'test-session',
                'gemini-pro',
                [{'role': 'user', 'content': 'テストメッセージ'}]
            )


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)