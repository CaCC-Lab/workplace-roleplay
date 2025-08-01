"""
履歴ルートの統合テスト
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from flask import Flask
from routes.history_routes import history_bp


class TestHistoryRoutes:
    """履歴ルートの統合テストクラス"""
    
    @pytest.fixture
    def app(self):
        """テスト用Flaskアプリケーション"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['TESTING'] = True
        app.register_blueprint(history_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """テストクライアント"""
        return app.test_client()
    
    def test_get_learning_history_正常系(self, client):
        """学習履歴取得の正常系テスト"""
        with patch('routes.history_routes.SessionService') as mock_session:
            # モックデータの設定
            mock_session.get_session_history.side_effect = lambda key, sub=None: {
                'chat_history': [
                    {'user': 'こんにちは', 'assistant': 'こんにちは！', 'timestamp': '2025-07-31T10:00:00'}
                ],
                'watch_history': []
            }.get(key, [])
            
            mock_session.get_session_data.return_value = {
                'scenario_001': [{'user': 'test', 'character': 'response'}]
            }
            
            response = client.get('/api/learning_history')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'chat' in data
            assert 'scenarios' in data
            assert 'watch' in data
            assert 'overall' in data
            
            assert data['chat']['count'] == 1
            assert data['overall']['total_activities'] >= 1
    
    def test_get_chat_history_正常系(self, client):
        """チャット履歴取得の正常系テスト"""
        with patch('routes.history_routes.SessionService') as mock_session:
            mock_history = [
                {'user': 'テスト1', 'assistant': '応答1'},
                {'user': 'テスト2', 'assistant': '応答2'}
            ]
            mock_session.get_session_history.return_value = mock_history
            mock_session.get_session_start_time.return_value = '2025-07-31T09:00:00'
            
            response = client.get('/api/chat_history')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'history' in data
            assert 'count' in data
            assert 'start_time' in data
            assert data['count'] == 2
    
    def test_get_scenario_history_正常系(self, client):
        """シナリオ履歴取得の正常系テスト"""
        with patch('routes.history_routes.SessionService') as mock_session, \
             patch('routes.history_routes.load_scenarios') as mock_load:
            
            mock_session.get_session_history.return_value = [
                {'user': 'プレゼンします', 'character': '続けてください'}
            ]
            mock_session.get_session_start_time.return_value = '2025-07-31T10:00:00'
            
            mock_load.return_value = {
                'scenario_001': {'title': 'プレゼンテーション練習'}
            }
            
            response = client.get('/api/scenario_history/scenario_001')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert data['scenario_id'] == 'scenario_001'
            assert data['scenario_title'] == 'プレゼンテーション練習'
            assert data['count'] == 1
    
    def test_clear_all_history_正常系(self, client):
        """全履歴クリアの正常系テスト"""
        with patch('routes.history_routes.SessionService') as mock_session:
            response = client.post('/api/clear_all_history')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'message' in data
            assert 'cleared' in data
            assert 'chat' in data['cleared']
            assert 'scenarios' in data['cleared']
            assert 'watch' in data['cleared']
            
            # クリア関数が呼ばれたことを確認
            assert mock_session.clear_session_history.call_count == 3
    
    def test_get_learning_history_エラー時(self, client):
        """学習履歴取得エラー時の処理"""
        with patch('routes.history_routes.SessionService') as mock_session:
            mock_session.get_session_history.side_effect = Exception("データベースエラー")
            
            response = client.get('/api/learning_history')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data