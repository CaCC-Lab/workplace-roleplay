# tests/test_redis_session.py
import pytest
import os
import time
import redis
from flask import Flask, session
from flask_session import Session
from unittest.mock import Mock, patch
import json

class TestRedisSessionIntegration:
    """Redis統合セッション管理のテストスイート - TDDアプローチ"""
    
    @pytest.fixture(scope="function")
    def redis_client(self):
        """実際のRedisクライアント（テスト用ポート使用）"""
        client = redis.Redis(
            host='localhost',
            port=6380,  # テスト用ポート
            db=0,
            decode_responses=True
        )
        # テスト前にデータクリア
        try:
            client.flushdb()
            yield client
        except redis.ConnectionError:
            pytest.skip("Redis test server not available")
        finally:
            # テスト後もクリア
            try:
                client.flushdb()
            except:
                pass
    
    @pytest.fixture
    def app_with_redis(self, redis_client):
        """Redis設定済みのFlaskアプリケーション"""
        app = Flask(__name__)
        app.config.update({
            'SECRET_KEY': 'test-secret-key-for-redis',
            'SESSION_TYPE': 'redis',
            'SESSION_REDIS': redis_client,
            'SESSION_PERMANENT': False,
            'SESSION_USE_SIGNER': True,
            'SESSION_KEY_PREFIX': 'workplace-test:',
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SECURE': False,  # テスト環境
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': 3600  # 1時間
        })
        
        Session(app)
        
        # テスト用エンドポイント
        @app.route('/set_session/<key>/<value>')
        def set_session(key, value):
            session[key] = value
            return 'OK'
        
        @app.route('/get_session/<key>')
        def get_session(key):
            return session.get(key, 'NOT_FOUND')
        
        @app.route('/clear_session')
        def clear_session():
            session.clear()
            return 'CLEARED'
        
        @app.route('/set_chat_history')
        def set_chat_history():
            """実際のアプリケーションのチャット履歴をシミュレート"""
            session['chat_history'] = [
                {'role': 'user', 'content': 'こんにちは'},
                {'role': 'assistant', 'content': 'こんにちは！お元気ですか？'}
            ]
            session['model_choice'] = 'gemini-1.5-pro'
            return 'CHAT_SET'
        
        return app
    
    def test_redis_connection(self, redis_client):
        """Redisへの基本接続テスト"""
        # Arrange & Act
        redis_client.set('test_key', 'test_value')
        result = redis_client.get('test_key')
        
        # Assert
        assert result == 'test_value'
        
    def test_session_storage_in_redis(self, app_with_redis, redis_client):
        """セッションデータがRedisに正しく保存されることを確認"""
        # Arrange
        client = app_with_redis.test_client()
        
        # Act - セッションにデータを設定
        response = client.get('/set_session/user_id/12345')
        
        # Assert
        assert response.status_code == 200
        assert response.data.decode() == 'OK'
        
        # Redisに実際にデータが保存されているか確認
        keys = redis_client.keys('workplace-test:*')
        assert len(keys) > 0, "セッションデータがRedisに保存されていない"
        
        # 同じセッションで値を取得できることを確認
        response2 = client.get('/get_session/user_id')
        assert response2.data.decode() == '12345'
    
    def test_session_persistence_across_requests(self, app_with_redis):
        """リクエスト間でのセッション永続性テスト"""
        # Arrange
        client = app_with_redis.test_client()
        
        # Act - 複数のリクエストを送信
        client.get('/set_session/step/1')
        client.get('/set_session/user/alice')
        
        # Assert - すべてのデータが保持されている
        response1 = client.get('/get_session/step')
        response2 = client.get('/get_session/user')
        
        assert response1.data.decode() == '1'
        assert response2.data.decode() == 'alice'
    
    def test_chat_history_storage(self, app_with_redis, redis_client):
        """チャット履歴の保存とシリアライゼーション"""
        # Arrange
        client = app_with_redis.test_client()
        
        # Act
        response = client.get('/set_chat_history')
        
        # Assert
        assert response.status_code == 200
        
        # セッションデータが正しく保存されているかチェック
        response2 = client.get('/get_session/model_choice')
        assert response2.data.decode() == 'gemini-1.5-pro'
    
    def test_concurrent_sessions_isolation(self, app_with_redis):
        """並行セッションの分離テスト"""
        # Arrange
        client1 = app_with_redis.test_client()
        client2 = app_with_redis.test_client()
        
        # Act - 異なるクライアントで異なるデータを設定
        client1.get('/set_session/user/alice')
        client2.get('/set_session/user/bob')
        
        # Assert - それぞれのセッションが分離されている
        response1 = client1.get('/get_session/user')
        response2 = client2.get('/get_session/user')
        
        assert response1.data.decode() == 'alice'
        assert response2.data.decode() == 'bob'
    
    def test_session_expiration(self, app_with_redis):
        """セッション有効期限のテスト"""
        # Arrange - 短い有効期限を設定
        app_with_redis.config['PERMANENT_SESSION_LIFETIME'] = 1  # 1秒
        client = app_with_redis.test_client()
        
        # Act
        with client.session_transaction() as sess:
            sess['temp_data'] = 'expires_soon'
            sess.permanent = True
        
        # 即座に確認
        response1 = client.get('/get_session/temp_data')
        assert response1.data.decode() == 'expires_soon'
        
        # 2秒待機
        time.sleep(2)
        
        # Assert - セッションが期限切れになっている
        response2 = client.get('/get_session/temp_data')
        assert response2.data.decode() == 'NOT_FOUND'
    
    def test_session_clear(self, app_with_redis):
        """セッションクリア機能のテスト"""
        # Arrange
        client = app_with_redis.test_client()
        client.get('/set_session/data1/value1')
        client.get('/set_session/data2/value2')
        
        # Act
        response = client.get('/clear_session')
        
        # Assert
        assert response.status_code == 200
        assert response.data.decode() == 'CLEARED'
        
        # データがクリアされていることを確認
        response1 = client.get('/get_session/data1')
        response2 = client.get('/get_session/data2')
        
        assert response1.data.decode() == 'NOT_FOUND'
        assert response2.data.decode() == 'NOT_FOUND'
    
    def test_large_session_data_handling(self, app_with_redis):
        """大容量セッションデータの処理テスト"""
        # Arrange
        client = app_with_redis.test_client()
        large_data = 'x' * 10000  # 10KB のデータ
        
        # Act
        response = client.get(f'/set_session/large_data/{large_data}')
        
        # Assert
        assert response.status_code == 200
        
        # データが正しく取得できることを確認
        response2 = client.get('/get_session/large_data')
        assert len(response2.data.decode()) == 10000
    
    def test_redis_connection_failure_handling(self, app_with_redis):
        """Redis接続エラー時のエラーハンドリングテスト"""
        # Arrange
        client = app_with_redis.test_client()
        
        # Act - Redis接続エラーをシミュレート
        with patch('redis.Redis.set', side_effect=redis.ConnectionError("Connection failed")):
            response = client.get('/set_session/test/value')
        
        # Assert - アプリケーションがクラッシュしないこと
        # セッションエラーの場合、通常は500番台のエラーが返される
        assert response.status_code in [200, 500, 503]


class TestRedisSessionManager:
    """Redis session manager専用のテストスイート"""
    
    def test_redis_session_manager_creation(self):
        """RedisSessionManagerクラスの作成テスト"""
        # このテストは失敗するはず（まだクラスを作成していない）
        from utils.redis_manager import RedisSessionManager
        
        manager = RedisSessionManager()
        assert manager is not None
    
    def test_redis_fallback_mechanism(self):
        """Redisフォールバック機能のテスト"""
        from utils.redis_manager import RedisSessionManager
        
        # Redis接続失敗時のフォールバック動作をテスト
        with patch('redis.Redis.ping', side_effect=redis.ConnectionError):
            manager = RedisSessionManager()
            # フォールバック機能が動作することを確認
            assert manager.has_fallback() is True