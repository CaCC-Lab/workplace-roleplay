"""
LLMServiceのユニットテスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from typing import List, Dict, Any
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.llm_service import LLMService
from langchain.schema import HumanMessage, AIMessage, SystemMessage


class TestLLMService:
    """LLMServiceのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        # APIキーマネージャーのモック
        self.mock_api_key_manager = Mock()
        self.mock_api_key_manager.get_next_key.return_value = "test-api-key"
        
        # Configのモック
        self.mock_config = Mock()
        self.mock_config.DEFAULT_TEMPERATURE = 0.7
        
    @patch('services.llm_service.APIKeyManager')
    @patch('services.llm_service.genai')
    def test_initialization(self, mock_genai, mock_api_key_manager_class):
        """サービスの初期化テスト"""
        # APIキーマネージャーのモック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # 検証
        assert service.config == self.mock_config
        assert service.default_temperature == 0.7
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")
    
    @patch('services.llm_service.APIKeyManager')
    @patch('services.llm_service.ChatGoogleGenerativeAI')
    def test_create_gemini_llm(self, mock_chat_model, mock_api_key_manager_class):
        """Gemini LLMの作成テスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        mock_llm_instance = Mock()
        mock_chat_model.return_value = mock_llm_instance
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # LLMを作成
        llm = service.create_gemini_llm("gemini-1.5-flash")
        
        # 検証
        mock_chat_model.assert_called_once_with(
            model="gemini-1.5-flash",
            google_api_key="test-api-key",
            temperature=0.7,
            convert_system_message_to_human=True,
            streaming=True
        )
        assert llm == mock_llm_instance
        self.mock_api_key_manager.record_usage.assert_called_once_with("test-api-key")
    
    @patch('services.llm_service.APIKeyManager')
    @patch('services.llm_service.ChatGoogleGenerativeAI')
    def test_deprecated_model_replacement(self, mock_chat_model, mock_api_key_manager_class):
        """廃止されたモデルの自動置換テスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # 廃止されたモデルで作成
        service.create_gemini_llm("gemini-pro")
        
        # 新しいモデルで作成されることを検証
        mock_chat_model.assert_called_once()
        call_args = mock_chat_model.call_args[1]
        assert call_args['model'] == "gemini-1.5-flash"
    
    @patch('services.llm_service.APIKeyManager')
    def test_initialize_llm_with_prefix(self, mock_api_key_manager_class):
        """プレフィックス付きモデル名の処理テスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # create_gemini_llmをモック
        service.create_gemini_llm = Mock(return_value=Mock())
        
        # プレフィックス付きで初期化
        service.initialize_llm("gemini/gemini-1.5-flash")
        
        # プレフィックスが削除されて呼ばれることを検証
        service.create_gemini_llm.assert_called_once_with("gemini-1.5-flash")
    
    @patch('services.llm_service.APIKeyManager')
    def test_get_or_create_model_caching(self, mock_api_key_manager_class):
        """モデルキャッシュ機能のテスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # initialize_llmをモック
        mock_model = Mock()
        service.initialize_llm = Mock(return_value=mock_model)
        
        # 初回取得
        model1 = service.get_or_create_model("gemini-1.5-flash")
        assert model1 == mock_model
        service.initialize_llm.assert_called_once()
        
        # 2回目取得（キャッシュから）
        model2 = service.get_or_create_model("gemini-1.5-flash")
        assert model2 == mock_model
        assert service.initialize_llm.call_count == 1  # 追加で呼ばれない
    
    @patch('services.llm_service.APIKeyManager')
    def test_build_messages(self, mock_api_key_manager_class):
        """メッセージ構築のテスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # 履歴とシステムプロンプトを準備
        history = [
            {'human': 'こんにちは'},
            {'ai': 'こんにちは！お元気ですか？'},
            {'human': '元気です'}
        ]
        system_prompt = "あなたは親切なアシスタントです。"
        
        # メッセージを構築
        messages = service._build_messages(history, "今日は何をしましょうか？", system_prompt)
        
        # 検証
        assert len(messages) == 5
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == system_prompt
        assert isinstance(messages[1], HumanMessage)
        assert messages[1].content == "こんにちは"
        assert isinstance(messages[2], AIMessage)
        assert messages[2].content == "こんにちは！お元気ですか？"
        assert isinstance(messages[3], HumanMessage)
        assert messages[3].content == "元気です"
        assert isinstance(messages[4], HumanMessage)
        assert messages[4].content == "今日は何をしましょうか？"
    
    @pytest.mark.asyncio
    @patch('services.llm_service.APIKeyManager')
    async def test_stream_chat_response(self, mock_api_key_manager_class):
        """ストリーミングレスポンスのテスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # LLMのモック
        mock_llm = AsyncMock()
        async def mock_astream(messages):
            chunks = ["こんにちは", "！", "お元気", "ですか", "？"]
            for chunk in chunks:
                mock_chunk = Mock()
                mock_chunk.content = chunk
                yield mock_chunk
        
        mock_llm.astream = mock_astream
        service.get_or_create_model = Mock(return_value=mock_llm)
        
        # ストリーミングレスポンスを取得
        response_chunks = []
        async for chunk in service.stream_chat_response(
            "こんにちは",
            [],
            "gemini-1.5-flash",
            "あなたは親切なアシスタントです。"
        ):
            response_chunks.append(chunk)
        
        # 検証
        assert response_chunks == ["こんにちは", "！", "お元気", "ですか", "？"]
    
    @patch('services.llm_service.APIKeyManager')
    def test_invoke_sync(self, mock_api_key_manager_class):
        """同期的な呼び出しのテスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # LLMのモック
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "こんにちは！お元気ですか？"
        mock_llm.invoke.return_value = mock_response
        service.get_or_create_model = Mock(return_value=mock_llm)
        
        # 同期呼び出し
        result = service.invoke_sync("こんにちは", extract_content=True)
        
        # 検証
        assert result == "こんにちは！お元気ですか？"
        mock_llm.invoke.assert_called_once_with("こんにちは")
    
    @patch('services.llm_service.APIKeyManager')
    def test_get_available_models(self, mock_api_key_manager_class):
        """利用可能なモデル一覧の取得テスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # モデル一覧を取得
        models = service.get_available_models()
        
        # 検証
        assert isinstance(models, list)
        assert "gemini-1.5-flash" in models
        assert "gemini-1.5-pro" in models
        assert len(models) > 0
    
    @patch('services.llm_service.APIKeyManager')
    def test_cleanup(self, mock_api_key_manager_class):
        """クリーンアップのテスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # モデルを追加
        service.models['test-model'] = Mock()
        
        # クリーンアップ
        service.cleanup()
        
        # 検証
        assert len(service.models) == 0
    
    @patch('services.llm_service.APIKeyManager')
    @patch('services.llm_service.ChatGoogleGenerativeAI')
    def test_error_handling_in_create_gemini_llm(self, mock_chat_model, mock_api_key_manager_class):
        """エラーハンドリングのテスト"""
        # モック設定
        mock_api_key_manager_class.return_value = self.mock_api_key_manager
        mock_chat_model.side_effect = Exception("API Error")
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # エラーが発生することを検証
        with pytest.raises(Exception) as exc_info:
            service.create_gemini_llm("gemini-1.5-flash")
        
        assert "API Error" in str(exc_info.value)
        self.mock_api_key_manager.record_error.assert_called_once()