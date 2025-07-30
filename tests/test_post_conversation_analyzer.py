"""
PostConversationAnalyzerサービスのユニットテスト
"""
import pytest
from datetime import datetime
from services.post_conversation_analyzer import PostConversationAnalyzer, ConversationAnalysis


class TestPostConversationAnalyzer:
    """PostConversationAnalyzerのテストクラス"""
    
    @pytest.fixture
    def analyzer(self):
        """テスト用のアナライザインスタンス"""
        return PostConversationAnalyzer()
    
    @pytest.fixture
    def sample_conversation(self):
        """サンプル会話履歴"""
        return [
            {"role": "assistant", "content": "お疲れ様です。何かお手伝いできることはありますか？"},
            {"role": "user", "content": "実は、この案件の進め方で少し迷っていて..."},
            {"role": "assistant", "content": "どのような点で迷われているか、詳しく教えていただけますか？"},
            {"role": "user", "content": "スケジュールが厳しくて、品質を保てるか心配なんです。"},
            {"role": "assistant", "content": "なるほど、品質とスケジュールのバランスは難しいですよね。優先順位を整理してみましょうか？"},
            {"role": "user", "content": "そうですね、まず重要な機能から着手したいと思います。"}
        ]
    
    @pytest.fixture
    def sample_scenario(self):
        """サンプルシナリオデータ"""
        return {
            "id": "test_scenario",
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
                }
            ]
        }
    
    def test_analyzer_initialization(self, analyzer):
        """アナライザの初期化テスト"""
        assert analyzer is not None
        assert hasattr(analyzer, 'analysis_prompts')
        assert isinstance(analyzer.analysis_prompts, dict)
    
    def test_analyze_conversation_basic(self, analyzer, sample_conversation, sample_scenario):
        """基本的な会話分析のテスト"""
        result = analyzer.analyze_conversation(
            conversation_history=sample_conversation,
            scenario_data=sample_scenario
        )
        
        assert isinstance(result, ConversationAnalysis)
        assert result.scenario_id == "test_scenario"
        assert isinstance(result.analyzed_at, datetime)
        assert isinstance(result.communication_patterns, dict)
        assert isinstance(result.emotional_transitions, list)
        assert isinstance(result.key_moments, list)
        assert isinstance(result.alternative_responses, list)
        assert isinstance(result.consultant_insights, dict)
        assert isinstance(result.growth_points, list)
        assert isinstance(result.strengths_demonstrated, list)
        assert isinstance(result.areas_for_improvement, list)
    
    def test_communication_patterns_analysis(self, analyzer, sample_conversation):
        """コミュニケーションパターン分析のテスト"""
        patterns = analyzer._analyze_communication_patterns(sample_conversation)
        
        assert 'response_style' in patterns
        assert 'assertiveness_level' in patterns
        assert 'empathy_indicators' in patterns
        assert 'clarity_score' in patterns
        assert 'professionalism_score' in patterns
        
        assert patterns['response_style'] in ["簡潔型", "標準型", "詳細型"]
        assert 0 <= patterns['assertiveness_level'] <= 1
        assert isinstance(patterns['empathy_indicators'], list)
        assert 0 <= patterns['clarity_score'] <= 1
        assert 0 <= patterns['professionalism_score'] <= 1
    
    def test_emotional_transitions_analysis(self, analyzer, sample_conversation):
        """感情推移分析のテスト"""
        transitions = analyzer._analyze_emotional_transitions(sample_conversation)
        
        assert isinstance(transitions, list)
        assert len(transitions) == 3  # ユーザーの発言数
        
        for transition in transitions:
            assert 'turn' in transition
            assert 'detected_emotion' in transition
            assert 'confidence' in transition
            assert 'content_excerpt' in transition
    
    def test_emotional_transitions_with_user_emotions(self, analyzer, sample_conversation):
        """ユーザー提供の感情を含む感情推移分析のテスト"""
        user_emotions = [
            {"emotion": "不安", "timestamp": "2024-01-01T10:00:00"},
            {"emotion": "困惑", "timestamp": "2024-01-01T10:01:00"},
            {"emotion": "安心", "timestamp": "2024-01-01T10:02:00"}
        ]
        
        transitions = analyzer._analyze_emotional_transitions(
            sample_conversation,
            user_emotions
        )
        
        assert transitions[0].get('user_reported') == user_emotions[0]
        assert transitions[1].get('user_reported') == user_emotions[1]
        assert transitions[2].get('user_reported') == user_emotions[2]
    
    def test_key_moments_identification(self, analyzer, sample_conversation, sample_scenario):
        """重要な瞬間の特定テスト"""
        key_moments = analyzer._identify_key_moments(
            sample_conversation,
            sample_scenario
        )
        
        assert isinstance(key_moments, list)
        for moment in key_moments:
            assert 'turn' in moment
            assert 'type' in moment
            assert 'content' in moment
            assert 'relevance_score' in moment
            assert 'related_learning_point' in moment
    
    def test_alternative_responses_generation(self, analyzer, sample_conversation, sample_scenario):
        """代替対応案生成のテスト"""
        alternatives = analyzer._generate_alternative_responses(
            sample_conversation,
            sample_scenario
        )
        
        assert isinstance(alternatives, list)
        assert len(alternatives) <= 3  # 最大3つの応答に対して
        
        for alt in alternatives:
            assert 'original_response' in alt
            assert 'alternatives' in alt
            assert 'turn' in alt
            assert isinstance(alt['alternatives'], list)
    
    def test_consultant_insights_generation(self, analyzer, sample_conversation, sample_scenario):
        """キャリアコンサルタント視点の洞察生成テスト"""
        patterns = analyzer._analyze_communication_patterns(sample_conversation)
        insights = analyzer._generate_consultant_insights(
            sample_conversation,
            sample_scenario,
            patterns
        )
        
        assert 'overall_assessment' in insights
        assert 'communication_style' in insights
        assert 'hidden_strengths' in insights
        assert 'growth_opportunities' in insights
        assert 'action_recommendations' in insights
        
        for key, value in insights.items():
            assert isinstance(value, str)
            assert len(value) > 0
    
    def test_growth_points_analysis(self, analyzer, sample_conversation, sample_scenario):
        """成長ポイント分析のテスト"""
        growth_analysis = analyzer._analyze_growth_points(
            sample_conversation,
            sample_scenario
        )
        
        assert 'growth_points' in growth_analysis
        assert 'strengths' in growth_analysis
        assert 'improvements' in growth_analysis
        
        assert isinstance(growth_analysis['growth_points'], list)
        assert isinstance(growth_analysis['strengths'], list)
        assert isinstance(growth_analysis['improvements'], list)
        
        assert len(growth_analysis['growth_points']) > 0
        assert len(growth_analysis['strengths']) > 0
        assert len(growth_analysis['improvements']) > 0
    
    def test_empty_conversation_handling(self, analyzer, sample_scenario):
        """空の会話履歴の処理テスト"""
        with pytest.raises(Exception):
            analyzer.analyze_conversation(
                conversation_history=[],
                scenario_data=sample_scenario
            )
    
    def test_emotion_detection(self, analyzer):
        """感情検出のテスト"""
        test_cases = [
            ("申し訳ございません", "apologetic"),
            ("ありがとうございます", "positive"),
            ("困っています", "anxious"),
            ("通常の文章です", "neutral")
        ]
        
        for text, expected_emotion in test_cases:
            detected = analyzer._detect_emotion(text)
            assert detected == expected_emotion
    
    def test_response_style_classification(self, analyzer):
        """応答スタイル分類のテスト"""
        # 簡潔な応答
        short_conversation = [
            {"role": "user", "content": "はい"},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "分かりました"}
        ]
        assert analyzer._classify_response_style(short_conversation) == "簡潔型"
        
        # 標準的な応答
        medium_conversation = [
            {"role": "user", "content": "承知しました。確認してみます。"},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "そのように対応させていただきます。"}
        ]
        assert analyzer._classify_response_style(medium_conversation) == "標準型"
        
        # 詳細な応答
        long_conversation = [
            {"role": "user", "content": "この件について詳しく説明させていただきますと、まず第一に考慮すべき点として..."},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "さらに付け加えさせていただきますと、この問題の背景には複数の要因が絡んでおりまして..."}
        ]
        assert analyzer._classify_response_style(long_conversation) == "詳細型"
    
    def test_empathy_indicators_finding(self, analyzer):
        """共感指標の検出テスト"""
        conversation = [
            {"role": "user", "content": "なるほど、そういうことだったんですね。"},
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "お気持ちはよく分かります。"}
        ]
        
        indicators = analyzer._find_empathy_indicators(conversation)
        assert "なるほど" in indicators
        assert "お気持ち" in indicators
        assert "分かります" in indicators


if __name__ == "__main__":
    pytest.main([__file__, "-v"])