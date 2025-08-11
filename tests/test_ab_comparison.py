"""
A/Bテスト比較テスト
新旧サービスの出力を比較して同等性を確認
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, process_chat_message_legacy
from services.chat_service import ChatService
from services.llm_service import LLMService
from services.session_service import SessionService


class TestABComparison:
    """A/Bテスト比較のテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
        
        # セッションの初期化
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'test-user'
            sess['chat_history'] = []
            sess['chat_settings'] = {
                'system_prompt': 'あなたは親切なアシスタントです。'
            }
    
    def test_v2_endpoint_exists(self):
        """V2エンドポイントが存在することを確認"""
        response = self.client.get('/api/v2/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
    
    def test_v2_config_endpoint(self):
        """V2設定エンドポイントのテスト"""
        response = self.client.get('/api/v2/config')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'service_mode' in data
        assert 'ab_test_enabled' in data
        assert 'features' in data
    
    @patch('services.llm_service.LLMService.stream_chat_response')
    def test_v2_chat_basic(self, mock_stream):
        """V2チャットエンドポイントの基本動作テスト"""
        # モックレスポンス
        async def mock_response(*args, **kwargs):
            for chunk in ["こんにちは", "！"]:
                yield chunk
        
        mock_stream.return_value = mock_response()
        
        # リクエスト送信
        response = self.client.post('/api/v2/chat', 
            json={'message': 'テスト'},
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'
        assert 'X-Service-Version' in response.headers
        assert response.headers['X-Service-Version'] == 'v2-new'
    
    @patch('app.process_chat_message_legacy')
    @patch('services.chat_service.ChatService.process_chat_message')
    def test_compare_endpoint(self, mock_new, mock_legacy):
        """比較エンドポイントのテスト"""
        # モック設定
        mock_legacy.return_value = "これは旧サービスの応答です"
        
        async def new_response(*args, **kwargs):
            for chunk in ["これは新サービスの応答です"]:
                yield chunk
        
        mock_new.return_value = new_response()
        
        # 比較エンドポイントを呼び出し
        response = self.client.post('/api/v2/chat/compare',
            json={'message': 'テストメッセージ'},
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # 比較結果の検証
        assert 'legacy' in data
        assert 'new' in data
        assert 'comparison' in data
        assert 'timestamp' in data
        
        # レスポンスが含まれることを確認
        assert data['legacy']['response'] == "これは旧サービスの応答です"
        assert data['new']['response'] == "これは新サービスの応答です"
        
        # 比較結果
        assert 'identical' in data['comparison']
        assert 'time_diff' in data['comparison']
    
    def test_feature_flags_integration(self):
        """フィーチャーフラグの統合テスト"""
        from config.feature_flags import feature_flags
        
        # デフォルト設定の確認
        config = feature_flags.get_config()
        assert config['service_mode'] in ['legacy', 'parallel', 'canary', 'new']
        
        # サービス判定のテスト
        should_use = feature_flags.should_use_new_service('chat', 'test-user')
        assert isinstance(should_use, bool)
    
    @pytest.mark.asyncio
    async def test_service_output_consistency(self):
        """サービス出力の一貫性テスト"""
        # サービスインスタンス作成
        llm_service = Mock(spec=LLMService)
        session_service = Mock(spec=SessionService)
        chat_service = ChatService(llm_service, session_service)
        
        # モック設定
        async def mock_stream(*args, **kwargs):
            for chunk in ["テスト", "応答"]:
                yield chunk
        
        llm_service.stream_chat_response = mock_stream
        session_service.get_current_model.return_value = "gemini-1.5-flash"
        session_service.get_chat_history.return_value = []
        
        # 実行
        result = ""
        async for chunk in chat_service.process_chat_message("テスト"):
            result += chunk
        
        assert result == "テスト応答"
    
    def test_backward_compatibility(self):
        """後方互換性のテスト（既存エンドポイントが動作すること）"""
        # CSRFトークンを取得
        csrf_response = self.client.get('/api/csrf-token')
        csrf_token = json.loads(csrf_response.data)['csrf_token']
        
        # 既存エンドポイントが引き続き動作することを確認
        with patch('app.process_chat_message_legacy') as mock_legacy:
            mock_legacy.return_value = "既存の応答"
            
            response = self.client.post('/api/chat',
                json={'message': 'テスト'},
                headers={
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrf_token
                }
            )
            
            # 既存エンドポイントが正常に動作
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'response' in data


class TestFeatureFlags:
    """フィーチャーフラグのテスト"""
    
    def test_service_mode_enum(self):
        """ServiceMode列挙型のテスト"""
        from config.feature_flags import ServiceMode
        
        assert ServiceMode.LEGACY.value == "legacy"
        assert ServiceMode.PARALLEL.value == "parallel"
        assert ServiceMode.CANARY.value == "canary"
        assert ServiceMode.NEW.value == "new"
    
    def test_canary_deployment(self):
        """カナリアデプロイメントのテスト"""
        from config.feature_flags import FeatureFlags
        import os
        
        # カナリアモードでテスト
        os.environ['SERVICE_MODE'] = 'canary'
        os.environ['AB_TEST_RATIO'] = '0.5'
        
        flags = FeatureFlags()
        
        # 複数のユーザーIDで一貫性をテスト
        user_results = {}
        for i in range(100):
            user_id = f"user_{i}"
            result = flags.should_use_new_service('chat', user_id)
            user_results[user_id] = result
        
        # 同じユーザーIDは常に同じ結果を返すことを確認
        for user_id, first_result in user_results.items():
            for _ in range(10):
                assert flags.should_use_new_service('chat', user_id) == first_result
        
        # おおよそ50%のユーザーが新サービスを使用（統計的な誤差を許容）
        new_service_count = sum(1 for r in user_results.values() if r)
        assert 30 < new_service_count < 70  # 30-70%の範囲