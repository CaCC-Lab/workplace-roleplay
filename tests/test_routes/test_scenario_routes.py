"""
シナリオルートの統合テスト
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from flask import Flask
from routes.scenario_routes import scenario_bp


class TestScenarioRoutes:
    """シナリオルートの統合テストクラス"""
    
    @pytest.fixture
    def app(self):
        """テスト用Flaskアプリケーション"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['TESTING'] = True
        app.register_blueprint(scenario_bp)
        return app
    
    @pytest.fixture
    def client(self, app):
        """テストクライアント"""
        return app.test_client()
    
    @pytest.fixture
    def mock_scenarios(self):
        """モックシナリオデータ"""
        return {
            'scenario_001': {
                'id': 'scenario_001',
                'title': 'プレゼンテーション練習',
                'description': '上司への提案練習',
                'difficulty': '中級',
                'tags': ['ビジネス', 'プレゼン'],
                'character': {
                    'name': '田中部長',
                    'role': '上司'
                }
            },
            'scenario_002': {
                'id': 'scenario_002',
                'title': '電話応対',
                'description': 'クレーム対応の練習',
                'difficulty': '上級',
                'tags': ['電話', 'クレーム'],
                'character': {
                    'name': '山田様',
                    'role': '顧客'
                }
            }
        }
    
    def test_get_scenarios_正常系(self, client, mock_scenarios):
        """シナリオ一覧取得の正常系テスト"""
        with patch('routes.scenario_routes.load_scenarios', return_value=mock_scenarios):
            response = client.get('/api/scenarios')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'scenarios' in data
            assert 'total' in data
            assert data['total'] == 2
            
            # シナリオ情報の確認
            scenario = data['scenarios'][0]
            assert 'id' in scenario
            assert 'title' in scenario
            assert 'character' in scenario
    
    def test_get_scenarios_エラー時(self, client):
        """シナリオ一覧取得エラー時の処理"""
        with patch('routes.scenario_routes.load_scenarios', side_effect=Exception("読み込みエラー")):
            response = client.get('/api/scenarios')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_get_scenario_正常系(self, client, mock_scenarios):
        """特定シナリオ取得の正常系テスト"""
        with patch('routes.scenario_routes.ScenarioService') as mock_service:
            mock_service.get_scenario.return_value = mock_scenarios['scenario_001']
            
            response = client.get('/api/scenario/scenario_001')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['title'] == 'プレゼンテーション練習'
    
    def test_get_scenario_存在しない場合(self, client):
        """存在しないシナリオ取得時のエラー"""
        with patch('routes.scenario_routes.ScenarioService') as mock_service:
            from errors import NotFoundError
            mock_service.get_scenario.side_effect = NotFoundError("シナリオが見つかりません")
            
            response = client.get('/api/scenario/non_existent')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_scenario_chat_正常系(self, client):
        """シナリオチャットの正常系テスト"""
        with patch('routes.scenario_routes.ScenarioService') as mock_service:
            # ストリーミングレスポンスのモック
            mock_service.handle_scenario_message.return_value = [
                'data: {"content": "了解しました", "type": "content"}\n\n',
                'data: {"type": "done"}\n\n'
            ]
            
            response = client.post('/api/scenario_chat',
                                 json={'scenario_id': 'scenario_001', 'message': 'テスト'},
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            assert response.content_type.startswith('text/event-stream')
    
    def test_scenario_feedback_正常系(self, client):
        """シナリオフィードバックの正常系テスト"""
        with patch('routes.scenario_routes.ScenarioService') as mock_service:
            mock_feedback = {
                'feedback': '良いコミュニケーションでした',
                'scenario_id': 'scenario_001',
                'conversation_count': 5,
                'model': 'gemini-1.5-flash'
            }
            mock_service.generate_scenario_feedback.return_value = mock_feedback
            
            response = client.post('/api/scenario_feedback',
                                 json={'scenario_id': 'scenario_001'},
                                 headers={'Content-Type': 'application/json'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data == mock_feedback
    
    def test_scenario_feedback_IDなしエラー(self, client):
        """シナリオIDなしでのフィードバックエラー"""
        response = client.post('/api/scenario_feedback',
                             json={},
                             headers={'Content-Type': 'application/json'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'シナリオID' in data['error']
    
    def test_clear_scenario_正常系(self, client):
        """シナリオ履歴クリアの正常系テスト"""
        with patch('routes.scenario_routes.ScenarioService') as mock_service:
            mock_service.clear_scenario_history.return_value = {'message': 'クリアしました'}
            
            response = client.post('/api/clear_scenario/scenario_001')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['message'] == 'クリアしました'
    
    def test_get_initial_message_正常系(self, client):
        """初期メッセージ取得の正常系テスト"""
        with patch('routes.scenario_routes.ScenarioService') as mock_service:
            mock_service.get_initial_message.return_value = 'それでは始めましょう'
            
            response = client.get('/api/scenario/scenario_001/initial_message')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['initial_message'] == 'それでは始めましょう'
            assert data['has_message'] is True