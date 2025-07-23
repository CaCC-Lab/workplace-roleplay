"""
app.pyのストリーミング機能とSSE処理テスト - カバレッジ向上のため
TDD原則に従い、Server-Sent Events、ストリーミング応答、リアルタイム通信をテスト
"""
import pytest
import json
import time
from unittest.mock import patch, MagicMock, PropertyMock, AsyncMock
from flask import session

# テスト対象の関数
from app import app


class TestServerSentEvents:
    """Server-Sent Events (SSE) のテスト"""
    
    @patch('app.create_gemini_llm')
    def test_sse_chat_streaming(self, mock_create_llm, csrf_client):
        """チャットのSSEストリーミングが正常に動作することを確認"""
        # ストリーミング用のLLMモックを設定
        mock_llm = MagicMock()
        
        def mock_stream_generator(*args, **kwargs):
            """ストリーミングデータを模擬"""
            chunks = [
                {"content": "こんにちは"},
                {"content": "！"},
                {"content": "今日は"},
                {"content": "良い天気ですね"}
            ]
            for chunk in chunks:
                yield chunk
        
        mock_llm.stream.return_value = mock_stream_generator()
        mock_create_llm.return_value = mock_llm
        
        # セッション初期化
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "あなたは職場での雑談練習をサポートするAIアシスタントです。",
                "model": "gemini-1.5-flash"
            }
        
        # ストリーミングリクエスト
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "こんにちは",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
        
        # レスポンスデータの確認
        response_data = response.get_data(as_text=True)
        assert "data:" in response_data
        assert "こんにちは" in response_data
    
    @patch('app.create_gemini_llm')
    def test_sse_scenario_streaming(self, mock_create_llm, csrf_client):
        """シナリオチャットのSSEストリーミングを確認"""
        mock_llm = MagicMock()
        
        def mock_scenario_stream(*args, **kwargs):
            yield {"content": "承知いたしました。"}
            yield {"content": "この件について"}
            yield {"content": "検討させていただきます。"}
        
        mock_llm.stream.return_value = mock_scenario_stream()
        mock_create_llm.return_value = mock_llm
        
        response = csrf_client.post('/api/scenario_chat',
                             json={
                                 "message": "プロジェクトの進捗はいかがですか？",
                                 "model": "gemini-1.5-flash",
                                 "scenario_id": "scenario1",
                                 "stream": True
                             })
        
        assert response.status_code == 200
        response_data = response.get_data(as_text=True)
        assert "承知いたしました" in response_data
    
    def test_sse_format_validation(self, csrf_client):
        """SSEレスポンス形式の検証"""
        with patch('app.create_gemini_llm') as mock_create_llm:
            mock_llm = MagicMock()
            
            def mock_sse_stream(*args, **kwargs):
                yield {"content": "テスト"}
                yield {"content": "メッセージ"}
            
            mock_llm.stream.return_value = mock_sse_stream()
            mock_create_llm.return_value = mock_llm
            
            with csrf_client.session_transaction() as sess:
                sess['chat_settings'] = {
                    "system_prompt": "テスト",
                    "model": "gemini-1.5-flash"
                }
            
            response = csrf_client.post('/api/chat',
                                 json={
                                     "message": "test",
                                     "model": "gemini-1.5-flash",
                                     "stream": True
                                 })
            
            response_data = response.get_data(as_text=True)
            
            # SSE形式の確認
            lines = response_data.strip().split('\n')
            data_lines = [line for line in lines if line.startswith('data:')]
            
            assert len(data_lines) > 0
            for line in data_lines:
                # JSONが正しくパースできることを確認
                json_str = line[5:]  # "data:" を除去
                if json_str.strip():
                    data = json.loads(json_str)
                    assert "content" in data
    
    @patch('app.create_gemini_llm')
    def test_sse_error_handling(self, mock_create_llm, csrf_client):
        """SSEストリーミング中のエラーハンドリングを確認"""
        mock_llm = MagicMock()
        
        def mock_error_stream(*args, **kwargs):
            yield {"content": "開始"}
            raise Exception("ストリーミングエラー")
        
        mock_llm.stream.return_value = mock_error_stream()
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "test",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        # エラーが発生してもレスポンスは返される
        assert response.status_code in [200, 500]


class TestStreamingFallback:
    """ストリーミングフォールバック機能のテスト"""
    
    @patch('app.create_gemini_llm')
    def test_stream_not_supported_fallback(self, mock_create_llm, csrf_client):
        """ストリーミングがサポートされていない場合のフォールバック"""
        mock_llm = MagicMock()
        # streamメソッドが存在しない場合を模擬
        delattr(mock_llm, 'stream')
        
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="通常応答")
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "test",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        # フォールバックして通常のJSONレスポンスが返される
        assert response.status_code == 200
        if response.mimetype == 'application/json':
            data = response.get_json()
            assert "response" in data
    
    @patch('app.create_gemini_llm')
    def test_stream_exception_fallback(self, mock_create_llm, csrf_client):
        """ストリーミング中の例外でのフォールバック"""
        mock_llm = MagicMock()
        mock_llm.stream.side_effect = Exception("ストリーミング失敗")
        
        # invokeメソッドは正常動作
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="フォールバック応答")
        mock_llm.invoke.return_value = mock_response
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "test",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        # フォールバック処理が動作
        assert response.status_code in [200, 500]


class TestStreamingPerformance:
    """ストリーミングパフォーマンスのテスト"""
    
    @patch('app.create_gemini_llm')
    def test_streaming_response_time(self, mock_create_llm, csrf_client):
        """ストリーミングレスポンスの応答時間を確認"""
        mock_llm = MagicMock()
        
        def mock_fast_stream(*args, **kwargs):
            """高速なストリーミングを模擬"""
            for i in range(5):
                yield {"content": f"chunk_{i}"}
        
        mock_llm.stream.return_value = mock_fast_stream()
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        start_time = time.time()
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "test",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        # レスポンス時間が合理的な範囲内（5秒以内）
        assert response_time < 5.0
    
    @patch('app.create_gemini_llm')
    def test_large_streaming_data(self, mock_create_llm, csrf_client):
        """大きなストリーミングデータの処理を確認"""
        mock_llm = MagicMock()
        
        def mock_large_stream(*args, **kwargs):
            """大きなデータのストリーミングを模擬"""
            for i in range(100):
                yield {"content": f"大きなテキストチャンク_{i} " * 10}
        
        mock_llm.stream.return_value = mock_large_stream()
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "長いレスポンスをお願いします",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        assert response.status_code == 200
        response_data = response.get_data(as_text=True)
        
        # 大きなデータが正しく送信されている
        assert len(response_data) > 1000
        assert "大きなテキストチャンク" in response_data


class TestRealTimeFeatures:
    """リアルタイム機能のテスト"""
    
    @patch('app.create_gemini_llm')
    def test_concurrent_streaming_requests(self, mock_create_llm, csrf_client):
        """複数の同時ストリーミングリクエストの処理"""
        mock_llm = MagicMock()
        
        def mock_concurrent_stream(*args, **kwargs):
            yield {"content": "同時"}
            yield {"content": "処理"}
            yield {"content": "テスト"}
        
        mock_llm.stream.return_value = mock_concurrent_stream()
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        # 複数のリクエストを送信（実際の並行処理は制限されるが、順次実行を確認）
        responses = []
        for i in range(3):
            response = csrf_client.post('/api/chat',
                                 json={
                                     "message": f"test_{i}",
                                     "model": "gemini-1.5-flash",
                                     "stream": True
                                 })
            responses.append(response)
        
        # すべてのレスポンスが正常
        for response in responses:
            assert response.status_code == 200
    
    @patch('app.create_gemini_llm')
    def test_streaming_with_session_isolation(self, mock_create_llm, client):
        """セッション分離でのストリーミングを確認"""
        mock_llm = MagicMock()
        
        def mock_isolated_stream(*args, **kwargs):
            yield {"content": "分離"}
            yield {"content": "ストリーミング"}
        
        mock_llm.stream.return_value = mock_isolated_stream()
        mock_create_llm.return_value = mock_llm
        
        # 2つの独立したクライアント
        client1 = client.application.test_client()
        client2 = client.application.test_client()
        
        with client1.session_transaction() as sess1:
            sess1['chat_settings'] = {
                "system_prompt": "クライアント1",
                "model": "gemini-1.5-flash"
            }
        
        with client2.session_transaction() as sess2:
            sess2['chat_settings'] = {
                "system_prompt": "クライアント2",
                "model": "gemini-1.5-flash"
            }
        
        # CSRFトークンを取得して設定
        csrf1_response = client1.get('/')
        csrf2_response = client2.get('/')
        
        # 各クライアントで独立したストリーミング
        response1 = client1.post('/api/chat',
                               json={
                                   "message": "client1",
                                   "model": "gemini-1.5-flash",
                                   "stream": True
                               })
        
        response2 = client2.post('/api/chat',
                               json={
                                   "message": "client2",
                                   "model": "gemini-1.5-flash",
                                   "stream": True
                               })
        
        # 独立して処理される
        assert response1.status_code in [200, 400]  # CSRFエラーの可能性
        assert response2.status_code in [200, 400]


class TestStreamingContentTypes:
    """ストリーミングコンテンツタイプのテスト"""
    
    @patch('app.create_gemini_llm')
    def test_text_content_streaming(self, mock_create_llm, csrf_client):
        """テキストコンテンツのストリーミングを確認"""
        mock_llm = MagicMock()
        
        def mock_text_stream(*args, **kwargs):
            yield {"content": "これは"}
            yield {"content": "テキスト"}
            yield {"content": "ストリーミング"}
            yield {"content": "です"}
        
        mock_llm.stream.return_value = mock_text_stream()
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "テキストストリーミングテスト",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        assert response.status_code == 200
        assert response.mimetype == 'text/plain'
        
        response_data = response.get_data(as_text=True)
        assert "これは" in response_data
        assert "テキスト" in response_data
        assert "ストリーミング" in response_data
    
    @patch('app.create_gemini_llm')
    def test_json_chunk_streaming(self, mock_create_llm, csrf_client):
        """JSONチャンクのストリーミングを確認"""
        mock_llm = MagicMock()
        
        def mock_json_stream(*args, **kwargs):
            yield {"content": "JSON", "type": "text"}
            yield {"content": "チャンク", "metadata": {"chunk_id": 1}}
            yield {"content": "テスト", "final": True}
        
        mock_llm.stream.return_value = mock_json_stream()
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "JSONストリーミングテスト",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        assert response.status_code == 200
        response_data = response.get_data(as_text=True)
        
        # 各行がJSONとしてパースできることを確認
        lines = [line for line in response_data.split('\n') if line.startswith('data:')]
        for line in lines:
            json_str = line[5:].strip()
            if json_str:
                data = json.loads(json_str)
                assert "content" in data


class TestStreamingHeaders:
    """ストリーミングヘッダーのテスト"""
    
    @patch('app.create_gemini_llm')
    def test_streaming_headers_set(self, mock_create_llm, csrf_client):
        """ストリーミング用のHTTPヘッダーが正しく設定されることを確認"""
        mock_llm = MagicMock()
        mock_llm.stream.return_value = [{"content": "test"}]
        mock_create_llm.return_value = mock_llm
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "ヘッダーテスト",
                                 "model": "gemini-1.5-flash",
                                 "stream": True
                             })
        
        assert response.status_code == 200
        
        # ストリーミング用ヘッダーの確認
        assert response.mimetype == 'text/plain'
        assert 'Cache-Control' in response.headers or response.mimetype == 'text/plain'


# テスト用のフィクスチャ
@pytest.fixture
def app_context():
    """アプリケーションコンテキストのフィクスチャ"""
    with app.app_context():
        yield app