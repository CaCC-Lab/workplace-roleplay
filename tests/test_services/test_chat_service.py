"""
ChatServiceのユニットテスト
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import json
from datetime import datetime

from services.chat_service import ChatService
from errors import ValidationError, ExternalAPIError


class TestChatService:
    """ChatServiceのテストクラス"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """依存関係のモック"""
        with patch('services.chat_service.LLMService') as mock_llm_service, \
             patch('services.chat_service.SessionService') as mock_session_service, \
             patch('services.chat_service.SecurityUtils') as mock_security:
            
            # LLMServiceのモック設定
            mock_llm = MagicMock()
            mock_llm_service.create_llm.return_value = mock_llm
            mock_llm_service.add_messages_from_history = MagicMock()
            mock_llm_service.try_multiple_models_for_prompt.return_value = ("フィードバック", "gemini-1.5-flash", None)
            
            # SessionServiceのモック設定
            mock_session_service.get_session_data.return_value = 'gemini-1.5-flash'
            mock_session_service.get_session_history.return_value = []
            
            # SecurityUtilsのモック設定
            mock_security.sanitize_input.side_effect = lambda x: x
            
            yield {
                'llm_service': mock_llm_service,
                'session_service': mock_session_service,
                'security': mock_security,
                'llm': mock_llm
            }
    
    def test_handle_chat_message_正常系(self, mock_dependencies):
        """チャットメッセージの正常処理"""
        # ストリーミングレスポンスのモック
        mock_chunk1 = MagicMock()
        mock_chunk1.content = "こんにちは"
        mock_chunk2 = MagicMock()
        mock_chunk2.content = "！"
        
        mock_chain = MagicMock()
        mock_chain.stream.return_value = [mock_chunk1, mock_chunk2]
        
        # チェーンの作成をモック
        with patch('services.chat_service.ChatPromptTemplate') as mock_prompt:
            mock_prompt.from_messages.return_value.__or__.return_value = mock_chain
            
            # generatorを実行してレスポンスを収集
            responses = list(ChatService.handle_chat_message("テストメッセージ"))
            
            # レスポンスの検証
            assert len(responses) == 3  # 2つのコンテンツ + 完了メッセージ
            
            # 最初のチャンク
            data1 = json.loads(responses[0].replace('data: ', ''))
            assert data1['content'] == 'こんにちは'
            assert data1['type'] == 'content'
            
            # 2番目のチャンク
            data2 = json.loads(responses[1].replace('data: ', ''))
            assert data2['content'] == '！'
            
            # 完了メッセージ
            data3 = json.loads(responses[2].replace('data: ', ''))
            assert data3['type'] == 'done'
    
    def test_handle_chat_message_空メッセージエラー(self, mock_dependencies):
        """空のメッセージでValidationError"""
        with pytest.raises(ValidationError, match="メッセージを入力してください"):
            list(ChatService.handle_chat_message(""))
        
        with pytest.raises(ValidationError, match="メッセージを入力してください"):
            list(ChatService.handle_chat_message("   "))
    
    def test_handle_chat_message_セキュリティサニタイズ(self, mock_dependencies):
        """XSS対策のサニタイズが実行される"""
        list(ChatService.handle_chat_message("<script>alert('XSS')</script>"))
        
        mock_dependencies['security'].sanitize_input.assert_called_once_with("<script>alert('XSS')</script>")
    
    def test_handle_chat_message_デフォルトモデル使用(self, mock_dependencies):
        """モデル未指定時はセッションから取得"""
        mock_dependencies['session_service'].get_session_data.return_value = 'gemini-1.5-pro'
        
        with patch('services.chat_service.ChatPromptTemplate'):
            list(ChatService.handle_chat_message("テスト"))
            
            mock_dependencies['llm_service'].create_llm.assert_called_once_with('gemini-1.5-pro')
    
    def test_handle_chat_message_指定モデル使用(self, mock_dependencies):
        """明示的に指定されたモデルを使用"""
        with patch('services.chat_service.ChatPromptTemplate'):
            list(ChatService.handle_chat_message("テスト", model_name="gemini-1.5-flash"))
            
            mock_dependencies['llm_service'].create_llm.assert_called_once_with('gemini-1.5-flash')
    
    def test_handle_chat_message_履歴の保存(self, mock_dependencies):
        """会話履歴が正しく保存される"""
        mock_chunk = MagicMock()
        mock_chunk.content = "応答内容"
        
        mock_chain = MagicMock()
        mock_chain.stream.return_value = [mock_chunk]
        
        with patch('services.chat_service.ChatPromptTemplate') as mock_prompt:
            mock_prompt.from_messages.return_value.__or__.return_value = mock_chain
            
            list(ChatService.handle_chat_message("ユーザーメッセージ"))
            
            # 履歴への追加を確認
            mock_dependencies['session_service'].add_to_session_history.assert_called_once()
            call_args = mock_dependencies['session_service'].add_to_session_history.call_args[0]
            
            assert call_args[0] == 'chat_history'
            assert call_args[1]['user'] == 'ユーザーメッセージ'
            assert call_args[1]['assistant'] == '応答内容'
            assert 'timestamp' in call_args[1]
            assert call_args[1]['model'] == 'gemini-1.5-flash'
    
    def test_handle_chat_message_ストリーミングエラー(self, mock_dependencies):
        """ストリーミング中のエラー処理"""
        mock_chain = MagicMock()
        mock_chain.stream.side_effect = Exception("ストリーミングエラー")
        
        with patch('services.chat_service.ChatPromptTemplate') as mock_prompt:
            mock_prompt.from_messages.return_value.__or__.return_value = mock_chain
            
            with pytest.raises(ExternalAPIError, match="チャット応答の生成に失敗しました"):
                responses = list(ChatService.handle_chat_message("テスト"))
                
                # エラーメッセージが含まれることを確認
                error_response = None
                for response in responses:
                    if 'error' in response:
                        error_response = json.loads(response.replace('data: ', ''))
                        break
                
                assert error_response is not None
                assert error_response['type'] == 'error'
    
    def test_generate_chat_feedback_履歴なし(self, mock_dependencies):
        """履歴がない場合のフィードバック生成"""
        mock_dependencies['session_service'].get_session_history.return_value = []
        
        result = ChatService.generate_chat_feedback()
        
        assert result['feedback'] == 'まだ会話履歴がありません。まずは雑談を楽しんでみましょう！'
        assert result['conversation_count'] == 0
    
    def test_generate_chat_feedback_履歴あり(self, mock_dependencies):
        """履歴がある場合のフィードバック生成"""
        history = [
            {'user': 'こんにちは', 'assistant': 'こんにちは！'},
            {'user': '今日の天気は？', 'assistant': '晴れみたいですね。'}
        ]
        mock_dependencies['session_service'].get_session_history.return_value = history
        
        result = ChatService.generate_chat_feedback()
        
        assert result['feedback'] == 'フィードバック'
        assert result['conversation_count'] == 2
        assert result['model'] == 'gemini-1.5-flash'
        assert 'recent_topics' in result
    
    def test_generate_chat_feedback_エラー時(self, mock_dependencies):
        """フィードバック生成エラー時の処理"""
        history = [{'user': 'test', 'assistant': 'response'}]
        mock_dependencies['session_service'].get_session_history.return_value = history
        mock_dependencies['llm_service'].try_multiple_models_for_prompt.side_effect = Exception("生成エラー")
        
        result = ChatService.generate_chat_feedback()
        
        assert result['feedback'] == 'フィードバックの生成中にエラーが発生しました。'
        assert result['conversation_count'] == 1
        assert 'error' in result
    
    def test_extract_topics_基本抽出(self):
        """話題の基本的な抽出"""
        history = [
            {'user': '仕事が忙しくて大変です'},
            {'user': '週末は映画を見に行きました'},
            {'user': '最近料理を始めました'}
        ]
        
        topics = ChatService._extract_topics(history)
        
        # 少なくとも1つの話題が抽出されることを確認
        assert len(topics) >= 1
        assert len(topics) <= 3
        # 抽出された話題はユーザーメッセージに関連しているはず
        all_text = ' '.join([h['user'] for h in history])
        for topic in topics:
            assert len(topic) > 0  # 空の話題ではない
    
    def test_extract_topics_重複排除(self):
        """重複する話題の排除"""
        history = [
            {'user': '仕事の話です'},
            {'user': '仕事について相談があります'},
            {'user': '趣味の話をしましょう'}
        ]
        
        topics = ChatService._extract_topics(history)
        
        assert topics.count('仕事') == 1
        assert '趣味' in topics
    
    def test_clear_chat_history(self, mock_dependencies):
        """チャット履歴のクリア"""
        result = ChatService.clear_chat_history()
        
        mock_dependencies['session_service'].clear_session_history.assert_called_once_with('chat_history')
        assert result['message'] == 'チャット履歴をクリアしました'