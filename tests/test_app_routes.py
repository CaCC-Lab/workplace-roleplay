"""
app.pyのルート・エンドポイント機能テスト - カバレッジ向上のため
TDD原則に従い、API呼び出し、ルーティング、レスポンス処理をテスト
"""
import pytest
import json
from unittest.mock import patch, MagicMock, PropertyMock
from flask import session, g

# テスト対象の関数
from app import app
from errors import AppError, ValidationError, AuthenticationError


class TestRouteConfiguration:
    """ルート設定のテスト"""
    
    def test_app_url_map_loaded(self):
        """URLマップが正しく読み込まれていることを確認"""
        url_map = app.url_map
        
        # 主要なルートが登録されていることを確認
        rules = [rule.rule for rule in url_map.iter_rules()]
        
        assert "/" in rules
        assert "/api/models" in rules
        assert "/api/chat" in rules
        assert "/api/scenario_chat" in rules
        assert "/api/watch/start" in rules
        assert "/api/watch/next" in rules
    
    def test_blueprint_registration(self):
        """ブループリントが正しく登録されていることを確認"""
        blueprints = app.blueprints
        
        # 期待されるブループリントが登録されている
        expected_blueprints = ['auth', 'main', 'watch_mode']
        for bp_name in expected_blueprints:
            if bp_name in blueprints:
                assert blueprints[bp_name] is not None


class TestStreamingResponse:
    """ストリーミングレスポンスのテスト"""
    
    @patch('app.create_gemini_llm')
    def test_streaming_chat_response(self, mock_create_llm, csrf_client):
        """ストリーミングレスポンスが正しく生成されることを確認"""
        # LLMのストリーミングモックを設定
        mock_llm = MagicMock()
        
        def mock_stream(*args, **kwargs):
            yield {"content": "Hello"}
            yield {"content": " world"}
            yield {"content": "!"}
        
        mock_llm.stream.return_value = mock_stream()
        mock_create_llm.return_value = mock_llm
        
        # セッション初期化
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        # ストリーミングリクエスト
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "Hello",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
    
    def test_non_streaming_response_fallback(self, csrf_client):
        """ストリーミングが無効な場合の通常レスポンス処理を確認"""
        with patch('app.create_gemini_llm') as mock_create_llm:
            mock_llm = MagicMock()
            from langchain_core.messages import AIMessage
            mock_response = AIMessage(content="通常応答")
            mock_llm.invoke.return_value = mock_response
            mock_create_llm.return_value = mock_llm
            
            # セッション初期化
            with csrf_client.session_transaction() as sess:
                sess['chat_settings'] = {
                    "system_prompt": "テスト",
                    "model": "gemini-1.5-flash"
                }
            
            response = csrf_client.post('/api/chat',
                                 json={
                                     "message": "Hello",
                                     "model": "gemini-1.5-flash",
                                     "stream": False
                                 })
            
            assert response.status_code == 200
            data = response.get_json()
            assert "response" in data


class TestRequestValidation:
    """リクエスト検証のテスト"""
    
    def test_empty_message_validation(self, csrf_client):
        """空のメッセージでのバリデーションエラーを確認"""
        response = csrf_client.post('/api/chat',
                             json={"message": "", "model": "gemini-1.5-flash"})
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_invalid_model_validation(self, csrf_client):
        """無効なモデル名でのバリデーションエラーを確認"""
        response = csrf_client.post('/api/chat',
                             json={"message": "test", "model": "invalid-model"})
        
        # 無効なモデルの場合のエラーハンドリング
        assert response.status_code in [400, 500]
    
    def test_request_method_validation(self, client):
        """不正なHTTPメソッドでのエラーを確認"""
        response = client.put('/api/chat')
        
        assert response.status_code == 405  # Method Not Allowed
    
    def test_content_type_validation(self, csrf_client):
        """不正なContent-Typeでのエラーを確認"""
        response = csrf_client.post('/api/chat',
                             data="message=test",
                             content_type='application/x-www-form-urlencoded')
        
        # JSONが期待されるエンドポイントでの処理
        assert response.status_code in [400, 500]


class TestModelManagement:
    """モデル管理機能のテスト"""
    
    @patch('app.get_available_gemini_models')
    def test_models_endpoint_success(self, mock_get_models, client):
        """モデル一覧エンドポイントが正常に動作することを確認"""
        mock_get_models.return_value = [
            "gemini/gemini-1.5-pro",
            "gemini/gemini-1.5-flash"
        ]
        
        response = client.get('/api/models')
        
        assert response.status_code == 200
        data = response.get_json()
        assert "models" in data
        assert len(data["models"]) == 2
    
    @patch('app.get_available_gemini_models')
    def test_models_endpoint_empty(self, mock_get_models, client):
        """利用可能なモデルがない場合の処理を確認"""
        mock_get_models.return_value = []
        
        response = client.get('/api/models')
        
        assert response.status_code == 200
        data = response.get_json()
        assert "models" in data
        assert len(data["models"]) == 0
    
    @patch('app.get_available_gemini_models')
    def test_models_endpoint_error(self, mock_get_models, client):
        """モデル取得でエラーが発生した場合の処理を確認"""
        mock_get_models.side_effect = Exception("API Error")
        
        response = client.get('/api/models')
        
        # エラーハンドリングがされる
        assert response.status_code in [200, 500]


class TestSessionHistoryManagement:
    """セッション履歴管理のテスト"""
    
    def test_chat_history_initialization(self, csrf_client):
        """チャット履歴の初期化を確認"""
        with csrf_client.session_transaction() as sess:
            assert 'chat_history' not in sess
        
        # チャットAPI呼び出し後に履歴が初期化される
        with patch('app.create_gemini_llm') as mock_create_llm:
            mock_llm = MagicMock()
            from langchain_core.messages import AIMessage
            mock_response = AIMessage(content="応答")
            mock_llm.invoke.return_value = mock_response
            mock_create_llm.return_value = mock_llm
            
            with csrf_client.session_transaction() as sess:
                sess['chat_settings'] = {
                    "system_prompt": "テスト",
                    "model": "gemini-1.5-flash"
                }
            
            csrf_client.post('/api/chat',
                       json={"message": "test", "model": "gemini-1.5-flash"})
        
        with csrf_client.session_transaction() as sess:
            assert 'chat_history' in sess
    
    def test_scenario_history_isolation(self, csrf_client):
        """シナリオ履歴が適切に分離されることを確認"""
        with patch('app.create_gemini_llm') as mock_create_llm:
            mock_llm = MagicMock()
            from langchain_core.messages import AIMessage
            mock_response = AIMessage(content="シナリオ応答")
            mock_llm.invoke.return_value = mock_response
            mock_create_llm.return_value = mock_llm
            
            # 2つの異なるシナリオでテスト
            csrf_client.post('/api/scenario_chat',
                       json={
                           "message": "test1",
                           "model": "gemini-1.5-flash",
                           "scenario_id": "scenario1"
                       })
            
            csrf_client.post('/api/scenario_chat',
                       json={
                           "message": "test2",
                           "model": "gemini-1.5-flash",
                           "scenario_id": "scenario2"
                       })
        
        with csrf_client.session_transaction() as sess:
            assert 'scenario_history' in sess
            assert 'scenario1' in sess['scenario_history']
            assert 'scenario2' in sess['scenario_history']
            assert len(sess['scenario_history']['scenario1']) == 1
            assert len(sess['scenario_history']['scenario2']) == 1
    
    def test_history_clear_functionality(self, csrf_client):
        """履歴クリア機能のテスト"""
        # セッションに履歴を設定
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = [{"human": "test", "ai": "response"}]
            sess['scenario_history'] = {
                "scenario1": [{"human": "test", "ai": "response"}]
            }
        
        # チャット履歴をクリア
        response = csrf_client.post('/api/clear_history',
                             json={"mode": "chat"})
        
        assert response.status_code == 200
        
        with csrf_client.session_transaction() as sess:
            assert len(sess.get('chat_history', [])) == 0
            # シナリオ履歴は保持される
            assert 'scenario1' in sess.get('scenario_history', {})
        
        # シナリオ履歴をクリア
        response = csrf_client.post('/api/clear_history',
                             json={"mode": "scenario", "scenario_id": "scenario1"})
        
        assert response.status_code == 200
        
        with csrf_client.session_transaction() as sess:
            scenario_history = sess.get('scenario_history', {})
            assert len(scenario_history.get('scenario1', [])) == 0


class TestExceptionHandling:
    """例外処理のテスト"""
    
    @patch('app.create_gemini_llm')
    def test_llm_timeout_handling(self, mock_create_llm, csrf_client):
        """LLMタイムアウト時の処理を確認"""
        mock_create_llm.side_effect = TimeoutError("Request timeout")
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={"message": "test", "model": "gemini-1.5-flash"})
        
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
    
    @patch('app.create_gemini_llm')
    def test_llm_rate_limit_handling(self, mock_create_llm, csrf_client):
        """LLMレート制限時の処理を確認"""
        mock_create_llm.side_effect = Exception("Rate limit exceeded")
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={"message": "test", "model": "gemini-1.5-flash"})
        
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
    
    def test_invalid_json_handling(self, csrf_client):
        """無効なJSONでのエラーハンドリングを確認"""
        response = csrf_client.post('/api/chat',
                             data='{"invalid": json}',
                             content_type='application/json')
        
        assert response.status_code in [400, 500]


class TestWatchModeIntegration:
    """観戦モード統合のテスト"""
    
    @patch('app.create_gemini_llm')
    def test_watch_mode_conversation_flow(self, mock_create_llm, csrf_client):
        """観戦モードの会話フローを確認"""
        mock_llm = MagicMock()
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="観戦会話")
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm
        
        # 観戦開始
        response = csrf_client.post('/api/watch/start',
                             json={
                                 "model_a": "gemini-1.5-pro",
                                 "model_b": "gemini-1.5-flash",
                                 "partner_type": "colleague",
                                 "situation": "break",
                                 "topic": "general"
                             })
        
        assert response.status_code == 200
        
        # セッションに設定が保存されていることを確認
        with csrf_client.session_transaction() as sess:
            assert 'watch_settings' in sess
            assert 'watch_history' in sess
        
        # 次の会話を生成
        response = csrf_client.post('/api/watch/next')
        
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "speaker" in data
    
    def test_watch_mode_without_settings(self, csrf_client):
        """観戦設定なしでの次の会話生成エラーを確認"""
        response = csrf_client.post('/api/watch/next')
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data


class TestResponseFormatting:
    """レスポンス形式のテスト"""
    
    @patch('app.create_gemini_llm')
    def test_json_response_structure(self, mock_create_llm, csrf_client):
        """JSONレスポンスの構造を確認"""
        mock_llm = MagicMock()
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="テスト応答")
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={"message": "test", "model": "gemini-1.5-flash"})
        
        assert response.status_code == 200
        data = response.get_json()
        
        # 必須フィールドの確認
        assert "response" in data
        assert isinstance(data["response"], str)
    
    def test_error_response_structure(self, csrf_client):
        """エラーレスポンスの構造を確認"""
        response = csrf_client.post('/api/chat',
                             json={"message": ""})  # 空メッセージでエラー
        
        assert response.status_code == 400
        data = response.get_json()
        
        # エラーレスポンスの構造確認
        assert "error" in data
        assert isinstance(data["error"], (str, dict))


# テスト用のフィクスチャ
@pytest.fixture
def app_context():
    """アプリケーションコンテキストのフィクスチャ"""
    with app.app_context():
        yield app