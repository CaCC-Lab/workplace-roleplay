"""
APIキーマネージャーのテスト
TDD原則に従い、まずテストを作成してから実装を改善する
"""
import os
import time
import pytest
from unittest.mock import patch, MagicMock
from api_key_manager import APIKeyManager, get_google_api_key, handle_api_error, record_api_usage, get_api_key_manager, _api_key_manager


class TestAPIKeyManager:
    """APIKeyManagerクラスのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される"""
        # グローバルインスタンスをリセット
        import api_key_manager
        api_key_manager._api_key_manager = None
    
    def test_初期化時に環境変数からAPIキーを読み込む(self, mock_env_vars):
        """環境変数から複数のAPIキーが正しく読み込まれることを確認"""
        manager = APIKeyManager()
        
        assert len(manager.api_keys) == 4
        assert 'mock-key-1' in manager.api_keys
        assert 'mock-key-2' in manager.api_keys
        assert 'mock-key-3' in manager.api_keys
        assert 'mock-key-4' in manager.api_keys
    
    def test_環境変数にAPIキーがない場合はエラー(self):
        """APIキーが見つからない場合、ValueErrorが発生することを確認"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No Google API keys found"):
                APIKeyManager()
    
    def test_get_next_keyは使用可能なキーを返す(self, mock_env_vars):
        """get_next_keyが利用可能なAPIキーを返すことを確認"""
        manager = APIKeyManager()
        
        key = manager.get_next_key()
        assert key is not None
        assert key in manager.api_keys
    
    def test_使用回数が最も少ないキーが優先される(self, mock_env_vars):
        """使用回数が少ないキーが優先的に選択されることを確認"""
        manager = APIKeyManager()
        
        # 最初の3つのキーを使用
        for i in range(3):
            key = manager.get_next_key()
            manager.record_usage(key)
            time.sleep(0.1)  # レート制限回避のため少し待つ
        
        # 4つ目のキーが選択されるはず（使用回数0）
        next_key = manager.get_next_key()
        assert manager.usage_counts[next_key] == 0
    
    def test_レート制限の遵守(self, mock_env_vars):
        """同じキーが4秒以内に再使用されないことを確認"""
        manager = APIKeyManager()
        
        first_key = manager.get_next_key()
        manager.record_usage(first_key)
        
        # すぐに次のキーを要求
        second_key = manager.get_next_key()
        
        # 同じキーが返されないことを確認（他のキーが利用可能な場合）
        if len(manager.api_keys) > 1:
            assert first_key != second_key
    
    def test_エラー記録とブロック機能(self, mock_env_vars):
        """エラーが記録され、レート制限エラーでキーがブロックされることを確認"""
        manager = APIKeyManager()
        
        key = manager.get_next_key()
        error = Exception("Error 429: insufficient_quota")
        
        # エラーを記録
        manager.record_error(key, error)
        
        # エラーカウントが増加
        assert manager.error_counts[key] == 1
        
        # キーがブロックされている
        assert manager.blocked_until[key] > time.time()
    
    def test_全キーがブロックされた場合の動作(self, mock_env_vars):
        """全てのキーがブロックされた場合、最も早く解除されるキーが返されることを確認"""
        manager = APIKeyManager()
        current_time = time.time()
        
        # 全てのキーをブロック（異なる解除時刻）
        for i, key in enumerate(manager.api_keys):
            manager.blocked_until[key] = current_time + (i + 1) * 10
        
        # 最も早く解除されるキー（最初のキー）が返される
        next_key = manager.get_next_key()
        assert next_key == manager.api_keys[0]
    
    def test_ステータス取得機能(self, mock_env_vars):
        """get_statusが正しい形式でステータス情報を返すことを確認"""
        manager = APIKeyManager()
        
        # いくつかのキーを使用
        key1 = manager.get_next_key()
        manager.record_usage(key1)
        
        # ステータスを取得
        status = manager.get_status()
        
        assert 'total_keys' in status
        assert status['total_keys'] == 4
        assert 'keys' in status
        assert len(status['keys']) == 4
        
        # 各キーのステータス情報を確認
        for key_status in status['keys']:
            assert 'index' in key_status
            assert 'key_suffix' in key_status
            assert 'usage_count' in key_status
            assert 'error_count' in key_status
            assert 'is_blocked' in key_status
    
    def test_日次カウンターのリセット(self, mock_env_vars):
        """reset_daily_countersがカウンターを正しくリセットすることを確認"""
        manager = APIKeyManager()
        
        # カウンターを増やす
        key = manager.get_next_key()
        manager.record_usage(key)
        manager.record_error(key, Exception("test error"))
        
        assert manager.usage_counts[key] > 0
        assert manager.error_counts[key] > 0
        
        # リセット
        manager.reset_daily_counters()
        
        assert manager.usage_counts[key] == 0
        assert manager.error_counts[key] == 0


class TestHelperFunctions:
    """ヘルパー関数のテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される"""
        # グローバルインスタンスをリセット
        import api_key_manager
        api_key_manager._api_key_manager = None
    
    @patch('api_key_manager.get_api_key_manager')
    def test_get_google_api_key関数(self, mock_get_manager):
        """get_google_api_key関数が正しく動作することを確認"""
        mock_manager = MagicMock()
        mock_manager.get_next_key.return_value = "test-key"
        mock_get_manager.return_value = mock_manager
        
        key = get_google_api_key()
        
        assert key == "test-key"
        mock_manager.get_next_key.assert_called_once()
    
    @patch('api_key_manager.get_api_key_manager')
    def test_get_google_api_keyは利用可能なキーがない場合エラー(self, mock_get_manager):
        """利用可能なキーがない場合、例外が発生することを確認"""
        mock_manager = MagicMock()
        mock_manager.get_next_key.return_value = None
        mock_get_manager.return_value = mock_manager
        
        with pytest.raises(Exception, match="No available API keys"):
            get_google_api_key()
    
    @patch('api_key_manager.get_api_key_manager')
    def test_handle_api_error関数(self, mock_get_manager):
        """handle_api_error関数がエラーを正しく記録することを確認"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        test_key = "test-key"
        test_error = Exception("Test error")
        
        handle_api_error(test_key, test_error)
        
        mock_manager.record_error.assert_called_once_with(test_key, test_error)
    
    @patch('api_key_manager.get_api_key_manager')
    def test_record_api_usage関数(self, mock_get_manager):
        """record_api_usage関数が使用を正しく記録することを確認"""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        test_key = "test-key"
        
        record_api_usage(test_key)
        
        mock_manager.record_usage.assert_called_once_with(test_key)


class TestEdgeCases:
    """エッジケースのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される"""
        # グローバルインスタンスをリセット
        import api_key_manager
        api_key_manager._api_key_manager = None
    
    def test_大量のAPIキーの処理(self):
        """多数のAPIキーが登録されている場合の動作を確認"""
        # 20個のAPIキーを環境変数に設定
        env_vars = {'GOOGLE_API_KEY': 'key-0'}
        for i in range(1, 20):
            env_vars[f'GOOGLE_API_KEY_{i}'] = f'key-{i}'
        
        with patch.dict(os.environ, env_vars):
            manager = APIKeyManager()
            
            # 最大9個までしか読み込まれない（仕様）
            assert len(manager.api_keys) <= 10
    
    def test_同時アクセス時のキー選択(self, mock_env_vars):
        """複数のリクエストが同時に来た場合のキー選択を確認"""
        manager = APIKeyManager()
        
        keys = []
        for _ in range(10):
            key = manager.get_next_key()
            if key:
                keys.append(key)
                manager.record_usage(key)
                time.sleep(0.01)  # 短い間隔でリクエスト
        
        # 複数の異なるキーが使用されていることを確認
        unique_keys = set(keys)
        assert len(unique_keys) > 1  # ローテーションが機能している
    
    def test_長時間ブロックされたキーの処理(self, mock_env_vars):
        """長時間ブロックされたキーが正しく解除されることを確認"""
        manager = APIKeyManager()
        
        key = manager.get_next_key()
        
        # 1秒間ブロック
        manager.blocked_until[key] = time.time() + 1
        
        # ブロック中は使用不可
        time.sleep(0.1)
        next_key = manager.get_next_key()
        if len(manager.api_keys) > 1:
            assert next_key != key
        
        # ブロック解除後は使用可能
        time.sleep(1)
        available_keys = []
        for _ in range(len(manager.api_keys)):
            k = manager.get_next_key()
            if k == key:
                available_keys.append(k)
                break
            manager.record_usage(k)
            time.sleep(0.1)
        
        assert key in available_keys or len(manager.api_keys) == 1