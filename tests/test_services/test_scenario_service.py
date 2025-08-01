"""
ScenarioServiceの包括的なユニットテスト
"""
import pytest
from unittest.mock import patch, MagicMock
import json

from services.scenario_service import ScenarioService
from errors import NotFoundError, ValidationError, ExternalAPIError


class TestScenarioService:
    """ScenarioServiceのテストクラス"""
    
    @pytest.fixture
    def mock_scenarios(self):
        """モックシナリオデータ"""
        return {
            'scenario_001': {
                'title': 'プレゼンテーション',
                'description': 'プレゼンの練習',
                'character': {
                    'name': '田中部長',
                    'role': '上司',
                    'personality': '厳格だが公正'
                },
                'situation': '月例会議でのプレゼン',
                'difficulty': '中級',
                'tags': ['プレゼン', 'ビジネス'],
                'learning_points': ['論理的説明', '質問対応'],
                'feedback_points': ['構成', '説得力']
            }
        }
    
    def test_get_scenario_正常系(self, mock_scenarios):
        """シナリオ取得の正常系テスト"""
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios):
            scenario = ScenarioService.get_scenario('scenario_001')
            
            assert scenario['title'] == 'プレゼンテーション'
            assert scenario['character']['name'] == '田中部長'
    
    def test_get_scenario_存在しない場合(self, mock_scenarios):
        """存在しないシナリオIDでNotFoundError"""
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios):
            with pytest.raises(NotFoundError) as exc_info:
                ScenarioService.get_scenario('non_existent')
            
            assert "シナリオ" in str(exc_info.value)
            assert "non_existent" in str(exc_info.value)
    
    def test_clear_scenario_history_特定シナリオ(self):
        """特定シナリオの履歴クリア"""
        with patch('services.scenario_service.SessionService') as mock_session:
            result = ScenarioService.clear_scenario_history('scenario_001')
            
            mock_session.clear_session_history.assert_called_once_with('scenario_history', 'scenario_001')
            assert result['message'] == 'シナリオ scenario_001 の履歴をクリアしました'
    
    def test_get_initial_message_存在する場合(self, mock_scenarios):
        """初期メッセージの取得"""
        mock_scenarios['scenario_001']['initial_message'] = 'それでは始めましょう'
        
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios):
            message = ScenarioService.get_initial_message('scenario_001')
            assert message == 'それでは始めましょう'
    
    def test_get_initial_message_存在しない場合(self, mock_scenarios):
        """初期メッセージがない場合はNone"""
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios):
            message = ScenarioService.get_initial_message('scenario_001')
            assert message is None
    
    def test_handle_scenario_message_正常系(self, mock_scenarios):
        """シナリオメッセージの正常処理"""
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios), \
             patch('services.scenario_service.LLMService') as mock_llm, \
             patch('services.scenario_service.SessionService') as mock_session, \
             patch('services.scenario_service.SecurityUtils') as mock_security:
            
            # モックの設定
            mock_security.sanitize_input.side_effect = lambda x: x
            mock_session.get_session_data.return_value = 'gemini-1.5-flash'
            mock_session.get_session_history.return_value = []
            
            # LLMのストリーミングレスポンスをモック
            mock_chunk = MagicMock()
            mock_chunk.content = '了解しました'
            mock_chain = MagicMock()
            mock_chain.stream.return_value = [mock_chunk]
            
            mock_llm.create_llm.return_value = MagicMock()
            with patch('services.scenario_service.ChatPromptTemplate'):
                with patch('services.scenario_service.RunnableWithMessageHistory', return_value=mock_chain):
                    # generatorを実行
                    responses = list(ScenarioService.handle_scenario_message('scenario_001', 'テストメッセージ'))
                    
                    assert len(responses) >= 2  # コンテンツと完了メッセージ
                    assert '了解しました' in responses[0]
    
    def test_handle_scenario_message_空メッセージエラー(self):
        """空メッセージでValidationError"""
        with pytest.raises(ValidationError, match="メッセージを入力してください"):
            list(ScenarioService.handle_scenario_message('scenario_001', ''))
    
    def test_handle_scenario_message_シナリオ不在エラー(self):
        """存在しないシナリオでNotFoundError"""
        with patch('services.scenario_service.load_scenarios', return_value={}):
            with pytest.raises(NotFoundError):
                list(ScenarioService.handle_scenario_message('non_existent', 'test'))
    
    def test_generate_scenario_feedback_正常系(self, mock_scenarios):
        """フィードバック生成の正常系"""
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios), \
             patch('services.scenario_service.SessionService') as mock_session, \
             patch('services.scenario_service.LLMService') as mock_llm:
            
            # 履歴の設定
            history = [{'user': 'テスト', 'character': '応答'}]
            mock_session.get_session_history.return_value = history
            
            # LLM応答の設定
            mock_llm.try_multiple_models_for_prompt.return_value = ('素晴らしいです', 'gemini-1.5-flash', None)
            
            result = ScenarioService.generate_scenario_feedback('scenario_001')
            
            assert result['feedback'] == '素晴らしいです'
            assert result['scenario_id'] == 'scenario_001'
            assert result['conversation_count'] == 1
            assert result['model'] == 'gemini-1.5-flash'
    
    def test_generate_scenario_feedback_履歴なし(self, mock_scenarios):
        """履歴がない場合のフィードバック"""
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios), \
             patch('services.scenario_service.SessionService') as mock_session:
            
            mock_session.get_session_history.return_value = []
            
            result = ScenarioService.generate_scenario_feedback('scenario_001')
            
            assert 'まだ会話履歴がありません' in result['feedback']
            assert result['conversation_count'] == 0
    
    def test_generate_scenario_feedback_エラー処理(self, mock_scenarios):
        """フィードバック生成エラー時の処理"""
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios), \
             patch('services.scenario_service.SessionService') as mock_session, \
             patch('services.scenario_service.LLMService') as mock_llm:
            
            mock_session.get_session_history.return_value = [{'user': 'test'}]
            mock_llm.try_multiple_models_for_prompt.side_effect = Exception("生成エラー")
            
            result = ScenarioService.generate_scenario_feedback('scenario_001')
            
            assert 'フィードバックの生成中にエラーが発生しました' in result['feedback']
            assert 'error' in result
    
    def test_handle_scenario_message_履歴保存(self, mock_scenarios):
        """会話履歴が正しく保存される"""
        with patch('services.scenario_service.load_scenarios', return_value=mock_scenarios), \
             patch('services.scenario_service.LLMService') as mock_llm, \
             patch('services.scenario_service.SessionService') as mock_session, \
             patch('services.scenario_service.SecurityUtils') as mock_security:
            
            # モックの設定
            mock_security.sanitize_input.side_effect = lambda x: x
            mock_session.get_session_data.return_value = 'gemini-1.5-flash'
            mock_session.get_session_history.return_value = []
            
            # LLMのストリーミングレスポンスをモック
            mock_chunk = MagicMock()
            mock_chunk.content = '承知しました'
            mock_chain = MagicMock()
            mock_chain.stream.return_value = [mock_chunk]
            
            mock_llm.create_llm.return_value = MagicMock()
            with patch('services.scenario_service.ChatPromptTemplate'):
                with patch('services.scenario_service.RunnableWithMessageHistory', return_value=mock_chain):
                    # generatorを実行
                    list(ScenarioService.handle_scenario_message('scenario_001', 'ユーザーメッセージ'))
                    
                    # 履歴への追加を確認
                    mock_session.add_to_session_history.assert_called()
                    call_args = mock_session.add_to_session_history.call_args[0]
                    
                    assert call_args[0] == 'scenario_history'
                    assert call_args[1]['user'] == 'ユーザーメッセージ'
                    assert call_args[1]['character'] == '承知しました'
                    assert call_args[2] == 'scenario_001'  # sub_key