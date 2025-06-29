"""
Flask APIエンドポイントの統合テスト
TDD原則に従い、APIの振る舞いをテスト
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from flask import session
import time


class TestAPIEndpoints:
    """基本的なAPIエンドポイントのテスト"""
    
    def test_ホームページが正常に表示される(self, client):
        """ルートURLが正常にレンダリングされることを確認"""
        response = client.get('/')
        
        assert response.status_code == 200
        # 日本語を含むテキストの確認（デコードして確認）
        data = response.get_data(as_text=True)
        assert "職場コミュニケーション練習アプリ" in data
        assert "シナリオロールプレイ" in data
    
    def test_利用可能なモデルリストが取得できる(self, client):
        """GET /api/models が正しいモデルリストを返すことを確認"""
        response = client.get('/api/models')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "models" in data
        assert len(data["models"]) > 0
        # Geminiモデルが含まれていることを確認
        assert any("gemini" in model["id"] for model in data["models"])
    
    def test_存在しないエンドポイントは404を返す(self, client):
        """存在しないURLへのアクセスが404を返すことを確認"""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404


class TestChatAPI:
    """雑談モードAPIのテスト"""
    
    @patch('app.create_gemini_llm')
    def test_チャットAPIが正常に応答を返す(self, mock_create_llm, client):
        """POST /api/chat が正常に動作することを確認"""
        # LLMのモックを設定
        mock_llm = MagicMock()
        mock_llm.stream.return_value = iter(["こんにちは", "！"])
        mock_create_llm.return_value = mock_llm
        
        # リクエストを送信
        response = client.post('/api/chat', 
                             json={
                                 "message": "こんにちは",
                                 "model_id": "gemini-1.5-flash"
                             },
                             headers={'Accept': 'text/event-stream'})
        
        assert response.status_code == 200
        assert response.content_type == 'text/event-stream'
        
        # SSEレスポンスを確認
        data = response.get_data(as_text=True)
        assert "data: " in data
        assert "こんにちは" in data
    
    def test_メッセージなしのリクエストはエラーを返す(self, client):
        """必須パラメータが欠けている場合のエラーハンドリングを確認"""
        response = client.post('/api/chat', json={})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    @patch('app.create_gemini_llm')
    def test_会話履歴がセッションに保存される(self, mock_create_llm, client):
        """会話履歴が正しくセッションに保存されることを確認"""
        mock_llm = MagicMock()
        mock_llm.stream.return_value = iter(["テスト応答"])
        mock_create_llm.return_value = mock_llm
        
        with client:
            # 最初のメッセージ
            client.post('/api/chat', 
                       json={"message": "テスト1", "model_id": "gemini-1.5-flash"})
            
            # セッションを確認
            with client.session_transaction() as sess:
                assert 'conversation_history' in sess
                assert len(sess['conversation_history']) == 2  # ユーザーとアシスタント
                assert sess['conversation_history'][0]['content'] == "テスト1"
    
    def test_会話履歴のクリア機能(self, client):
        """POST /api/clear_chat が会話履歴をクリアすることを確認"""
        with client:
            # セッションに履歴を追加
            with client.session_transaction() as sess:
                sess['conversation_history'] = [
                    {"role": "user", "content": "テスト"},
                    {"role": "assistant", "content": "応答"}
                ]
            
            # クリアAPI呼び出し
            response = client.post('/api/clear_chat')
            
            assert response.status_code == 200
            
            # セッションが空になっていることを確認
            with client.session_transaction() as sess:
                assert len(sess.get('conversation_history', [])) == 0


class TestScenarioAPI:
    """シナリオモードAPIのテスト"""
    
    @patch('app.create_gemini_llm')
    def test_シナリオチャットが正常に動作する(self, mock_create_llm, client):
        """POST /api/scenario_chat が正常に動作することを確認"""
        mock_llm = MagicMock()
        mock_llm.stream.return_value = iter(["シナリオ応答"])
        mock_create_llm.return_value = mock_llm
        
        # テスト用のシナリオIDを使用
        response = client.post('/api/scenario_chat',
                             json={
                                 "message": "こんにちは",
                                 "model_id": "gemini-1.5-flash",
                                 "scenario_id": "scenario1"
                             },
                             headers={'Accept': 'text/event-stream'})
        
        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert "シナリオ応答" in data
    
    def test_存在しないシナリオIDはエラーを返す(self, client):
        """無効なシナリオIDでエラーが返されることを確認"""
        response = client.post('/api/scenario_chat',
                             json={
                                 "message": "テスト",
                                 "model_id": "gemini-1.5-flash",
                                 "scenario_id": "invalid_scenario_999"
                             })
        
        # app.pyの529-530行目で無効なシナリオIDの場合は400を返す
        assert response.status_code == 400
        assert response.json["error"] == "無効なシナリオIDです"
    
    @patch('app.create_gemini_llm')
    def test_シナリオフィードバックが生成される(self, mock_create_llm, client):
        """POST /api/scenario_feedback がフィードバックを返すことを確認"""
        # LLMモックの設定
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "communication_score": 85,
            "strengths": ["明確な説明", "共感的な対応"],
            "improvements": ["より具体的な例を"],
            "overall_feedback": "良いコミュニケーションです"
        })
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm
        
        with client:
            # セッションに会話履歴を設定
            with client.session_transaction() as sess:
                sess['scenario_conversation_history'] = [
                    {"role": "user", "content": "テスト"},
                    {"role": "assistant", "content": "応答"}
                ]
            
            response = client.post('/api/scenario_feedback',
                                 json={"scenario_id": "scenario1"})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "feedback" in data
            assert "communication_score" in data["feedback"]


class TestWatchAPI:
    """観戦モードAPIのテスト"""
    
    @patch('app.create_gemini_llm')
    def test_観戦モード開始が成功する(self, mock_create_llm, client):
        """POST /api/watch/start が正常に動作することを確認"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "会話が始まります"
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm
        
        response = client.post('/api/watch/start',
                             json={
                                 "scenario_id": "scenario1",
                                 "model1": "gemini-1.5-pro",
                                 "model2": "gemini-1.5-flash"
                             })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "speaker" in data
        assert "message" in data
    
    @patch('app.create_gemini_llm')
    def test_観戦モード次の会話が生成される(self, mock_create_llm, client):
        """POST /api/watch/next が次の会話を生成することを確認"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "次の発言です"
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm
        
        with client:
            # セッションに会話履歴を設定
            with client.session_transaction() as sess:
                sess['watch_conversation_history'] = [
                    {"speaker": "社員A", "message": "こんにちは"}
                ]
                sess['watch_current_speaker'] = "上司B"
            
            response = client.post('/api/watch/next')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "speaker" in data
            assert "message" in data


class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    @patch('app.create_gemini_llm')
    def test_LLMエラーが適切にハンドリングされる(self, mock_create_llm, client):
        """LLMでエラーが発生した場合の処理を確認"""
        mock_llm = MagicMock()
        mock_llm.stream.side_effect = Exception("LLM Error")
        mock_create_llm.return_value = mock_llm
        
        response = client.post('/api/chat',
                             json={
                                 "message": "テスト",
                                 "model_id": "gemini-1.5-flash"
                             })
        
        # エラーハンドリングにより、適切なレスポンスが返される
        assert response.status_code in [200, 500]  # エラーでも200を返す場合がある
        
        if response.status_code == 500:
            data = json.loads(response.data)
            assert "error" in data
    
    def test_不正なJSONリクエストはエラーを返す(self, client):
        """不正なJSONでのリクエストが400エラーを返すことを確認"""
        response = client.post('/api/chat',
                             data="不正なJSON",
                             content_type='application/json')
        
        assert response.status_code == 400


class TestSessionManagement:
    """セッション管理のテスト"""
    
    def test_セッションが独立して管理される(self, client):
        """異なるクライアントのセッションが独立していることを確認"""
        # クライアント1
        with client as c1:
            with c1.session_transaction() as sess:
                sess['test_data'] = "client1"
            
            # クライアント2（新しいセッション）
            c2 = client.application.test_client()
            with c2.session_transaction() as sess2:
                assert 'test_data' not in sess2
    
    def test_セッションタイムアウトが設定されている(self, app):
        """セッションのタイムアウト設定を確認"""
        # セッション設定を確認
        assert app.config.get('PERMANENT_SESSION_LIFETIME') is not None


class TestModelSelection:
    """モデル選択機能のテスト"""
    
    def test_デフォルトモデルが使用される(self, client):
        """モデルIDが指定されない場合、デフォルトモデルが使用されることを確認"""
        with patch('app.create_gemini_llm') as mock_create_llm:
            mock_llm = MagicMock()
            mock_llm.stream.return_value = iter(["応答"])
            mock_create_llm.return_value = mock_llm
            
            response = client.post('/api/chat',
                                 json={"message": "テスト"})
            
            # デフォルトモデルで呼び出されたことを確認
            mock_create_llm.assert_called()
            call_args = mock_create_llm.call_args[0]
            assert "gemini" in call_args[0].lower()  # デフォルトはGeminiモデル


class TestCORS:
    """CORS設定のテスト"""
    
    def test_CORSヘッダーが設定される(self, client):
        """適切なCORSヘッダーが設定されることを確認"""
        response = client.options('/api/chat')
        
        # CORSヘッダーの確認
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers


# SSEレスポンスのパース用ヘルパー関数
def parse_sse_response(response_data):
    """SSEレスポンスをパースしてメッセージを抽出"""
    messages = []
    for line in response_data.split('\n'):
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                if 'content' in data:
                    messages.append(data['content'])
            except json.JSONDecodeError:
                pass
    return ''.join(messages)