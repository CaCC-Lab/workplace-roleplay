"""
PromptServiceのユニットテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.prompt_service import PromptService, get_prompt_service


class TestPromptService:
    """PromptServiceのテストクラス"""
    
    @pytest.fixture
    def prompt_service(self):
        return PromptService()


class TestBuildScenarioSystemPrompt:
    """build_scenario_system_promptメソッドのテスト"""
    
    @pytest.fixture
    def sample_scenario(self):
        return {
            "title": "進捗報告シナリオ",
            "character": {
                "name": "田中課長",
                "role": "上司",
                "personality": "厳格だが公平な上司で、部下の成長を見守っている。"
            },
            "situation": "週次の進捗報告会議で、遅延しているプロジェクトについて報告する場面。",
            "instructions": "建設的なフィードバックを心がけてください。"
        }
    
    def test_returns_string(self, sample_scenario):
        """文字列が返されることをテスト"""
        result = PromptService.build_scenario_system_prompt(sample_scenario)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_contains_character_name(self, sample_scenario):
        """キャラクター名が含まれることをテスト"""
        result = PromptService.build_scenario_system_prompt(sample_scenario)
        assert "田中課長" in result
    
    def test_contains_character_role(self, sample_scenario):
        """キャラクターの役割が含まれることをテスト"""
        result = PromptService.build_scenario_system_prompt(sample_scenario)
        assert "上司" in result
    
    def test_contains_situation(self, sample_scenario):
        """状況が含まれることをテスト"""
        result = PromptService.build_scenario_system_prompt(sample_scenario)
        assert "週次の進捗報告会議" in result
    
    def test_handles_empty_scenario(self):
        """空のシナリオでのテスト"""
        result = PromptService.build_scenario_system_prompt({})
        assert isinstance(result, str)


class TestBuildWatchModePrompt:
    """build_watch_mode_promptメソッドのテスト"""
    
    def test_returns_string(self):
        """文字列が返されることをテスト"""
        result = PromptService.build_watch_mode_prompt("天気")
        assert isinstance(result, str)
    
    def test_contains_topic(self):
        """トピックが含まれることをテスト"""
        result = PromptService.build_watch_mode_prompt("週末の予定")
        assert "週末の予定" in result
    
    def test_initiator_prompt(self):
        """開始者用プロンプトのテスト"""
        result = PromptService.build_watch_mode_prompt("天気", is_initiator=True)
        assert "話題を始めて" in result
    
    def test_responder_prompt(self):
        """応答者用プロンプトのテスト"""
        result = PromptService.build_watch_mode_prompt("天気", is_initiator=False)
        assert "自然に返答" in result


class TestBuildChatFeedbackPrompt:
    """build_chat_feedback_promptメソッドのテスト"""
    
    def test_returns_string(self):
        """文字列が返されることをテスト"""
        result = PromptService.build_chat_feedback_prompt("あなた: こんにちは\n相手: こんにちは！")
        assert isinstance(result, str)
    
    def test_contains_conversation(self):
        """会話内容が含まれることをテスト"""
        conversation = "あなた: 今日は暑いですね\n相手: 本当ですね、熱中症に気をつけましょう"
        result = PromptService.build_chat_feedback_prompt(conversation)
        assert "今日は暑いですね" in result
    
    def test_contains_evaluation_criteria(self):
        """評価基準が含まれることをテスト"""
        result = PromptService.build_chat_feedback_prompt("会話内容")
        assert "話題の選び方" in result
        assert "相手への配慮" in result


class TestBuildScenarioFeedbackPrompt:
    """build_scenario_feedback_promptメソッドのテスト"""
    
    @pytest.fixture
    def sample_scenario(self):
        return {
            "title": "報告シナリオ",
            "situation": "進捗報告の場面",
            "your_role": "部下",
            "feedback_points": ["報告の明確さ", "課題の伝え方"]
        }
    
    def test_returns_string(self, sample_scenario):
        """文字列が返されることをテスト"""
        result = PromptService.build_scenario_feedback_prompt(
            sample_scenario,
            "あなた: 報告があります\n上司: はい、どうぞ"
        )
        assert isinstance(result, str)
    
    def test_contains_scenario_title(self, sample_scenario):
        """シナリオタイトルが含まれることをテスト"""
        result = PromptService.build_scenario_feedback_prompt(sample_scenario, "会話")
        assert "報告シナリオ" in result
    
    def test_contains_feedback_points(self, sample_scenario):
        """フィードバックポイントが含まれることをテスト"""
        result = PromptService.build_scenario_feedback_prompt(sample_scenario, "会話")
        assert "報告の明確さ" in result
        assert "課題の伝え方" in result


class TestFormatConversationForFeedback:
    """format_conversation_for_feedbackメソッドのテスト"""
    
    def test_formats_history(self):
        """履歴が正しくフォーマットされることをテスト"""
        history = [
            {"human": "こんにちは", "ai": "こんにちは！"},
            {"human": "お元気ですか？", "ai": "はい、元気です！"}
        ]
        result = PromptService.format_conversation_for_feedback(history)
        
        assert "あなた: こんにちは" in result
        assert "相手: こんにちは！" in result
    
    def test_custom_ai_name(self):
        """カスタムAI名のテスト"""
        history = [{"human": "テスト", "ai": "応答"}]
        result = PromptService.format_conversation_for_feedback(history, ai_name="田中課長")
        
        assert "田中課長: 応答" in result
    
    def test_handles_empty_history(self):
        """空の履歴でのテスト"""
        result = PromptService.format_conversation_for_feedback([])
        assert result == ""


class TestGetPromptService:
    """get_prompt_service関数のテスト"""
    
    def test_returns_instance(self):
        """インスタンスが返されることをテスト"""
        import services.prompt_service as module
        module._prompt_service = None
        
        service = get_prompt_service()
        assert isinstance(service, PromptService)
    
    def test_singleton(self):
        """シングルトンパターンのテスト"""
        import services.prompt_service as module
        module._prompt_service = None
        
        service1 = get_prompt_service()
        service2 = get_prompt_service()
        assert service1 is service2
