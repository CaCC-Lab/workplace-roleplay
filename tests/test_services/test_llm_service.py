"""
LLMServiceのユニットテスト
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import os

from services.llm_service import LLMService
from errors import AuthenticationError, ValidationError


class TestLLMService:
    """LLMServiceのテストクラス"""
    
    @pytest.fixture
    def mock_env_with_api_key(self):
        """APIキーを含む環境変数のモック"""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'AIzaSyTest123456789'}, clear=False):
            yield
    
    @pytest.fixture
    def mock_config(self):
        """設定のモック"""
        with patch('services.llm_service.get_cached_config') as mock:
            config = MagicMock()
            config.GOOGLE_API_KEY = 'AIzaSyTest123456789'
            mock.return_value = config
            yield mock
    
    def test_get_available_models_正常系(self, mock_config):
        """利用可能なモデル情報の取得"""
        with patch('services.llm_service.genai.configure'):
            models = LLMService.get_available_models()
            
            assert isinstance(models, dict)
            assert 'gemini/gemini-1.5-pro' in models
            assert 'gemini/gemini-1.5-flash' in models
            assert models['gemini/gemini-1.5-pro']['temperature'] == 0.7
            assert models['gemini/gemini-1.5-flash']['temperature'] == 0.9
    
    def test_get_available_models_APIキーなし(self):
        """APIキーがない場合は空の辞書を返す"""
        with patch('services.llm_service.get_cached_config') as mock_config:
            config = MagicMock()
            config.GOOGLE_API_KEY = None
            mock_config.return_value = config
            
            with patch.dict(os.environ, {}, clear=True):
                models = LLMService.get_available_models()
                assert models == {}
    
    def test_create_llm_正常系(self, mock_env_with_api_key):
        """LLMインスタンスの正常作成"""
        with patch('services.llm_service.get_google_api_key', return_value='AIzaSyTest123456789'):
            with patch('services.llm_service.ChatGoogleGenerativeAI') as mock_llm:
                with patch('services.llm_service.record_api_usage'):
                    llm = LLMService.create_llm('gemini-1.5-flash')
                    
                    mock_llm.assert_called_once_with(
                        model='gemini-1.5-flash',
                        google_api_key='AIzaSyTest123456789',
                        temperature=0.9,
                        max_output_tokens=4096,
                        convert_system_message_to_human=True,
                        streaming=True
                    )
                    assert llm is not None
    
    def test_create_llm_APIキー取得エラー(self):
        """APIキー取得エラー時の処理"""
        with patch('services.llm_service.get_google_api_key', side_effect=Exception("API key error")):
            with pytest.raises(AuthenticationError, match="Google APIキーの取得に失敗しました"):
                LLMService.create_llm('gemini-1.5-flash')
    
    def test_create_llm_無効なAPIキー形式(self):
        """無効なAPIキー形式の検証"""
        with patch('services.llm_service.get_google_api_key', return_value='invalid-key'):
            with pytest.raises(AuthenticationError, match="無効なGoogle APIキー形式です"):
                LLMService.create_llm('gemini-1.5-flash')
    
    def test_create_llm_サポートされていないモデル(self, mock_env_with_api_key):
        """サポートされていないモデルの検証"""
        with patch('services.llm_service.get_google_api_key', return_value='AIzaSyTest123456789'):
            with pytest.raises(ValidationError) as exc_info:
                LLMService.create_llm('unsupported-model')
            
            assert "サポートされていないモデル" in str(exc_info.value)
            assert exc_info.value.field == "model_name"
    
    def test_create_llm_プレフィックス付きモデル名(self, mock_env_with_api_key):
        """gemini/プレフィックス付きモデル名の処理"""
        with patch('services.llm_service.get_google_api_key', return_value='AIzaSyTest123456789'):
            with patch('services.llm_service.ChatGoogleGenerativeAI') as mock_llm:
                with patch('services.llm_service.record_api_usage'):
                    llm = LLMService.create_llm('gemini/gemini-1.5-flash')
                    
                    # プレフィックスが除去されていることを確認
                    mock_llm.assert_called_once()
                    call_args = mock_llm.call_args[1]
                    assert call_args['model'] == 'gemini-1.5-flash'
    
    def test_initialize_llm_エイリアス(self, mock_env_with_api_key):
        """initialize_llmがcreate_llmのエイリアスとして機能"""
        with patch.object(LLMService, 'create_llm') as mock_create:
            LLMService.initialize_llm('gemini-1.5-pro')
            mock_create.assert_called_once_with('gemini-1.5-pro')
    
    def test_extract_content_各種形式(self):
        """様々な形式からのコンテンツ抽出"""
        # contentプロパティを持つオブジェクト
        obj_with_content = MagicMock()
        obj_with_content.content = "test content"
        assert LLMService.extract_content(obj_with_content) == "test content"
        
        # textプロパティを持つオブジェクト
        obj_with_text = MagicMock()
        obj_with_text.text = "test text"
        del obj_with_text.content  # contentプロパティを削除
        assert LLMService.extract_content(obj_with_text) == "test text"
        
        # 文字列
        assert LLMService.extract_content("plain string") == "plain string"
        
        # contentキーを持つ辞書
        assert LLMService.extract_content({'content': 'dict content'}) == 'dict content'
        
        # textキーを持つ辞書
        assert LLMService.extract_content({'text': 'dict text'}) == 'dict text'
        
        # その他のオブジェクト
        assert LLMService.extract_content(12345) == "12345"
    
    def test_create_chat_prompt_履歴あり(self):
        """履歴を含むチャットプロンプトの作成"""
        prompt = LLMService.create_chat_prompt("システムプロンプト", include_history=True)
        
        messages = prompt.messages
        assert len(messages) == 3
        assert messages[0][0] == "system"
        assert messages[0][1] == "システムプロンプト"
        assert messages[1].variable_name == "history"
        assert messages[2][0] == "human"
        assert messages[2][1] == "{input}"
    
    def test_create_chat_prompt_履歴なし(self):
        """履歴を含まないチャットプロンプトの作成"""
        prompt = LLMService.create_chat_prompt("システムプロンプト", include_history=False)
        
        messages = prompt.messages
        assert len(messages) == 2
        assert messages[0][0] == "system"
        assert messages[1][0] == "human"
    
    def test_add_messages_from_history_基本(self):
        """履歴からメッセージを追加"""
        messages = []
        history = [
            {'user': 'ユーザー質問1', 'assistant': 'アシスタント回答1'},
            {'user': 'ユーザー質問2', 'assistant': 'アシスタント回答2'}
        ]
        
        LLMService.add_messages_from_history(messages, history)
        
        assert len(messages) == 4
        assert messages[0].content == 'ユーザー質問1'
        assert messages[1].content == 'アシスタント回答1'
        assert messages[2].content == 'ユーザー質問2'
        assert messages[3].content == 'アシスタント回答2'
    
    def test_add_messages_from_history_最大エントリ制限(self):
        """最大エントリ数の制限"""
        messages = []
        history = [{'user': f'質問{i}', 'assistant': f'回答{i}'} for i in range(10)]
        
        LLMService.add_messages_from_history(messages, history, max_entries=3)
        
        # 最後の3エントリのみが追加される
        assert len(messages) == 6  # 3エントリ × 2メッセージ
        assert messages[0].content == '質問7'
        assert messages[-1].content == '回答9'
    
    def test_try_multiple_models_for_prompt_成功(self, mock_env_with_api_key):
        """複数モデルでのプロンプト実行（成功）"""
        with patch('services.llm_service.get_google_api_key', return_value='AIzaSyTest123456789'):
            with patch.object(LLMService, 'create_llm') as mock_create:
                mock_llm = MagicMock()
                mock_response = MagicMock()
                mock_response.content = "成功した応答"
                mock_llm.invoke.return_value = mock_response
                mock_create.return_value = mock_llm
                
                content, model, error = LLMService.try_multiple_models_for_prompt("テストプロンプト")
                
                assert content == "成功した応答"
                assert model == "gemini-1.5-flash"
                assert error is None
    
    def test_try_multiple_models_for_prompt_最初失敗_次成功(self, mock_env_with_api_key):
        """最初のモデルが失敗し、次のモデルで成功"""
        with patch('services.llm_service.get_google_api_key', return_value='AIzaSyTest123456789'):
            with patch.object(LLMService, 'create_llm') as mock_create:
                # 最初のモデルは失敗
                mock_llm1 = MagicMock()
                mock_llm1.invoke.side_effect = Exception("モデル1エラー")
                
                # 2番目のモデルは成功
                mock_llm2 = MagicMock()
                mock_response2 = MagicMock()
                mock_response2.content = "2番目で成功"
                mock_llm2.invoke.return_value = mock_response2
                
                mock_create.side_effect = [mock_llm1, mock_llm2]
                
                content, model, error = LLMService.try_multiple_models_for_prompt("テストプロンプト")
                
                assert content == "2番目で成功"
                assert model == "gemini-1.5-pro"
                assert error is None
    
    def test_try_multiple_models_for_prompt_全て失敗(self, mock_env_with_api_key):
        """すべてのモデルで失敗"""
        with patch('services.llm_service.get_google_api_key', return_value='AIzaSyTest123456789'):
            with patch.object(LLMService, 'create_llm') as mock_create:
                mock_llm = MagicMock()
                mock_llm.invoke.side_effect = Exception("エラー")
                mock_create.return_value = mock_llm
                
                content, model, error = LLMService.try_multiple_models_for_prompt("テストプロンプト")
                
                assert content == ""
                assert model == ""
                assert "すべてのモデルで生成に失敗しました" in error