"""
モデルルートの統合テスト
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from flask import Flask
from routes.model_routes import model_bp


class TestModelRoutes:
    """モデルルートの統合テストクラス"""
    
    @pytest.fixture
    def app(self):
        """テスト用Flaskアプリケーション"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['TESTING'] = True
        app.register_blueprint(model_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """テストクライアント"""
        return app.test_client()
    
    def test_get_models_endpoint_正常系(self, client):
        """利用可能なモデル取得エンドポイントの正常系テスト"""
        with patch('routes.model_routes.LLMService') as mock_llm_service, \
             patch('routes.model_routes.SessionService') as mock_session_service:
            
            # モックの設定
            mock_models = {
                'gemini/gemini-1.5-pro': {
                    'description': 'プロモデル',
                    'temperature': 0.7,
                    'max_tokens': 8192
                },
                'gemini/gemini-1.5-flash': {
                    'description': 'フラッシュモデル',
                    'temperature': 0.9,
                    'max_tokens': 4096
                }
            }
            mock_llm_service.get_available_models.return_value = mock_models
            mock_session_service.get_session_data.return_value = 'gemini-1.5-flash'
            
            response = client.get('/api/models')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'models' in data
            assert len(data['models']) == 2
            assert data['selected'] == 'gemini-1.5-flash'
            
            # モデル情報の確認
            flash_model = next(m for m in data['models'] if m['name'] == 'gemini-1.5-flash')
            assert flash_model['selected'] is True
            assert flash_model['description'] == 'フラッシュモデル'
    
    def test_get_models_endpoint_エラー時(self, client):
        """モデル取得エラー時の処理"""
        with patch('routes.model_routes.LLMService') as mock_llm_service:
            mock_llm_service.get_available_models.side_effect = Exception("API error")
            
            response = client.get('/api/models')
            
            assert response.status_code == 200  # エラーでも200を返す
            data = json.loads(response.data)
            assert data['models'] == []
            assert 'error' in data
    
    def test_select_model_endpoint_正常系(self, client):
        """モデル選択エンドポイントの正常系テスト"""
        with patch('routes.model_routes.LLMService') as mock_llm_service, \
             patch('routes.model_routes.SessionService') as mock_session_service:
            
            mock_models = {
                'gemini/gemini-1.5-flash': {'description': 'test'}
            }
            mock_llm_service.get_available_models.return_value = mock_models
            
            response = client.post('/api/select_model',
                                 json={'model': 'gemini-1.5-flash'},
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'message' in data
            assert 'gemini-1.5-flash' in data['message']
            
            # セッションへの保存を確認
            mock_session_service.set_session_data.assert_called_once_with('selected_model', 'gemini-1.5-flash')
    
    def test_select_model_endpoint_モデル名なし(self, client):
        """モデル名が指定されていない場合のエラー"""
        response = client.post('/api/select_model',
                             json={},
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'モデル名が指定されていません' in data['error']
    
    def test_get_model_info_endpoint_正常系(self, client):
        """モデル詳細情報取得エンドポイントの正常系テスト"""
        with patch('routes.model_routes.LLMService') as mock_llm_service:
            mock_models = {
                'gemini/gemini-1.5-pro': {
                    'description': '高性能モデル',
                    'temperature': 0.7,
                    'max_tokens': 8192
                }
            }
            mock_llm_service.get_available_models.return_value = mock_models
            
            response = client.get('/api/model_info/gemini-1.5-pro')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['name'] == 'gemini-1.5-pro'
            assert data['description'] == '高性能モデル'
            assert data['temperature'] == 0.7
            assert data['max_tokens'] == 8192
    
    def test_get_model_info_endpoint_モデルが見つからない(self, client):
        """存在しないモデルの詳細取得時のエラー"""
        with patch('routes.model_routes.LLMService') as mock_llm_service:
            mock_llm_service.get_available_models.return_value = {}
            
            response = client.get('/api/model_info/non-existent-model')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data
            assert 'モデルが見つかりません' in data['error']