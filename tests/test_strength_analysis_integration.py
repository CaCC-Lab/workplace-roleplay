"""
強み分析機能の統合テスト（簡略版）

Celeryタスクのモックを最小限にして、実際の処理フローをテスト
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from strength_analyzer import (
    create_strength_analysis_prompt,
    parse_strength_analysis,
    get_top_strengths,
    generate_encouragement_messages
)


class TestStrengthAnalysisIntegration:
    """強み分析機能の統合テスト"""
    
    def test_エンドツーエンドフロー(self):
        """プロンプト作成から結果取得までの統合テスト"""
        # 1. 会話履歴を準備
        conversation_history = [
            {"role": "user", "content": "新しいプロジェクトのリーダーになりました。"},
            {"role": "assistant", "content": "リーダーに就任されたんですね！"},
            {"role": "user", "content": "チームメンバーの意見をうまく引き出せるようになりたいです。"}
        ]
        
        # 2. プロンプトを作成
        prompt = create_strength_analysis_prompt(conversation_history)
        assert "ユーザー: 新しいプロジェクトのリーダーになりました。" in prompt
        assert "AI: リーダーに就任されたんですね！" in prompt
        
        # 3. LLMレスポンスをシミュレート
        llm_response = json.dumps({
            "empathy": 72,
            "clarity": 85,
            "active_listening": 78,
            "adaptability": 70,
            "positivity": 75,
            "professionalism": 88
        })
        
        # 4. レスポンスをパース
        scores = parse_strength_analysis(llm_response)
        assert scores["clarity"] == 85
        assert scores["professionalism"] == 88
        
        # 5. トップ3の強みを取得
        top_strengths = get_top_strengths(scores, 3)
        assert len(top_strengths) == 3
        assert top_strengths[0]["score"] == 88  # professionalism
        assert top_strengths[1]["score"] == 85  # clarity
        assert top_strengths[2]["score"] == 78  # active_listening
        
        # 6. 励ましメッセージを生成
        messages = generate_encouragement_messages(scores, [])
        assert len(messages) > 0
        assert any("プロフェッショナリズム" in msg for msg in messages)
    
    def test_エラーケースのハンドリング(self):
        """エラーケースでの適切な処理を確認"""
        # 不正なLLMレスポンス
        invalid_response = "これはJSONではありません"
        scores = parse_strength_analysis(invalid_response)
        
        # デフォルト値が返される
        assert all(score == 50 for score in scores.values())
        
        # それでも処理は継続できる
        top_strengths = get_top_strengths(scores, 3)
        assert len(top_strengths) == 3
        
        messages = generate_encouragement_messages(scores, [])
        assert len(messages) > 0
    
    @patch('langchain_google_genai.ChatGoogleGenerativeAI')
    def test_LLM呼び出しのモック(self, mock_llm_class):
        """LLM呼び出しを含む処理のテスト"""
        # LLMインスタンスのモック
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content=json.dumps({
            "empathy": 80,
            "clarity": 75,
            "active_listening": 82,
            "adaptability": 70,
            "positivity": 78,
            "professionalism": 85
        }))
        mock_llm_class.return_value = mock_llm
        
        # プロンプトを作成
        conversation_history = [{"role": "user", "content": "テスト"}]
        prompt = create_strength_analysis_prompt(conversation_history)
        
        # LLMを呼び出し（実際のタスクの一部をシミュレート）
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content="あなたは職場コミュニケーションの専門家です。"),
            HumanMessage(content=prompt)
        ]
        
        response = mock_llm.invoke(messages)
        analysis_text = response.content
        
        # 結果をパース
        scores = parse_strength_analysis(analysis_text)
        assert scores["empathy"] == 80
        assert scores["professionalism"] == 85