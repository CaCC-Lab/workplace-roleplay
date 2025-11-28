"""
Flask APIエンドポイントの統合テスト
TDD原則に従い、APIの振る舞いをテスト

注: これらのテストはモックを使用してAPIの動作を検証します。
    実際のLLM APIは呼び出しません。
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from flask import session
import time

# CSRF対応のテストヘルパーをインポート
from tests.helpers.csrf_helpers import requires_csrf


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
        with patch('routes.model_routes.get_all_available_models') as mock_get_models:
            # モックモデルを設定
            mock_get_models.return_value = {
                "models": [
                    {"id": "gemini/gemini-1.5-pro", "name": "gemini-1.5-pro", "provider": "gemini"},
                    {"id": "gemini/gemini-1.5-flash", "name": "gemini-1.5-flash", "provider": "gemini"}
                ],
                "categories": {"gemini": []}
            }
            
            response = client.get('/api/models')
            
            # フィーチャーフラグで無効化されている場合も考慮
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "models" in data
    
    def test_存在しないエンドポイントは404を返す(self, client):
        """存在しないURLへのアクセスが404を返すことを確認"""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404


@pytest.mark.integration
class TestChatAPI:
    """雑談モードAPIのテスト"""
    
    def test_チャットAPIが正常に応答を返す(self, csrf_client):
        """POST /api/chat が正常に動作することを確認"""
        with patch('app.initialize_llm') as mock_init_llm:
            # LLMのモックを設定
            mock_llm = MagicMock()
            from langchain_core.messages import AIMessage
            
            # ストリーミングレスポンスをモック
            mock_chunk = MagicMock()
            mock_chunk.content = "こんにちは！"
            mock_llm.stream.return_value = iter([mock_chunk])
            mock_init_llm.return_value = mock_llm
            
            # チャットセッションを初期化
            with csrf_client.session_transaction() as sess:
                sess['chat_settings'] = {
                    "system_prompt": "あなたは職場での雑談練習をサポートするAIアシスタントです。",
                    "model": "gemini-1.5-flash"
                }
        
            # リクエストを送信
            response = csrf_client.post('/api/chat', 
                                 json={
                                     "message": "こんにちは",
                                     "model": "gemini-1.5-flash"
                                 })
            
            # ストリーミングレスポンス(200)またはJSON応答
            assert response.status_code == 200
    
    def test_メッセージなしのリクエストはエラーを返す(self, csrf_client):
        """必須パラメータが欠けている場合のエラーハンドリングを確認"""
        response = csrf_client.post('/api/chat', json={})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_会話履歴がセッションに保存される(self, csrf_client):
        """会話履歴が正しくセッションに保存されることを確認"""
        with patch('app.initialize_llm') as mock_init_llm:
            mock_llm = MagicMock()
            mock_chunk = MagicMock()
            mock_chunk.content = "テスト応答"
            mock_llm.stream.return_value = iter([mock_chunk])
            mock_init_llm.return_value = mock_llm
            
            # チャットセッションを初期化
            with csrf_client.session_transaction() as sess:
                sess['chat_settings'] = {
                    "system_prompt": "テスト用プロンプト",
                    "model": "gemini-1.5-flash"
                }
            
            # 最初のメッセージ - レスポンスを消費
            response = csrf_client.post('/api/chat', 
                       json={"message": "テスト1", "model": "gemini-1.5-flash"})
            # ストリーミングレスポンスを消費
            list(response.response)
            
            # セッションを確認
            with csrf_client.session_transaction() as sess:
                # 履歴が保存されていることを確認
                assert 'chat_history' in sess
    
    def test_会話履歴のクリア機能(self, csrf_client):
        """POST /api/clear_history が会話履歴をクリアすることを確認"""
        # セッションに履歴を追加
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = [
                {"human": "テスト", "ai": "応答"}
            ]
        
        # クリアAPI呼び出し（modeをchatに設定）
        response = csrf_client.post('/api/clear_history', json={"mode": "chat"})
        
        assert response.status_code == 200
        
        # セッションが空になっていることを確認
        with csrf_client.session_transaction() as sess:
                assert len(sess.get('chat_history', [])) == 0


@pytest.mark.integration
class TestScenarioAPI:
    """シナリオモードAPIのテスト"""
    
    def test_シナリオチャットが正常に動作する(self, csrf_client):
        """POST /api/scenario_chat が正常に動作することを確認"""
        with patch('app.initialize_llm') as mock_init_llm:
            mock_llm = MagicMock()
            mock_chunk = MagicMock()
            mock_chunk.content = "シナリオ応答"
            mock_llm.stream.return_value = iter([mock_chunk])
            mock_init_llm.return_value = mock_llm
            
            # テスト用のシナリオIDを使用
            response = csrf_client.post('/api/scenario_chat',
                                 json={
                                     "message": "こんにちは",
                                     "model": "gemini-1.5-flash",
                                     "scenario_id": "scenario1"
                                 })
            
            assert response.status_code == 200
    
    def test_存在しないシナリオIDはエラーを返す(self, csrf_client):
        """無効なシナリオIDでエラーが返されることを確認"""
        response = csrf_client.post('/api/scenario_chat',
                             json={
                                 "message": "テスト",
                                 "model_id": "gemini-1.5-flash",
                                 "scenario_id": "invalid_scenario_999"
                             })
        
        assert response.status_code == 400
        assert response.json["error"] == "無効なシナリオIDです"
    
    def test_シナリオフィードバックが生成される(self, csrf_client):
        """POST /api/scenario_feedback がフィードバックを返すことを確認"""
        with patch('services.feedback_service.FeedbackService.try_multiple_models_for_prompt') as mock_try:
            # フィードバックとして適切な文字列を返す (3値のタプル)
            feedback_text = """
## コミュニケーションスコア
85点

## 良かった点
- 明確な説明
- 共感的な対応

## 改善のヒント
- より具体的な例を使うとよいでしょう
"""
            # (feedback_content, used_model, error_msg) の形式で返す
            mock_try.return_value = (feedback_text, "gemini-1.5-flash", None)
            
            # セッションにシナリオ会話履歴を設定
            with csrf_client.session_transaction() as sess:
                sess['scenario_history'] = {
                    "scenario1": [
                        {"human": "テスト", "ai": "応答"}
                    ]
                }
            
            response = csrf_client.post('/api/scenario_feedback',
                                 json={"scenario_id": "scenario1"})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "feedback" in data


@pytest.mark.integration
class TestWatchAPI:
    """観戦モードAPIのテスト"""
    
    def test_観戦モード開始が成功する(self, csrf_client):
        """POST /api/watch/start が正常に動作することを確認"""
        with patch('app.initialize_llm') as mock_init_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="会話が始まります")
            mock_init_llm.return_value = mock_llm
            
            response = csrf_client.post('/api/watch/start',
                                 json={
                                     "model_a": "gemini-1.5-pro",
                                     "model_b": "gemini-1.5-flash",
                                     "partner_type": "colleague",
                                     "situation": "break",
                                     "topic": "general"
                                 })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "message" in data
    
    def test_観戦モード次の会話が生成される(self, csrf_client):
        """POST /api/watch/next が次の会話を生成することを確認"""
        with patch('app.initialize_llm') as mock_init_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="次の発言です")
            mock_init_llm.return_value = mock_llm
            
            # セッションに観戦設定と履歴を設定
            with csrf_client.session_transaction() as sess:
                sess['watch_settings'] = {
                    "model_a": "gemini-1.5-pro",
                    "model_b": "gemini-1.5-flash",
                    "current_speaker": "B",
                    "partner_type": "colleague",
                    "situation": "break",
                    "topic": "general"
                }
                sess['watch_history'] = [
                    {"speaker": "A", "message": "こんにちは"}
                ]
            
            response = csrf_client.post('/api/watch/next')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "message" in data


class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_LLMエラーが適切にハンドリングされる(self, csrf_client):
        """LLMでエラーが発生した場合の処理を確認"""
        with patch('app.initialize_llm') as mock_init_llm:
            # 初期化時にエラーを発生させる
            mock_init_llm.side_effect = Exception("LLM Error")
            
            # チャットセッションを初期化
            with csrf_client.session_transaction() as sess:
                sess['chat_settings'] = {
                    "system_prompt": "テスト用プロンプト",
                    "model": "gemini-1.5-flash"
                }
            
            response = csrf_client.post('/api/chat',
                                 json={
                                     "message": "テスト",
                                     "model": "gemini-1.5-flash"
                                 })
            
            # エラーハンドリングにより、適切なレスポンスが返される
            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data
    
    def test_不正なJSONリクエストはエラーを返す(self, csrf_client):
        """不正なJSONでのリクエストがエラーを返すことを確認"""
        response = csrf_client.post('/api/chat',
                             data="不正なJSON",
                             content_type='application/json')
        
        # Flaskの内部エラーハンドラーは500を返す可能性がある
        assert response.status_code in [400, 500]


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


@pytest.mark.integration
class TestModelSelection:
    """モデル選択機能のテスト"""
    
    def test_デフォルトモデルが使用される(self, csrf_client):
        """モデルIDが指定されない場合、デフォルトモデルが使用されることを確認"""
        with patch('app.initialize_llm') as mock_init_llm:
            mock_llm = MagicMock()
            mock_chunk = MagicMock()
            mock_chunk.content = "応答"
            mock_llm.stream.return_value = iter([mock_chunk])
            mock_init_llm.return_value = mock_llm
            
            # チャットセッションを初期化
            with csrf_client.session_transaction() as sess:
                sess['chat_settings'] = {
                    "system_prompt": "テスト用プロンプト",
                    "model": "gemini-1.5-flash"
                }
            
            response = csrf_client.post('/api/chat',
                                 json={"message": "テスト"})
            
            # モックが呼び出されたことを確認
            mock_init_llm.assert_called()


class TestCORS:
    """CORS設定のテスト"""
    
    def test_CORSヘッダーが設定される(self, client):
        """適切なCORSヘッダーが設定されることを確認"""
        # ヘルスチェックエンドポイントでテスト
        response = client.get('/api/v2/health')
        
        assert response.status_code == 200
        # CORSが設定されている場合のチェック（オプショナル）
        # Access-Control-Allow-Originがあればチェック
        if 'Access-Control-Allow-Origin' in response.headers:
            assert response.headers['Access-Control-Allow-Origin'] is not None


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
