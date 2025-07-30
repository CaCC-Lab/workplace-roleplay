"""
最小限のヒントサービスのテスト
"""
import pytest
from services.minimal_hint_service import MinimalHintService


class TestMinimalHintService:
    """MinimalHintServiceのテストクラス"""
    
    @pytest.fixture
    def hint_service(self):
        """テスト用のヒントサービスインスタンス"""
        return MinimalHintService()
    
    @pytest.fixture
    def sample_scenario(self):
        """サンプルシナリオデータ"""
        return {
            "id": "scenario1",
            "title": "上司への報告",
            "description": "プロジェクトの進捗を上司に報告する",
            "learning_points": [
                "明確な情報伝達",
                "課題の整理",
                "解決策の提示"
            ],
            "alternative_approaches": [
                {
                    "example": "具体的な数値を含めて報告する",
                    "benefit": "進捗が明確に伝わる",
                    "practice_point": "定量的な表現を使う"
                },
                {
                    "example": "課題と対策をセットで伝える",
                    "benefit": "前向きな印象を与える",
                    "practice_point": "建設的な姿勢を示す"
                }
            ],
            "feedback_points": {
                "good_points": [
                    "相手の立場を考える",
                    "簡潔に要点を伝える"
                ]
            }
        }
    
    @pytest.fixture
    def sample_conversation(self):
        """サンプル会話履歴"""
        return [
            {"role": "assistant", "content": "プロジェクトの進捗はどうですか？"},
            {"role": "user", "content": "えっと..."}
        ]
    
    def test_service_initialization(self, hint_service):
        """サービスの初期化テスト"""
        assert hint_service is not None
        assert hasattr(hint_service, 'hint_templates')
        assert isinstance(hint_service.hint_templates, dict)
    
    def test_generate_hint_first_level(self, hint_service, sample_scenario, sample_conversation):
        """1回目のヒント生成テスト（優しいレベル）"""
        hint = hint_service.generate_hint(
            scenario_id="scenario1",
            scenario_data=sample_scenario,
            conversation_history=sample_conversation,
            hint_number=1
        )
        
        assert isinstance(hint, dict)
        assert 'type' in hint
        assert 'message' in hint
        assert hint['message'] != ""
        assert len(hint['message']) > 10
    
    def test_generate_hint_second_level(self, hint_service, sample_scenario, sample_conversation):
        """2回目のヒント生成テスト（中程度レベル）"""
        hint = hint_service.generate_hint(
            scenario_id="scenario1",
            scenario_data=sample_scenario,
            conversation_history=sample_conversation,
            hint_number=2
        )
        
        assert isinstance(hint, dict)
        assert 'type' in hint
        assert 'message' in hint
        # 2回目のヒントはより具体的
        assert 'example' in hint or 'considerationPoints' in hint
    
    def test_generate_hint_third_level(self, hint_service, sample_scenario, sample_conversation):
        """3回目のヒント生成テスト（具体的レベル）"""
        hint = hint_service.generate_hint(
            scenario_id="scenario1",
            scenario_data=sample_scenario,
            conversation_history=sample_conversation,
            hint_number=3
        )
        
        assert isinstance(hint, dict)
        assert 'type' in hint
        assert 'message' in hint
        # 3回目のヒントは最も具体的
        assert 'considerationPoints' in hint
        assert len(hint['considerationPoints']) > 0
    
    def test_conversation_state_analysis(self, hint_service, sample_scenario):
        """会話状態分析のテスト"""
        # 初期状態
        empty_conversation = []
        state = hint_service._analyze_conversation_state(
            empty_conversation,
            sample_scenario
        )
        assert state['stage'] == 'initial'
        assert state['user_message_count'] == 0
        
        # 会話が進んだ状態
        advanced_conversation = [
            {"role": "assistant", "content": "進捗はどうですか？"},
            {"role": "user", "content": "順調です"},
            {"role": "assistant", "content": "課題はありますか？"},
            {"role": "user", "content": "少し遅れています"}
        ]
        state = hint_service._analyze_conversation_state(
            advanced_conversation,
            sample_scenario
        )
        assert state['stage'] == 'middle'  # 2つのユーザーメッセージは'middle'
        assert state['user_message_count'] == 2
    
    def test_difficulty_point_inference(self, hint_service, sample_scenario):
        """困難ポイント推測のテスト"""
        # 短い返答
        short_messages = [{"role": "user", "content": "はい"}]
        difficulty = hint_service._infer_difficulty_point(
            short_messages,
            "質問への返答",
            sample_scenario
        )
        assert difficulty == 'finding_words'
        
        # 謝罪が多い
        apologetic_messages = [{"role": "user", "content": "すみません、申し訳ございません"}]
        difficulty = hint_service._infer_difficulty_point(
            apologetic_messages,
            "指摘への対応",
            sample_scenario
        )
        assert difficulty == 'over_apologizing'
        
        # 質問で返す
        question_messages = [{"role": "user", "content": "それはどういう意味ですか？"}]
        difficulty = hint_service._infer_difficulty_point(
            question_messages,
            "説明への反応",
            sample_scenario
        )
        assert difficulty == 'questioning_back'
    
    def test_fallback_hint(self, hint_service):
        """フォールバックヒントのテスト"""
        hint = hint_service._create_fallback_hint()
        
        assert isinstance(hint, dict)
        assert hint['type'] == 'general'
        assert 'message' in hint
        assert 'considerationPoints' in hint
        assert len(hint['considerationPoints']) > 0
    
    def test_scenario_specific_points(self, hint_service, sample_scenario):
        """シナリオ固有ポイント取得のテスト"""
        points = hint_service._get_scenario_specific_points(sample_scenario)
        
        assert isinstance(points, list)
        assert len(points) > 0
        assert len(points) <= 3  # 最大3つまで
        
        # 代替アプローチから抽出されているか確認
        assert any("定量的" in point for point in points)
    
    def test_empty_conversation_handling(self, hint_service, sample_scenario):
        """空の会話履歴の処理テスト"""
        hint = hint_service.generate_hint(
            scenario_id="scenario1",
            scenario_data=sample_scenario,
            conversation_history=[],
            hint_number=1
        )
        
        assert isinstance(hint, dict)
        assert 'message' in hint
        assert hint['message'] != ""
    
    def test_hint_level_determination(self, hint_service):
        """ヒントレベル決定のテスト"""
        assert hint_service._determine_hint_level(1) == 'gentle'
        assert hint_service._determine_hint_level(2) == 'moderate'
        assert hint_service._determine_hint_level(3) == 'specific'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])