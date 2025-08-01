"""
観戦モードルートの統合テスト
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from flask import Flask
from routes.watch_routes import watch_bp


class TestWatchRoutes:
    """観戦モードルートの統合テストクラス"""
    
    @pytest.fixture
    def app(self):
        """テスト用Flaskアプリケーション"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['TESTING'] = True
        app.register_blueprint(watch_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """テストクライアント"""
        return app.test_client()
    
    def test_start_watch_正常系(self, client):
        """観戦モード開始の正常系テスト"""
        with patch('routes.watch_routes.WatchService') as mock_service:
            mock_result = {
                'partner1_type': '同僚',
                'partner2_type': '友人',
                'topic': '日常',
                'model': 'gemini-1.5-flash',
                'first_message': 'こんにちは',
                'current_speaker': 'AI1'
            }
            mock_service.start_watch_mode.return_value = mock_result
            
            response = client.post('/api/watch/start',
                                 json={'topic': '日常'},
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data == mock_result
    
    def test_next_watch_message_正常系(self, client):
        """次のメッセージ生成の正常系テスト"""
        with patch('routes.watch_routes.WatchService') as mock_service:
            mock_result = {
                'speaker': 'AI2',
                'partner_type': '友人',
                'message': 'こんにちは！元気ですか？',
                'next_speaker': 'AI1'
            }
            mock_service.generate_next_message.return_value = mock_result
            
            response = client.post('/api/watch/next')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data == mock_result
    
    def test_get_watch_summary_正常系(self, client):
        """観戦サマリー取得の正常系テスト"""
        with patch('routes.watch_routes.WatchService') as mock_service:
            mock_summary = {
                'total_messages': 10,
                'participants': ['同僚', '友人'],
                'ai1_messages': 5,
                'ai2_messages': 5
            }
            mock_service.get_watch_summary.return_value = mock_summary
            
            response = client.get('/api/watch/summary')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data == mock_summary
    
    def test_get_partner_types_正常系(self, client):
        """パートナータイプ一覧取得の正常系テスト"""
        with patch('routes.watch_routes.WatchService') as mock_service:
            mock_service.PARTNER_TYPES = {
                '同僚': '職場の同僚として会話',
                '友人': '親しい友人として会話'
            }
            
            response = client.get('/api/watch/partner_types')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'partner_types' in data
            assert len(data['partner_types']) == 2
    
    def test_get_topics_正常系(self, client):
        """話題一覧取得の正常系テスト"""
        with patch('routes.watch_routes.WatchService') as mock_service:
            mock_service.TOPICS = {
                '仕事': '仕事の話題',
                '日常': '日常会話'
            }
            
            response = client.get('/api/watch/topics')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'topics' in data
            assert len(data['topics']) == 2