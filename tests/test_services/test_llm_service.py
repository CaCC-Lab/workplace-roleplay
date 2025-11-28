"""
LLMServiceのユニットテスト

注: これらのテストはLLMServiceの内部実装をモックして検証します。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
from typing import List, Dict, Any
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestLLMService:
    """LLMServiceのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        # APIキーマネージャーのモック
        self.mock_api_manager = Mock()
        self.mock_api_manager.get_api_key.return_value = "test-api-key"
        
        # Configのモック
        self.mock_config = Mock()
        self.mock_config.DEFAULT_TEMPERATURE = 0.7
        self.mock_config.GOOGLE_API_KEY = "test-api-key"
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.genai')
    def test_initialization(self, mock_genai, mock_api_manager_class):
        """サービスの初期化テスト"""
        from services.llm_service import LLMService
        
        # APIキーマネージャーのモック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # 検証
        assert service.config == self.mock_config
        assert service.default_temperature == 0.7
        mock_genai.configure.assert_called_once_with(api_key="test-api-key")
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.ChatGoogleGenerativeAI')
    @patch('services.llm_service.genai')
    def test_create_gemini_llm(self, mock_genai, mock_chat_model, mock_api_manager_class):
        """Gemini LLMの作成テスト"""
        from services.llm_service import LLMService
        
        # モック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        mock_llm_instance = Mock()
        mock_chat_model.return_value = mock_llm_instance
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # LLMを作成
        llm = service.create_gemini_llm("gemini-1.5-flash")
        
        # 検証
        mock_chat_model.assert_called()
        assert llm == mock_llm_instance
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.ChatGoogleGenerativeAI')
    @patch('services.llm_service.genai')
    def test_deprecated_model_replacement(self, mock_genai, mock_chat_model, mock_api_manager_class):
        """廃止されたモデルの自動置換テスト"""
        from services.llm_service import LLMService
        
        # モック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # 廃止されたモデルで作成
        service.create_gemini_llm("gemini-pro")
        
        # 新しいモデルで作成されることを検証
        mock_chat_model.assert_called()
        call_args = mock_chat_model.call_args[1]
        assert call_args['model'] == "gemini-1.5-flash"
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.genai')
    def test_initialize_llm_with_prefix(self, mock_genai, mock_api_manager_class):
        """プレフィックス付きモデル名の処理テスト"""
        from services.llm_service import LLMService
        
        # モック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # create_gemini_llmをモック
        service.create_gemini_llm = Mock(return_value=Mock())
        
        # プレフィックス付きで初期化
        service.initialize_llm("gemini/gemini-1.5-flash")
        
        # プレフィックスが削除されて呼ばれることを検証
        service.create_gemini_llm.assert_called_once_with("gemini-1.5-flash")
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.genai')
    def test_get_or_create_model_caching(self, mock_genai, mock_api_manager_class):
        """モデルキャッシュ機能のテスト"""
        from services.llm_service import LLMService
        
        # モック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        
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
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.genai')
    def test_build_messages(self, mock_genai, mock_api_manager_class):
        """メッセージ構築のテスト"""
        from services.llm_service import LLMService
        from langchain.schema import HumanMessage, AIMessage, SystemMessage
        
        # モック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # 履歴とシステムプロンプトを準備
        history = [
            {'human': 'こんにちは', 'ai': 'こんにちは！お元気ですか？'},
            {'human': '元気です', 'ai': 'それは良かったです！'}
        ]
        system_prompt = "あなたは親切なアシスタントです。"
        current_message = "今日は何をしましょうか？"
        
        # メッセージを構築
        messages = service._build_messages(history, current_message, system_prompt)
        
        # 検証
        assert len(messages) > 0
        assert isinstance(messages[0], SystemMessage)
        assert messages[0].content == system_prompt
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.genai')
    def test_get_available_models(self, mock_genai, mock_api_manager_class):
        """利用可能なモデル一覧の取得テスト"""
        from services.llm_service import LLMService
        
        # モック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # モデル一覧を取得
        models = service.get_available_models()
        
        # 検証
        assert isinstance(models, list)
        assert "gemini-1.5-flash" in models
        assert "gemini-1.5-pro" in models
        assert len(models) > 0
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.genai')
    def test_cleanup(self, mock_genai, mock_api_manager_class):
        """クリーンアップのテスト"""
        from services.llm_service import LLMService
        
        # モック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # モデルを追加
        service.models['test-model'] = Mock()
        
        # クリーンアップ
        service.cleanup()
        
        # 検証
        assert len(service.models) == 0
    
    @patch('services.llm_service.CompliantAPIManager')
    @patch('services.llm_service.ChatGoogleGenerativeAI')
    @patch('services.llm_service.genai')
    def test_error_handling_in_create_gemini_llm(self, mock_genai, mock_chat_model, mock_api_manager_class):
        """エラーハンドリングのテスト"""
        from services.llm_service import LLMService
        
        # モック設定
        mock_api_manager_class.return_value = self.mock_api_manager
        mock_chat_model.side_effect = Exception("API Error")
        
        # サービスを初期化
        service = LLMService(self.mock_config)
        
        # エラーが発生することを検証
        with pytest.raises(Exception) as exc_info:
            service.create_gemini_llm("gemini-1.5-flash")
        
        assert "API Error" in str(exc_info.value)


class TestLLMServiceDeprecatedModels:
    """廃止されたモデルの処理テスト"""
    
    def test_deprecated_models_mapping_exists(self):
        """廃止されたモデルのマッピングが存在することを確認"""
        from services.llm_service import LLMService
        
        assert hasattr(LLMService, 'DEPRECATED_MODELS')
        assert isinstance(LLMService.DEPRECATED_MODELS, dict)
        assert len(LLMService.DEPRECATED_MODELS) > 0
    
    def test_gemini_pro_is_deprecated(self):
        """gemini-proが廃止モデルリストに含まれることを確認"""
        from services.llm_service import LLMService
        
        assert 'gemini-pro' in LLMService.DEPRECATED_MODELS
    
    def test_available_models_list_exists(self):
        """利用可能なモデルリストが存在することを確認"""
        from services.llm_service import LLMService
        
        assert hasattr(LLMService, 'AVAILABLE_MODELS')
        assert isinstance(LLMService.AVAILABLE_MODELS, list)
        assert 'gemini-1.5-flash' in LLMService.AVAILABLE_MODELS
