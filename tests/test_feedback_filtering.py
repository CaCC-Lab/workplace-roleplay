"""
フィードバックフィルタリングのテスト
ユーザーメッセージのみが評価されることを確認
"""
import pytest
from unittest.mock import Mock, patch
from services.conversation_service import ConversationService
from services.scenario_service import ScenarioService
from tasks.llm import _create_scenario_feedback_prompt, _create_chat_feedback_prompt


class TestFeedbackFiltering:
    """フィードバックがユーザーメッセージのみを評価することを確認するテスト"""
    
    @pytest.fixture
    def sample_conversation_history(self):
        """テスト用の会話履歴（ユーザーとAIの混合）"""
        return [
            {"role": "user", "content": "おはようございます！今日はいい天気ですね。"},
            {"role": "assistant", "content": "おはようございます！本当にいい天気ですね。朝から気持ちがいいです。"},
            {"role": "user", "content": "最近、仕事が忙しくて大変です。"},
            {"role": "assistant", "content": "お疲れ様です。忙しい時期は体調管理も大切ですよ。"},
            {"role": "user", "content": "そうですね。週末はゆっくり休もうと思います。"},
            {"role": "assistant", "content": "それがいいですね。リフレッシュは大切です。"}
        ]
    
    @pytest.fixture
    def sample_scenario(self):
        """テスト用のシナリオデータ"""
        return {
            'title': '同僚との朝の挨拶',
            'description': '朝、オフィスで同僚と会った際の雑談',
            'situation': 'オフィスの給湯室',
            'difficulty': '初級',
            'learning_points': ['適切な挨拶', '相手への配慮', '話題選び'],
            'feedback_points': ['挨拶の自然さ', '話題の適切さ', '相手への共感']
        }
    
    def test_conversation_service_filters_user_messages_only(self, sample_conversation_history):
        """ConversationServiceがユーザーメッセージのみをフィルタリングすることを確認"""
        service = ConversationService()
        result = service.format_user_messages_only(sample_conversation_history)
        
        # ユーザーメッセージが含まれていることを確認
        assert "おはようございます！今日はいい天気ですね。" in result
        assert "最近、仕事が忙しくて大変です。" in result
        assert "そうですね。週末はゆっくり休もうと思います。" in result
        
        # AIメッセージが含まれていないことを確認
        assert "本当にいい天気ですね。朝から気持ちがいいです。" not in result
        assert "お疲れ様です。忙しい時期は体調管理も大切ですよ。" not in result
        assert "それがいいですね。リフレッシュは大切です。" not in result
        
        # 正しい番号付けがされていることを確認
        assert "[1] ユーザー:" in result
        assert "[2] ユーザー:" in result
        assert "[3] ユーザー:" in result
    
    def test_scenario_service_filters_user_messages_only(self, sample_conversation_history):
        """ScenarioServiceがユーザーメッセージのみをフィルタリングすることを確認"""
        service = ScenarioService()
        result = service._format_user_messages_only(sample_conversation_history)
        
        # ユーザーメッセージが含まれていることを確認
        assert "おはようございます！今日はいい天気ですね。" in result
        assert "最近、仕事が忙しくて大変です。" in result
        assert "そうですね。週末はゆっくり休もうと思います。" in result
        
        # AIメッセージが含まれていないことを確認
        assert "本当にいい天気ですね。朝から気持ちがいいです。" not in result
        assert "お疲れ様です。忙しい時期は体調管理も大切ですよ。" not in result
        assert "それがいいですね。リフレッシュは大切です。" not in result
    
    def test_empty_conversation_history(self):
        """空の会話履歴の処理を確認"""
        conv_service = ConversationService()
        scenario_service = ScenarioService()
        
        result_conv = conv_service.format_user_messages_only([])
        result_scenario = scenario_service._format_user_messages_only([])
        
        assert result_conv == "（ユーザーの発言なし）"
        assert result_scenario == "（ユーザーの発言なし）"
    
    def test_only_ai_messages_history(self):
        """AIメッセージのみの会話履歴の処理を確認"""
        ai_only_history = [
            {"role": "assistant", "content": "こんにちは！"},
            {"role": "assistant", "content": "何かお手伝いできることはありますか？"}
        ]
        
        conv_service = ConversationService()
        scenario_service = ScenarioService()
        
        result_conv = conv_service.format_user_messages_only(ai_only_history)
        result_scenario = scenario_service._format_user_messages_only(ai_only_history)
        
        assert result_conv == "（ユーザーの発言なし）"
        assert result_scenario == "（ユーザーの発言なし）"
    
    def test_scenario_feedback_prompt_creation(self, sample_conversation_history, sample_scenario):
        """シナリオフィードバックプロンプトがユーザーメッセージのみを含むことを確認"""
        prompt = _create_scenario_feedback_prompt(sample_conversation_history, sample_scenario)
        
        # プロンプトにユーザーメッセージが含まれていることを確認
        assert "ユーザーの発言:" in prompt
        assert "おはようございます！今日はいい天気ですね。" in prompt
        
        # AIメッセージが含まれていないことを確認
        assert "本当にいい天気ですね。朝から気持ちがいいです。" not in prompt
        assert "お疲れ様です。" not in prompt
        
        # シナリオ情報が含まれていることを確認
        assert sample_scenario['title'] in prompt
        assert sample_scenario['description'] in prompt
    
    def test_chat_feedback_prompt_creation(self, sample_conversation_history):
        """雑談フィードバックプロンプトがユーザーメッセージのみを含むことを確認"""
        prompt = _create_chat_feedback_prompt(sample_conversation_history)
        
        # プロンプトにユーザーメッセージが含まれていることを確認
        assert "ユーザーの発言:" in prompt
        assert "おはようございます！今日はいい天気ですね。" in prompt
        
        # AIメッセージが含まれていないことを確認
        assert "本当にいい天気ですね。朝から気持ちがいいです。" not in prompt
        assert "お疲れ様です。" not in prompt
    
    @patch('services.conversation_service.ConversationService.format_user_messages_only')
    def test_generate_chat_feedback_uses_filtered_messages(self, mock_format, sample_conversation_history):
        """generate_chat_feedbackがフィルタリングされたメッセージを使用することを確認"""
        mock_format.return_value = "[1] ユーザー: テストメッセージ"
        
        service = ConversationService()
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = "テストフィードバック"
        
        service.generate_chat_feedback(
            mock_llm,
            sample_conversation_history,
            {'partner_type': '同僚', 'situation': '朝の挨拶', 'topic': '天気'}
        )
        
        # format_user_messages_onlyが呼ばれたことを確認
        mock_format.assert_called_once_with(sample_conversation_history)
    
    @patch('services.scenario_service.ScenarioService._format_user_messages_only')
    def test_generate_scenario_feedback_uses_filtered_messages(self, mock_format, sample_conversation_history, sample_scenario):
        """generate_scenario_feedbackがフィルタリングされたメッセージを使用することを確認"""
        mock_format.return_value = "[1] ユーザー: テストメッセージ"
        
        service = ScenarioService()
        mock_llm = Mock()
        mock_llm.invoke.return_value.content = "テストフィードバック"
        
        service.generate_scenario_feedback(
            mock_llm,
            sample_scenario,
            sample_conversation_history
        )
        
        # _format_user_messages_onlyが呼ばれたことを確認
        mock_format.assert_called_once_with(sample_conversation_history)
    
    def test_mixed_role_types(self):
        """様々な役割タイプが混在する会話履歴の処理を確認"""
        mixed_history = [
            {"role": "system", "content": "システムメッセージ"},
            {"role": "user", "content": "ユーザーメッセージ1"},
            {"role": "assistant", "content": "AIメッセージ"},
            {"role": "user", "content": "ユーザーメッセージ2"},
            {"role": "system", "type": "feedback", "content": "フィードバック"},
            {"role": "user", "content": "ユーザーメッセージ3"},
            {"role": "unknown", "content": "不明なメッセージ"}
        ]
        
        conv_service = ConversationService()
        result = conv_service.format_user_messages_only(mixed_history)
        
        # ユーザーメッセージのみが含まれていることを確認
        assert "[1] ユーザー: ユーザーメッセージ1" in result
        assert "[2] ユーザー: ユーザーメッセージ2" in result
        assert "[3] ユーザー: ユーザーメッセージ3" in result
        
        # その他のメッセージが含まれていないことを確認
        assert "システムメッセージ" not in result
        assert "AIメッセージ" not in result
        assert "フィードバック" not in result
        assert "不明なメッセージ" not in result