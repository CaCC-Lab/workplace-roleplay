"""
ユーザー強み分析機能のテスト
TDD原則に従い、テストファーストで実装を改善
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from strength_analyzer import (
    STRENGTH_CATEGORIES,
    ENCOURAGEMENT_PATTERNS,
    create_strength_analysis_prompt,
    parse_strength_analysis,
    get_top_strengths,
    calculate_score_improvement,
    generate_encouragement_messages,
    analyze_user_strengths,
    create_personalized_message_prompt
)


class TestStrengthAnalysisPrompt:
    """強み分析プロンプト生成のテスト"""
    
    def test_プロンプト作成に会話履歴が含まれる(self):
        """作成されたプロンプトに会話履歴が含まれることを確認"""
        conversation_history = [
            {"role": "user", "content": "テストメッセージ1"},
            {"role": "assistant", "content": "返答1"}
        ]
        
        prompt = create_strength_analysis_prompt(conversation_history)
        
        assert "会話履歴:" in prompt
        assert "ユーザー: テストメッセージ1" in prompt
        assert "AI: 返答1" in prompt
    
    def test_プロンプトにすべての評価項目が含まれる(self):
        """プロンプトに全ての強みカテゴリが含まれることを確認"""
        prompt = create_strength_analysis_prompt([])
        
        for key, category in STRENGTH_CATEGORIES.items():
            assert key in prompt
            assert category["name"] in prompt
            assert category["description"] in prompt
            # インジケーターも含まれているか確認
            for indicator in category["indicators"]:
                assert indicator in prompt
    
    def test_プロンプトにJSON形式の指示が含まれる(self):
        """プロンプトにJSON形式での回答指示が含まれることを確認"""
        prompt = create_strength_analysis_prompt([])
        
        assert "以下の形式で回答してください" in prompt
        assert '"empathy": XX' in prompt
        assert '"clarity": XX' in prompt
        assert "JSONのみを返し" in prompt


class TestParseStrengthAnalysis:
    """AI分析結果のパース機能のテスト"""
    
    def test_正常なJSON形式の解析(self):
        """正しいJSON形式のレスポンスが適切に解析されることを確認"""
        valid_response = json.dumps({
            "empathy": 85,
            "clarity": 70,
            "active_listening": 75,
            "adaptability": 80,
            "positivity": 78,
            "professionalism": 82
        })
        
        result = parse_strength_analysis(valid_response)
        
        assert result["empathy"] == 85
        assert result["clarity"] == 70
        assert result["active_listening"] == 75
        assert len(result) == 6
    
    def test_シンプルなスコア形式の解析(self):
        """スコアが数値のみの形式でも解析できることを確認"""
        simple_response = json.dumps({
            "empathy": 85,
            "clarity": 70,
            "active_listening": 50,
            "adaptability": 50,
            "positivity": 50,
            "professionalism": 50
        })
        
        result = parse_strength_analysis(simple_response)
        
        assert result["empathy"] == 85
        assert result["clarity"] == 70
    
    def test_不正なJSON形式の場合のフォールバック(self):
        """JSON解析エラー時にデフォルト値が返されることを確認"""
        invalid_response = "これはJSONではありません"
        
        result = parse_strength_analysis(invalid_response)
        
        assert all(score == 50 for score in result.values())
        assert len(result) == 6
    
    def test_部分的に欠損したJSONの処理(self):
        """一部のフィールドが欠損していても処理できることを確認"""
        partial_response = json.dumps({
            "empathy": 80,
            "clarity": 75
            # 他のキーが欠損
        })
        
        result = parse_strength_analysis(partial_response)
        
        assert result["empathy"] == 80
        assert result["clarity"] == 75
        # 欠損キーはデフォルト値
        assert result["active_listening"] == 50
        assert result["adaptability"] == 50


class TestGetTopStrengths:
    """トップ強みの取得機能のテスト"""
    
    def test_トップ3の強みを正しく取得(self):
        """スコアが高い順に3つの強みが取得されることを確認"""
        scores = {
            "empathy": 90,
            "clarity": 85,
            "active_listening": 80,
            "adaptability": 75,
            "positivity": 70,
            "professionalism": 65
        }
        
        top_strengths = get_top_strengths(scores, 3)
        
        assert len(top_strengths) == 3
        # キーはkeyではなくnameで参照
        assert top_strengths[0]["score"] == 90
        assert top_strengths[1]["score"] == 85
        assert top_strengths[2]["score"] == 80
        # 名前が含まれていることを確認
        assert top_strengths[0]["name"] == "共感力"
        assert top_strengths[1]["name"] == "明確な伝達力"
    
    def test_強み情報に名前と説明が含まれる(self):
        """取得した強み情報に必要な属性が含まれることを確認"""
        scores = {"empathy": 90}
        
        top_strengths = get_top_strengths(scores, 1)
        
        assert top_strengths[0]["name"] == STRENGTH_CATEGORIES["empathy"]["name"]
        assert top_strengths[0]["description"] == STRENGTH_CATEGORIES["empathy"]["description"]
    
    def test_スコアが少ない場合の処理(self):
        """スコア数がtop_nより少ない場合の処理を確認"""
        scores = {"empathy": 90, "clarity": 85}
        
        top_strengths = get_top_strengths(scores, 5)
        
        assert len(top_strengths) == 2


class TestCalculateScoreImprovement:
    """スコア改善計算のテスト"""
    
    def test_前回からの改善を正しく計算(self):
        """前回のスコアとの差分が正しく計算されることを確認"""
        current_scores = {"empathy": 85, "clarity": 75}
        history = [{
            "scores": {"empathy": 70, "clarity": 80}
        }]
        
        improvements = calculate_score_improvement(current_scores, history)
        
        assert improvements["empathy"] == 15
        assert improvements["clarity"] == -5
    
    def test_履歴が空の場合は空の辞書を返す(self):
        """履歴がない場合、空の辞書が返されることを確認"""
        current_scores = {"empathy": 85}
        
        improvements = calculate_score_improvement(current_scores, [])
        
        assert improvements == {}
    
    def test_新しいカテゴリが追加された場合の処理(self):
        """現在のスコアに新しいカテゴリがある場合の処理を確認"""
        current_scores = {"empathy": 85, "new_skill": 60}
        history = [{
            "scores": {"empathy": 70}
        }]
        
        improvements = calculate_score_improvement(current_scores, history)
        
        assert improvements["empathy"] == 15
        assert "new_skill" not in improvements


class TestGenerateEncouragementMessages:
    """励ましメッセージ生成のテスト"""
    
    def test_練習回数による励ましメッセージ(self):
        """練習回数が閾値を超えた場合のメッセージ生成を確認"""
        scores = {"empathy": 80, "clarity": 75}
        # 練習回数4回の履歴（+現在で5回）
        history = [{} for _ in range(4)]
        
        messages = generate_encouragement_messages(scores, history)
        
        # メッセージの内容を確認（複数のパターンがあるため柔軟にチェック）
        practice_keywords = ["練習", "継続", "積み重ね", "コンスタント"]
        assert any(any(keyword in msg for keyword in practice_keywords) for msg in messages)
    
    def test_高得点スキルによる励ましメッセージ(self):
        """高得点（80点以上）のスキルがある場合のメッセージ生成を確認"""
        scores = {"empathy": 85, "clarity": 60}
        
        messages = generate_encouragement_messages(scores, [])
        
        # 高得点スキルに関するメッセージがあることを確認
        assert any("共感力" in msg for msg in messages)
        strength_keywords = ["強み", "才能", "素晴らしい", "高得点"]
        assert any(any(keyword in msg for keyword in strength_keywords) for msg in messages)
    
    def test_バランスの取れた成長によるメッセージ(self):
        """全スキルが閾値以上の場合のメッセージ生成を確認"""
        scores = {
            "empathy": 65,
            "clarity": 70,
            "active_listening": 68,
            "adaptability": 72,
            "positivity": 65,
            "professionalism": 70
        }
        
        messages = generate_encouragement_messages(scores, [])
        
        # バランスの取れた成長に関するメッセージがあることを確認
        balance_keywords = ["バランス", "全体", "総合", "すべて", "着実"]
        assert any(any(keyword in msg for keyword in balance_keywords) for msg in messages)
    
    def test_スコア改善によるメッセージ(self):
        """大幅なスコア改善（10点以上）がある場合のメッセージ生成を確認"""
        scores = {"empathy": 85}
        history = [{
            "scores": {"empathy": 70}
        }]
        
        messages = generate_encouragement_messages(scores, history)
        
        # スコア改善に関するメッセージがあることを確認
        improvement_keywords = ["向上", "成長", "上達", "改善", "ポイント"]
        assert any(any(keyword in msg for keyword in improvement_keywords) for msg in messages)
        # 共感力についての言及も確認
        assert any("共感力" in msg for msg in messages)
    
    def test_デフォルトメッセージの生成(self):
        """特別な条件に該当しない場合のデフォルトメッセージを確認"""
        scores = {"empathy": 55}
        
        messages = generate_encouragement_messages(scores, [])
        
        assert len(messages) > 0
        assert "着実に成長しています" in messages[0]


class TestAnalyzeUserStrengths:
    """ユーザー強み分析（シンプル版）のテスト"""
    
    def test_空の会話履歴でデフォルト値を返す(self):
        """会話履歴が空の場合、全て50点のデフォルト値を返すことを確認"""
        scores = analyze_user_strengths("")
        
        assert all(score == 50 for score in scores.values())
        assert len(scores) == 6
    
    def test_会話履歴がある場合のスコア生成(self):
        """会話履歴がある場合、60点以上のスコアが生成されることを確認"""
        conversation = "こんにちは\nよろしくお願いします\nありがとうございます"
        
        scores = analyze_user_strengths(conversation)
        
        assert all(40 <= score <= 95 for score in scores.values())
        assert all(score >= 50 for score in scores.values())  # 基本的に50点以上
    
    def test_全カテゴリのスコアが含まれる(self):
        """全ての強みカテゴリのスコアが含まれることを確認"""
        scores = analyze_user_strengths("test")
        
        for category in STRENGTH_CATEGORIES.keys():
            assert category in scores
    
    @patch('random.randint')
    def test_ランダム変動の適用(self, mock_randint):
        """ランダムな変動が適切に適用されることを確認"""
        # ランダム値を固定（全て+5）
        mock_randint.return_value = 5
        
        conversation = "test"
        scores = analyze_user_strengths(conversation)
        
        # 基本スコア62 + 変動5 = 67
        assert all(score == 67 for score in scores.values())


class TestCreatePersonalizedMessagePrompt:
    """パーソナライズメッセージプロンプト生成のテスト"""
    
    def test_トップ3の強みが含まれる(self):
        """プロンプトにトップ3の強みが含まれることを確認"""
        scores = {
            "empathy": 90,
            "clarity": 85,
            "active_listening": 80,
            "adaptability": 70
        }
        base_message = "素晴らしい成長です！"
        
        prompt = create_personalized_message_prompt(scores, base_message)
        
        assert "共感力" in prompt
        assert "明確な伝達力" in prompt
        assert "傾聴力" in prompt
        assert "90点" in prompt
    
    def test_基本メッセージが含まれる(self):
        """基本メッセージがプロンプトに含まれることを確認"""
        scores = {"empathy": 80}
        base_message = "テスト基本メッセージ"
        
        prompt = create_personalized_message_prompt(scores, base_message)
        
        assert base_message in prompt
    
    def test_文字数制限の指示が含まれる(self):
        """50文字以内という制限がプロンプトに含まれることを確認"""
        scores = {"empathy": 80}
        
        prompt = create_personalized_message_prompt(scores, "test")
        
        assert "50文字以内" in prompt


class TestIntegration:
    """統合テスト"""
    
    def test_エンドツーエンドの強み分析フロー(self):
        """会話履歴から強み分析、メッセージ生成までの一連の流れをテスト"""
        # 1. 会話履歴からスコアを生成
        conversation = "相手の気持ちを考えて話すことが大切だと思います"
        scores = analyze_user_strengths(conversation)
        
        # 2. トップ強みを取得
        top_strengths = get_top_strengths(scores, 3)
        assert len(top_strengths) == 3
        
        # 3. 励ましメッセージを生成
        messages = generate_encouragement_messages(scores, [])
        assert len(messages) > 0
        
        # 4. パーソナライズメッセージ用プロンプトを作成
        prompt = create_personalized_message_prompt(scores, messages[0])
        assert "ユーザーのコミュニケーションスキル分析結果" in prompt