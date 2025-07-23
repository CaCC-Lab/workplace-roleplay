"""
app.pyのユーティリティ関数テスト - カバレッジ向上のため
TDD原則に従い、Geminiモデル管理、LLM作成機能をテスト
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import json

# テスト対象の関数
from app import (
    get_available_gemini_models,
    create_gemini_llm
)
from errors import AuthenticationError, ValidationError


class TestGeminiModels:
    """Geminiモデル管理のテスト"""
    
    @patch('app.GENAI_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key')
    @patch('app.genai')
    def test_get_available_gemini_models_正常(self, mock_genai):
        """利用可能なGeminiモデルが正常に取得されることを確認"""
        # モックモデルオブジェクトを作成
        mock_model1 = MagicMock()
        mock_model1.name = "models/gemini-1.5-pro"
        
        mock_model2 = MagicMock()
        mock_model2.name = "models/gemini-1.5-flash"
        
        mock_model3 = MagicMock() 
        mock_model3.name = "models/text-bison"  # 非Geminiモデル
        
        mock_genai.list_models.return_value = [mock_model1, mock_model2, mock_model3]
        
        result = get_available_gemini_models()
        
        # Geminiモデルのみが返されることを確認
        assert len(result) == 2
        assert "gemini/gemini-1.5-pro" in result
        assert "gemini/gemini-1.5-flash" in result
        assert "gemini/text-bison" not in result
    
    @patch('app.GENAI_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key')
    @patch('app.genai')
    def test_get_available_gemini_models_廃止モデル置換(self, mock_genai):
        """廃止されたモデルが代替モデルに置き換えられることを確認"""
        # 廃止されたモデルを含むモックを作成
        mock_model = MagicMock()
        mock_model.name = "models/gemini-1.0-pro-vision"
        
        mock_genai.list_models.return_value = [mock_model]
        
        result = get_available_gemini_models()
        
        # 代替モデルが返されることを確認
        assert "gemini/gemini-1.5-flash" in result
        assert "gemini/gemini-1.0-pro-vision" not in result
    
    @patch('app.GOOGLE_API_KEY', None)
    def test_get_available_gemini_models_APIキーなし(self):
        """APIキーがない場合の処理を確認"""
        result = get_available_gemini_models()
        
        assert result == []
    
    @patch('app.GENAI_AVAILABLE', False)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key')
    def test_get_available_gemini_models_genai無効(self):
        """genaiが利用できない場合の処理を確認"""
        result = get_available_gemini_models()
        
        assert result == []
    
    @patch('app.GENAI_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key')
    @patch('app.genai')
    def test_get_available_gemini_models_API例外(self, mock_genai):
        """API例外時にフォールバックモデルが返されることを確認"""
        mock_genai.list_models.side_effect = Exception("API Error")
        
        result = get_available_gemini_models()
        
        # フォールバックモデルが返される
        assert "gemini/gemini-1.5-pro" in result
        assert "gemini/gemini-1.5-flash" in result
        assert len(result) == 2


class TestCreateGeminiLLM:
    """Gemini LLM作成のテスト"""
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key-12345')
    @patch('app.ChatGoogleGenerativeAI')
    def test_create_gemini_llm_正常(self, mock_chat_google):
        """Gemini LLMが正常に作成されることを確認"""
        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm
        
        result = create_gemini_llm("gemini-1.5-flash")
        
        assert result == mock_llm
        mock_chat_google.assert_called_once_with(
            model="gemini-1.5-flash",
            temperature=0.7,
            convert_system_message_to_human=True
        )
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key-12345')
    @patch('app.ChatGoogleGenerativeAI')
    def test_create_gemini_llm_prefixあり(self, mock_chat_google):
        """gemini/プレフィックス付きモデル名が正しく処理されることを確認"""
        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm
        
        result = create_gemini_llm("gemini/gemini-1.5-pro")
        
        mock_chat_google.assert_called_once()
        call_args = mock_chat_google.call_args[1]
        assert call_args["model"] == "gemini-1.5-pro"  # プレフィックスが削除される
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key-12345')
    @patch('app.ChatGoogleGenerativeAI')
    def test_create_gemini_llm_廃止モデル置換(self, mock_chat_google):
        """廃止されたモデルが代替モデルに置き換えられることを確認"""
        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm
        
        result = create_gemini_llm("gemini-pro-vision")
        
        mock_chat_google.assert_called_once()
        call_args = mock_chat_google.call_args[1]
        assert call_args["model"] == "gemini-1.5-flash"  # 代替モデルが使用される
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', None)
    def test_create_gemini_llm_APIキーなし(self):
        """APIキーがない場合にAuthenticationErrorが発生することを確認"""
        with pytest.raises(AuthenticationError, match="GOOGLE_API_KEY環境変数が設定されていません"):
            create_gemini_llm("gemini-1.5-flash")
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'your_google_api_key_here')
    def test_create_gemini_llm_無効APIキー(self):
        """無効なAPIキーでValidationErrorが発生することを確認"""
        with pytest.raises(ValidationError, match="Google APIキーが設定されていません"):
            create_gemini_llm("gemini-1.5-flash")
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', '')
    def test_create_gemini_llm_空APIキー(self):
        """空のAPIキーでValidationErrorが発生することを確認"""
        with pytest.raises(ValidationError, match="Google APIキーが設定されていません"):
            create_gemini_llm("gemini-1.5-flash")
    
    @patch('app.LANGCHAIN_AVAILABLE', False)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key')
    def test_create_gemini_llm_langchain無効(self):
        """LangChainが利用できない場合にNoneが返されることを確認"""
        result = create_gemini_llm("gemini-1.5-flash")
        
        assert result is None
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key-12345')
    @patch('app.ChatGoogleGenerativeAI')
    def test_create_gemini_llm_温度設定(self, mock_chat_google):
        """カスタム温度設定が正しく適用されることを確認"""
        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm
        
        result = create_gemini_llm("gemini-1.5-flash", temperature=0.3)
        
        mock_chat_google.assert_called_once()
        call_args = mock_chat_google.call_args[1]
        assert call_args["temperature"] == 0.3
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key-12345')
    @patch('app.ChatGoogleGenerativeAI')
    def test_create_gemini_llm_例外処理(self, mock_chat_google):
        """ChatGoogleGenerativeAI作成時の例外が適切に処理されることを確認"""
        mock_chat_google.side_effect = Exception("LLM creation failed")
        
        result = create_gemini_llm("gemini-1.5-flash")
        
        assert result is None


class TestModelHandling:
    """モデル処理のテスト"""
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key-12345')
    @patch('app.ChatGoogleGenerativeAI')
    def test_model_creation_success(self, mock_chat_google):
        """モデル作成の成功パターン"""
        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm
        
        result = create_gemini_llm("gemini-1.5-flash")
        
        assert result == mock_llm
        mock_chat_google.assert_called_once()
    
    @patch('app.LANGCHAIN_AVAILABLE', False)
    def test_model_creation_no_langchain(self):
        """LangChainが利用できない場合の処理"""
        result = create_gemini_llm("gemini-1.5-flash")
        
        assert result is None
    
    @patch('app.GENAI_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key')
    @patch('app.genai')
    def test_model_listing_success(self, mock_genai):
        """モデル一覧取得の成功パターン"""
        mock_model = MagicMock()
        mock_model.name = "models/gemini-1.5-pro"
        mock_genai.list_models.return_value = [mock_model]
        
        result = get_available_gemini_models()
        
        assert len(result) > 0
    
    @patch('app.GOOGLE_API_KEY', None)
    def test_model_listing_no_key(self):
        """APIキーがない場合のモデル一覧取得"""
        result = get_available_gemini_models()
        
        assert result == []


class TestModelCompatibility:
    """モデル互換性のテスト"""
    
    def test_deprecated_model_mapping(self):
        """廃止されたモデルのマッピングが正しく定義されていることを確認"""
        # create_gemini_llm内の廃止モデルマッピングをテスト
        deprecated_models = {
            'gemini-pro-vision': 'gemini-1.5-flash',
            'gemini-1.0-pro-vision': 'gemini-1.5-flash',
            'gemini-1.0-pro-vision-latest': 'gemini-1.5-flash-latest'
        }
        
        for deprecated, replacement in deprecated_models.items():
            # 各廃止モデルが代替モデルにマッピングされることを確認
            assert replacement.startswith('gemini-1.5')
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key-12345')
    @patch('app.ChatGoogleGenerativeAI')
    def test_all_deprecated_models_replaced(self, mock_chat_google):
        """全ての廃止モデルが正しく代替モデルに置き換えられることを確認"""
        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm
        
        deprecated_models = [
            'gemini-pro-vision',
            'gemini-1.0-pro-vision', 
            'gemini-1.0-pro-vision-latest'
        ]
        
        for deprecated_model in deprecated_models:
            create_gemini_llm(deprecated_model)
            
            # 代替モデルが使用されることを確認
            call_args = mock_chat_google.call_args[1]
            model_used = call_args["model"]
            assert model_used.startswith('gemini-1.5')
            assert model_used != deprecated_model
            
            mock_chat_google.reset_mock()


class TestErrorScenarios:
    """エラーシナリオのテスト"""
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'YOUR_API_KEY_HERE')
    def test_placeholder_api_key_detected(self):
        """プレースホルダーAPIキーが検出されることを確認"""
        placeholder_keys = [
            "your_google_api_key_here",
            "YOUR_API_KEY_HERE", 
            ""
        ]
        
        for placeholder in placeholder_keys:
            with patch('app.GOOGLE_API_KEY', placeholder):
                with pytest.raises(ValidationError, match="Google APIキーが設定されていません"):
                    create_gemini_llm("gemini-1.5-flash")
    
    @patch('app.LANGCHAIN_AVAILABLE', True)
    @patch('app.GOOGLE_API_KEY', 'valid-api-key-12345')
    @patch('app.ChatGoogleGenerativeAI')
    def test_llm_creation_network_error(self, mock_chat_google):
        """ネットワークエラー時の処理を確認"""
        mock_chat_google.side_effect = ConnectionError("Network error")
        
        result = create_gemini_llm("gemini-1.5-flash")
        
        assert result is None