"""
WatchServiceのユニットテスト
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import json

from services.watch_service import WatchService
from errors import ValidationError, ExternalAPIError


class TestWatchService:
    """WatchServiceのテストクラス"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """依存関係のモック"""
        with patch('services.watch_service.LLMService') as mock_llm_service, \
             patch('services.watch_service.SessionService') as mock_session_service:
            
            # LLMServiceのモック設定
            mock_llm = MagicMock()
            mock_llm_service.create_llm.return_value = mock_llm
            
            # SessionServiceのモック設定
            mock_session_service.get_session_data.return_value = 'gemini-1.5-flash'
            mock_session_service.get_session_history.return_value = []
            
            yield {
                'llm_service': mock_llm_service,
                'session_service': mock_session_service,
                'llm': mock_llm
            }
    
    def test_start_watch_mode_デフォルト設定(self, mock_dependencies):
        """デフォルト設定での観戦モード開始"""
        mock_response = MagicMock()
        mock_response.content = "こんにちは、今日の天気はどうですか？"
        mock_dependencies['llm'].invoke.return_value = mock_response
        
        result = WatchService.start_watch_mode()
        
        # デフォルト値の確認
        assert result['partner1_type'] == '同僚'
        assert result['partner2_type'] == '友人'
        assert result['topic'] == '日常'
        assert result['model'] == 'gemini-1.5-flash'
        assert result['first_message'] == "こんにちは、今日の天気はどうですか？"
        assert result['current_speaker'] == 'AI1'
        assert result['next_speaker'] == 'AI2'
    
    def test_start_watch_mode_カスタム設定(self, mock_dependencies):
        """カスタム設定での観戦モード開始"""
        mock_response = MagicMock()
        mock_response.content = "仕事の進捗はいかがですか？"
        mock_dependencies['llm'].invoke.return_value = mock_response
        
        result = WatchService.start_watch_mode(
            partner1_type='先輩',
            partner2_type='部下',
            topic='仕事',
            model_name='gemini-1.5-pro'
        )
        
        assert result['partner1_type'] == '先輩'
        assert result['partner2_type'] == '部下'
        assert result['topic'] == '仕事'
        assert result['model'] == 'gemini-1.5-pro'
        mock_dependencies['llm_service'].create_llm.assert_called_with('gemini-1.5-pro')
    
    def test_start_watch_mode_エラー処理(self, mock_dependencies):
        """観戦モード開始時のエラー処理"""
        mock_dependencies['llm'].invoke.side_effect = Exception("API error")
        
        with pytest.raises(ExternalAPIError, match="観戦モードの初期化に失敗しました"):
            WatchService.start_watch_mode()
    
    def test_generate_next_message_正常系(self, mock_dependencies):
        """次のメッセージ生成の正常系"""
        # セッションデータのモック
        config = {
            'partner1_type': '同僚',
            'partner2_type': '友人',
            'topic': '日常',
            'model': 'gemini-1.5-flash',
            'next_speaker': 'AI2'
        }
        history = [
            {'speaker': 'AI1', 'message': 'こんにちは', 'partner_type': '同僚'}
        ]
        
        mock_dependencies['session_service'].get_session_data.side_effect = lambda key, default=None: {
            'watch_config': config,
            'selected_model': 'gemini-1.5-flash'
        }.get(key, default)
        mock_dependencies['session_service'].get_session_history.return_value = history
        
        # LLM応答のモック
        mock_response = MagicMock()
        mock_response.content = "こんにちは！元気ですか？"
        mock_dependencies['llm'].invoke.return_value = mock_response
        
        result = WatchService.generate_next_message()
        
        assert result['speaker'] == 'AI2'
        assert result['partner_type'] == '友人'
        assert result['message'] == "こんにちは！元気ですか？"
        assert result['next_speaker'] == 'AI1'
    
    def test_generate_next_message_設定なしエラー(self, mock_dependencies):
        """観戦設定がない場合のエラー"""
        mock_dependencies['session_service'].get_session_data.return_value = None
        
        with pytest.raises(ValidationError, match="観戦モードが開始されていません"):
            WatchService.generate_next_message()
    
    def test_generate_next_message_会話終了(self, mock_dependencies):
        """20回を超えた場合の会話終了"""
        # 20個のメッセージを持つ履歴
        history = [{'speaker': f'AI{i%2+1}', 'message': f'msg{i}'} for i in range(20)]
        mock_dependencies['session_service'].get_session_history.return_value = history
        
        config = {'next_speaker': 'AI1', 'partner1_type': '同僚', 'partner2_type': '友人'}
        mock_dependencies['session_service'].get_session_data.return_value = config
        
        result = WatchService.generate_next_message()
        
        assert result['speaker'] == 'system'
        assert result['message'] == '会話が終了しました'
        assert result['finished'] is True
    
    def test_get_watch_summary_履歴なし(self, mock_dependencies):
        """履歴がない場合のサマリー"""
        mock_dependencies['session_service'].get_session_history.return_value = []
        
        result = WatchService.get_watch_summary()
        
        assert result['turn_count'] == 0
        assert result['summary'] == '会話履歴がありません'
    
    def test_get_watch_summary_履歴あり(self, mock_dependencies):
        """履歴がある場合のサマリー"""
        history = [
            {'speaker': 'AI1', 'partner_type': '同僚', 'message': 'こんにちは'},
            {'speaker': 'AI2', 'partner_type': '友人', 'message': 'こんにちは！'},
            {'speaker': 'AI1', 'partner_type': '同僚', 'message': '元気ですか？'}
        ]
        mock_dependencies['session_service'].get_session_history.return_value = history
        # configデータをモック
        mock_dependencies['session_service'].get_session_data.return_value = {
            'partner1_type': '同僚',
            'partner2_type': '友人',
            'topic': '日常'
        }
        
        result = WatchService.get_watch_summary()
        
        assert result['turn_count'] == 3
        assert result['partner1_type'] == '同僚'
        assert result['partner2_type'] == '友人'
        assert result['topic'] == '日常'
    
    def test_extract_message_content_各種形式(self):
        """様々な形式からのメッセージ抽出"""
        # contentプロパティを持つオブジェクト
        obj = MagicMock()
        obj.content = "test content"
        assert WatchService._extract_message_content(obj) == "test content"
        
        # 文字列
        assert WatchService._extract_message_content("plain string") == "plain string"
        
        # 辞書
        assert WatchService._extract_message_content({'content': 'dict content'}) == 'dict content'
        assert WatchService._extract_message_content({'text': 'dict text'}) == 'dict text'
        
        # その他
        assert WatchService._extract_message_content(12345) == "12345"
    
    def test_get_partner_types_定数(self):
        """パートナータイプの定数確認"""
        assert '同僚' in WatchService.PARTNER_TYPES
        assert '友人' in WatchService.PARTNER_TYPES
        assert '先輩' in WatchService.PARTNER_TYPES
        assert 'カウンセラー' in WatchService.PARTNER_TYPES
    
    def test_get_topics_定数(self):
        """話題の定数確認"""
        assert '仕事' in WatchService.TOPICS
        assert '趣味' in WatchService.TOPICS
        assert '日常' in WatchService.TOPICS
        assert '悩み' in WatchService.TOPICS