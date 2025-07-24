"""
主要APIエンドポイントの実環境テスト

開発規約準拠：モック禁止、実際のGemini APIを使用した統合テスト
実際のAPIキーとFlaskセッションを使用してエンドポイントの動作を検証
"""
import pytest
import json
import os
import time
from flask import session

from utils.security import CSRFToken
from models import User


class TestChatAPIReal:
    """チャットAPI (/api/chat) の実環境テスト"""
    
    def test_api_chat_success_real(self, client, app, auth_user):
        """正常なチャットAPIリクエスト（実際のGemini API使用）"""
        # 実際のGoogle API Keyが必要
        if not os.getenv('GOOGLE_API_KEY'):
            pytest.skip("GOOGLE_API_KEY environment variable required for real API test")
            
        with app.app_context():
            # 実際のCSRFトークンを生成
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
                sess['conversation_history'] = []
                # 実際のチャット設定（短い応答を要求）
                sess['chat_settings'] = {
                    'system_prompt': 'あなたは職場でのコミュニケーションを支援するAIアシスタントです。テスト用なので10文字以内で短く応答してください。'
                }
            
            # 実際のAPI呼び出し（モックなし）
            response = client.post('/api/chat',
                data=json.dumps({
                    'message': 'こんにちは、テストです',
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            # 実際のAPI応答を検証
            assert response.status_code == 200
            # ストリーミングレスポンスまたはJSON応答を確認
            content_type = response.content_type
            assert content_type.startswith('application/json') or content_type.startswith('text/event-stream')
            
            # APIレート制限を考慮した待機
            time.sleep(2)
    
    def test_api_chat_missing_message_real(self, client, app):
        """メッセージなしのチャットAPIリクエスト（実際のバリデーション）"""
        with app.app_context():
            # 実際のCSRF検証
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            # 実際のバリデーションエラーテスト
            response = client.post('/api/chat',
                data=json.dumps({'csrf_token': csrf_token}),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
    
    def test_api_chat_invalid_csrf_real(self, client, app, auth_user):
        """無効なCSRFトークンでのエラー（実際のセキュリティテスト）"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
            
            # 無効なCSRFトークンで実際のリクエスト
            response = client.post('/api/chat',
                data=json.dumps({
                    'message': 'テストメッセージ',
                    'csrf_token': 'invalid_csrf_token'
                }),
                content_type='application/json',
                headers={'X-CSRFToken': 'invalid_csrf_token'}
            )
            
            # 実際のCSRF検証エラー
            assert response.status_code in [400, 403]


class TestScenarioChatAPIReal:
    """シナリオチャットAPI (/api/scenario_chat) の実環境テスト"""
    
    def test_scenario_chat_success_real(self, client, app, auth_user, sample_scenario_data):
        """正常なシナリオチャットAPIリクエスト（実際のAPI使用）"""
        if not os.getenv('GOOGLE_API_KEY'):
            pytest.skip("GOOGLE_API_KEY environment variable required for real API test")
            
        with app.app_context():
            # テストフィクスチャとして、app.scenariosにテスト用シナリオを追加
            # これによりテストが実際のYAMLファイルから独立し、安定性が向上
            import app as app_module
            scenario_id = sample_scenario_data['id']
            app_module.scenarios[scenario_id] = sample_scenario_data
            
            csrf_token = CSRFToken.generate()
            
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
                # 実際のシナリオデータ設定
                sess['current_scenario'] = sample_scenario_data
                sess['scenario_history'] = {
                    scenario_id: []
                }
            
            # 実際のシナリオチャットリクエスト
            response = client.post('/api/scenario_chat',
                data=json.dumps({
                    'message': 'プロジェクトの進捗を報告します',
                    'scenario_id': scenario_id,
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            # 実際のAPI応答を検証
            if response.status_code != 200:
                print(f"Scenario chat failed: {response.status_code} - {response.get_json()}")
            
            assert response.status_code == 200
            
            # APIレート制限対応
            time.sleep(2)
    
    def test_scenario_chat_no_scenario_real(self, client, app):
        """シナリオ未選択時のエラー（実際のバリデーション）"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            response = client.post('/api/scenario_chat',
                data=json.dumps({
                    'message': 'テストメッセージ',
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data


class TestUtilityAPIReal:
    """ユーティリティAPI の実環境テスト"""
    
    def test_clear_history_success_real(self, client, app):
        """履歴クリアAPI実環境テスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['conversation_history'] = ['test', 'data']
            
            response = client.post('/api/clear_history',
                data=json.dumps({'csrf_token': csrf_token}),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'status' in data and data['status'] == 'success'
    
    def test_models_api_real(self, client, app):
        """モデル一覧API 実環境テスト"""
        if not os.getenv('GOOGLE_API_KEY'):
            pytest.skip("GOOGLE_API_KEY environment variable required for real API test")
            
        with app.app_context():
            response = client.get('/api/models')
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'models' in data
            assert isinstance(data['models'], list)
            # Geminiモデルが含まれていることを確認
            model_names = [model.get('id', '') for model in data['models']]
            assert any('gemini' in name.lower() for name in model_names)
    
    def test_session_clear_success_real(self, client, app):
        """セッションクリアAPI実環境テスト"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['test_data'] = 'should_be_cleared'
            
            response = client.post('/api/session/clear',
                data=json.dumps({'csrf_token': csrf_token}),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'status' in data and data['status'] == 'success'


class TestFeedbackAPIReal:
    """フィードバックAPI の実環境テスト"""
    
    def test_chat_feedback_success_real(self, client, app, auth_user):
        """チャットフィードバックAPI実環境テスト"""
        if not os.getenv('GOOGLE_API_KEY'):
            pytest.skip("GOOGLE_API_KEY environment variable required for real API test")
            
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
                sess['user_id'] = auth_user.id
                sess['chat_history'] = [
                    {'role': 'user', 'content': 'こんにちは'},
                    {'role': 'assistant', 'content': 'こんにちは！何かお手伝いできることはありますか？'}
                ]
            
            # 実際のフィードバック生成
            response = client.post('/api/chat_feedback',
                data=json.dumps({'csrf_token': csrf_token}),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 200
            
            # APIレート制限対応
            time.sleep(3)
    
    def test_feedback_no_conversation_real(self, client, app):
        """会話履歴なしでのフィードバックAPIエラー"""
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            response = client.post('/api/chat_feedback',
                data=json.dumps({'csrf_token': csrf_token}),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data


class TestWatchAPIReal:
    """観戦モードAPI の実環境テスト"""
    
    def test_watch_start_success_real(self, client, app):
        """観戦モード開始API実環境テスト"""
        if not os.getenv('GOOGLE_API_KEY'):
            pytest.skip("GOOGLE_API_KEY environment variable required for real API test")
            
        with app.app_context():
            csrf_token = CSRFToken.generate()
            with client.session_transaction() as sess:
                sess['csrf_token'] = csrf_token
            
            response = client.post('/api/watch/start',
                data=json.dumps({
                    'topic': 'プロジェクト管理について（テスト用短縮版）',
                    'model_a': 'gemini/gemini-1.5-flash',
                    'model_b': 'gemini/gemini-1.5-flash',
                    'partner_type': '同僚',
                    'situation': 'オフィス',
                    'csrf_token': csrf_token
                }),
                content_type='application/json',
                headers={'X-CSRFToken': csrf_token}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'message' in data or 'assistant1_message' in data
            
            # APIレート制限対応
            time.sleep(3)


class TestStrengthAnalysisAPIReal:
    """強み分析API の実環境テスト"""
    
    def test_strength_analysis_success_real(self, client, app):
        """強み分析API実環境テスト"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['chat_history'] = [
                    {'role': 'user', 'content': 'プロジェクトについて相談があります'},
                    {'role': 'assistant', 'content': 'どのような相談でしょうか？'},
                    {'role': 'user', 'content': '期限が迫っているのですが、品質を保ちたいです'}
                ]
            
            # 実際の強み分析（内部関数を使用）
            response = client.post('/api/strength_analysis',
                data=json.dumps({}),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'scores' in data
            assert 'empathy' in data['scores']
    
    def test_strength_analysis_no_conversation_real(self, client, app):
        """会話履歴なしでの強み分析（デフォルト値）"""
        with app.app_context():
            response = client.post('/api/strength_analysis',
                data=json.dumps({}),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'scores' in data
            # デフォルトスコアは50が設定される
            assert data['scores']['empathy'] == 50


# TTS と画像生成 API は複雑な外部依存があるため、基本的な接続テストのみ
class TestComplexAPIReal:
    """複雑なAPI（TTS、画像生成）の基本テスト"""
    
    def test_tts_endpoint_exists(self, client, app):
        """TTS APIエンドポイントの存在確認"""
        with app.app_context():
            # エンドポイントが存在することのみ確認
            response = client.post('/api/tts',
                data=json.dumps({'text': 'テスト'}),
                content_type='application/json'
            )
            # 400 (必要パラメータ不足) または 200 (成功) を期待
            assert response.status_code in [200, 400, 405]
    
    def test_image_generation_endpoint_exists(self, client, app):
        """画像生成APIエンドポイントの存在確認"""
        with app.app_context():
            # エンドポイントが存在することのみ確認
            response = client.post('/api/generate_character_image',
                data=json.dumps({'character_description': 'テスト'}),
                content_type='application/json'
            )
            # エンドポイントが存在し、何らかのレスポンスを返すことを確認
            assert response.status_code in [200, 400, 405, 501]