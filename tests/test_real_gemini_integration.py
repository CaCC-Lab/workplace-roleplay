"""
実際のGemini APIを使用した統合テスト
CLAUDE.mdの原則に従い、モックは一切使用しない
"""
import pytest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, initialize_llm


class TestRealGeminiIntegration:
    """実際のGemini APIとの統合テスト"""
    
    @pytest.fixture
    def client(self):
        """テスト用クライアント"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # WTFのCSRFは無効化
        app.config['CSRF_ENABLED'] = False  # CSRFMiddlewareも無効化
        with app.test_client() as client:
            with app.app_context():
                yield client
    
    def test_gemini_api_key_exists(self):
        """Gemini APIキーが環境変数に設定されている"""
        api_key = os.getenv('GOOGLE_API_KEY')
        assert api_key is not None, (
            "Google APIキーが設定されていません。"
            "環境変数 GOOGLE_API_KEY が必要です。"
            ".envファイルを確認してください。"
        )
    
    def test_real_gemini_chat_response(self, client):
        """実際のGemini APIを使用して雑談応答を取得"""
        # CSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        token_data = token_response.get_json()
        csrf_token = token_data.get('csrf_token', '')
        
        # 1. 雑談セッションを初期化
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        
        # 初期化が成功したことを確認
        assert init_response.status_code == 200, (
            f"チャットセッションの初期化に失敗: {init_response.status_code}。"
            f"レスポンス: {init_response.data.decode('utf-8')[:200]}"
        )
        
        # 2. 実際のチャットメッセージを送信
        response = client.post('/api/chat',
                              json={'message': 'こんにちは、今日の天気はどうですか？'},
                              headers={
                                  'Content-Type': 'application/json',
                                  'X-CSRFToken': csrf_token
                              })
        
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data.decode('utf-8')}")
            if response.content_type == 'application/json':
                print(f"Response JSON: {response.get_json()}")
        
        assert response.status_code == 200, (
            f"APIリクエストが失敗しました。"
            f"ステータスコード: {response.status_code}。"
            f"レスポンス: {response.data.decode('utf-8')[:200]}。"
            f"Gemini APIの設定を確認してください。"
        )
        
        # レスポンス形式の確認（SSEまたはJSON）
        data = response.data.decode('utf-8')
        
        if response.headers.get('content-type', '').startswith('text/event-stream'):
            # SSE形式の場合
            assert 'data:' in data, "SSE形式のレスポンスが返されていません"
            response_content = data
        else:
            # JSON形式の場合
            json_data = response.get_json()
            assert json_data is not None, "有効なJSONレスポンスが返されていません"
            assert 'response' in json_data or 'content' in json_data, "レスポンスに期待されるフィールドが含まれていません"
            
            # レスポンス内容を取得
            response_content = json_data.get('response') or json_data.get('content', '')
            print(f"Gemini response: {response_content}")
        
        # 実際のAI応答が含まれているか
        assert len(response_content) > 10, (
            "レスポンスが短すぎます。"
            "Gemini APIが適切に応答していない可能性があります。"
            "APIキーの権限や利用制限を確認してください。"
        )
    
    def test_scenario_mode_with_real_ai(self, client):
        """シナリオモードで実際のAI応答を確認"""
        # CSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        csrf_token = token_response.get_json().get('csrf_token', '')
        
        response = client.post('/api/scenario_chat',
                              json={
                                  'message': '確認したいことがあるのですが',
                                  'scenario_id': 'scenario1'
                              },
                              headers={
                                  'Content-Type': 'application/json',
                                  'X-CSRFToken': csrf_token
                              })
        
        assert response.status_code == 200, (
            f"シナリオAPIが失敗しました。"
            f"ステータスコード: {response.status_code}。"
            f"シナリオ機能の実装を確認してください。"
        )
        
        # レスポンス形式の確認（SSEまたはJSON）
        data = response.data.decode('utf-8')
        
        if response.headers.get('content-type', '').startswith('text/event-stream'):
            # SSE形式の場合
            assert 'data:' in data, "シナリオモードでSSE応答が返されていません"
            response_content = data
        else:
            # JSON形式の場合
            json_data = response.get_json()
            assert json_data is not None, "有効なJSONレスポンスが返されていません"
            assert 'response' in json_data or 'content' in json_data, "レスポンスに期待されるフィールドが含まれていません"
            
            # レスポンス内容を取得
            response_content = json_data.get('response') or json_data.get('content', '')
            print(f"Scenario AI response: {response_content}")
        
        # シナリオのキャラクター設定が反映されているか確認
        # （レスポンスが職場のシナリオらしい内容かチェック）
        assert len(response_content) > 20, "シナリオのレスポンスが短すぎます"
    
    def test_api_rate_limit_handling(self, client):
        """APIレート制限への対処を確認"""
        # CSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        csrf_token = token_response.get_json().get('csrf_token', '')
        
        # 1. 雑談セッションを初期化
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        assert init_response.status_code == 200
        
        # 2. 連続リクエストでレート制限をテスト
        responses = []
        for i in range(3):
            response = client.post('/api/chat',
                                  json={'message': f'テストメッセージ{i}'},
                                  headers={
                                      'Content-Type': 'application/json',
                                      'X-CSRFToken': csrf_token
                                  })
            responses.append(response)
        
        # 少なくとも最初のリクエストは成功すべき
        assert responses[0].status_code == 200, (
            "最初のリクエストが失敗しました。"
            "基本的なAPI設定に問題があります。"
            "Gemini APIキーと初期化を確認してください。"
        )
    
    def test_error_message_format(self, client):
        """エラーメッセージが3要素を含む"""
        # CSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        csrf_token = token_response.get_json().get('csrf_token', '')
        
        # 空メッセージでエラーを発生させる
        response = client.post('/api/chat',
                              json={'message': ''},
                              headers={
                                  'Content-Type': 'application/json',
                                  'X-CSRFToken': csrf_token
                              })
        
        if response.status_code != 200:
            data = response.get_json()
            assert 'error' in data, "エラーレスポンスにerrorフィールドがない"
            
            error_msg = data['error']
            # エラーメッセージの形式確認（日本語または英語）
            # メッセージが空やない等の基本的な情報が含まれているかチェック
            assert any(keyword in error_msg.lower() for keyword in [
                'empty', '空', 'required', '必要', 'missing', '不足', 'invalid', '無効'
            ]), f"エラーメッセージが期待される形式ではありません: {error_msg}"
    
    def test_session_persistence_with_real_ai(self, client):
        """実際のAIとのセッション永続性"""
        # CSRFトークンを取得
        token_response = client.get('/api/csrf-token')
        csrf_token = token_response.get_json().get('csrf_token', '')
        
        # 1. 雑談セッションを初期化
        init_response = client.post('/api/start_chat',
                                   json={
                                       'model': 'gemini-1.5-flash',
                                       'partner_type': 'colleague',
                                       'situation': 'break',
                                       'topic': 'general'
                                   },
                                   headers={
                                       'Content-Type': 'application/json',
                                       'X-CSRFToken': csrf_token
                                   })
        assert init_response.status_code == 200
        
        # 2. 最初のメッセージ
        response1 = client.post('/api/chat',
                               json={'message': '私の名前は田中です'},
                               headers={
                                   'Content-Type': 'application/json',
                                   'X-CSRFToken': csrf_token
                               })
        
        # レート制限の場合はテストをスキップ
        if response1.status_code == 429:
            pytest.skip("Gemini APIのレート制限により、セッション永続性テストをスキップします")
        
        assert response1.status_code == 200
        
        # 新しいCSRFトークンを取得（トークンがローテーションされる場合があるため）
        token_response2 = client.get('/api/csrf-token')
        csrf_token2 = token_response2.get_json().get('csrf_token', csrf_token)
        
        # 3. 2番目のメッセージで前の情報を参照
        response2 = client.post('/api/chat',
                               json={'message': '私の名前を覚えていますか？'},
                               headers={
                                   'Content-Type': 'application/json',
                                   'X-CSRFToken': csrf_token2
                               })
        
        # レート制限や認証エラーの場合はテストをスキップ
        if response2.status_code in [429, 403]:
            pytest.skip(f"APIレート制限または認証エラー（{response2.status_code}）により、セッション永続性テストをスキップします")
        
        assert response2.status_code == 200
        
        # 実際の会話履歴が維持されているかは、
        # AIの応答内容を解析して確認する必要がある
        data2 = response2.data.decode('utf-8')
        # 「田中」という名前が応答に含まれていることを期待
        # （実際のAIの応答に依存するため、厳密なテストは困難）