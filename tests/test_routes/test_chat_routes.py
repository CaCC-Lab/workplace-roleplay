"""
チャットルートの統合テスト
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from flask import Flask
from routes.chat_routes import chat_bp


class TestChatRoutes:
    """チャットルートの統合テストクラス"""
    
    @pytest.fixture
    def app(self):
        """テスト用Flaskアプリケーション"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['TESTING'] = True
        app.register_blueprint(chat_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """テストクライアント"""
        return app.test_client()
    
    def test_chat_endpoint_正常系(self, client):
        """チャットエンドポイントの正常系テスト"""
        with patch('routes.chat_routes.ChatService') as mock_service:
            # ストリーミングレスポンスのモック
            mock_service.handle_chat_message.return_value = [
                'data: {"content": "こんにちは", "type": "content"}\n\n',
                'data: {"type": "done"}\n\n'
            ]
            
            response = client.post('/api/chat', 
                                 json={'message': 'テストメッセージ'},
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            assert response.content_type.startswith('text/event-stream')
            
            # レスポンスの内容を確認
            data = response.get_data(as_text=True)
            assert 'こんにちは' in data
            assert '"type": "done"' in data
    
    def test_chat_endpoint_空メッセージ(self, client):
        """空メッセージでのエラー処理"""
        with patch('routes.chat_routes.ChatService') as mock_service:
            from errors import ValidationError
            mock_service.handle_chat_message.side_effect = ValidationError("メッセージを入力してください")
            
            response = client.post('/api/chat', 
                                 json={'message': ''},
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data
            assert 'メッセージを入力してください' in data['error']
    
    def test_chat_feedback_endpoint_正常系(self, client):
        """フィードバックエンドポイントの正常系テスト"""
        with patch('routes.chat_routes.ChatService') as mock_service:
            mock_feedback = {
                'feedback': '良い会話でした',
                'conversation_count': 5,
                'model': 'gemini-1.5-flash'
            }
            mock_service.generate_chat_feedback.return_value = mock_feedback
            
            response = client.post('/api/chat_feedback')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data == mock_feedback
    
    def test_clear_chat_endpoint_正常系(self, client):
        """チャット履歴クリアエンドポイントの正常系テスト"""
        with patch('routes.chat_routes.ChatService') as mock_service:
            mock_service.clear_chat_history.return_value = {'message': 'チャット履歴をクリアしました'}
            
            response = client.post('/api/clear_chat')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['message'] == 'チャット履歴をクリアしました'