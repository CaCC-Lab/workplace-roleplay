"""
更新された強み分析機能のユニットテスト

parse_strength_analysisの新しい返り値形式に対応
"""
import pytest
import json
from strength_analyzer import (
    create_strength_analysis_prompt,
    parse_strength_analysis,
    get_top_strengths,
    STRENGTH_CATEGORIES
)


class TestCreateStrengthAnalysisPrompt:
    """create_strength_analysis_prompt関数のテスト"""
    
    def test_会話履歴の正しいフォーマット(self):
        """会話履歴が正しくフォーマットされるかのテスト"""
        conversation = [
            {"role": "user", "content": "テストメッセージ1"},
            {"role": "assistant", "content": "返答1"},
            {"role": "user", "content": "テストメッセージ2"}
        ]
        
        prompt = create_strength_analysis_prompt(conversation)
        
        # フォーマットされた会話が含まれていることを確認
        assert "ユーザー: テストメッセージ1" in prompt
        assert "AI: 返答1" in prompt
        assert "ユーザー: テストメッセージ2" in prompt
    
    def test_評価項目が全て含まれる(self):
        """全ての評価項目がプロンプトに含まれるかのテスト"""
        prompt = create_strength_analysis_prompt([])
        
        for key, category in STRENGTH_CATEGORIES.items():
            assert key in prompt
            assert category["name"] in prompt
            assert category["description"] in prompt
    
    def test_JSON形式の指示が含まれる(self):
        """JSON形式での回答指示が含まれるかのテスト"""
        prompt = create_strength_analysis_prompt([])
        
        assert "以下の形式で回答してください" in prompt
        assert '"empathy": XX' in prompt
        assert '"clarity": XX' in prompt
        assert "JSONのみを返し" in prompt
    
    def test_空の会話履歴でもプロンプトが生成される(self):
        """空の会話履歴でもプロンプトが生成されるかのテスト"""
        prompt = create_strength_analysis_prompt([])
        
        assert prompt is not None
        assert len(prompt) > 0
        assert "会話履歴:" in prompt


class TestParseStrengthAnalysis:
    """parse_strength_analysis関数のテスト（新形式）"""
    
    def test_正常なJSON形式の解析(self):
        """正常なJSON形式の解析テスト"""
        response = json.dumps({
            "empathy": 75,
            "clarity": 80,
            "active_listening": 70,
            "adaptability": 65,
            "positivity": 85,
            "professionalism": 90
        })
        
        result = parse_strength_analysis(response)
        
        assert isinstance(result, dict)
        assert result["empathy"] == 75
        assert result["clarity"] == 80
        assert len(result) == 6
    
    def test_前後にテキストがあるJSONの解析(self):
        """JSON前後にテキストがある場合の解析テスト"""
        response = """
        以下が分析結果です：
        {
            "empathy": 60,
            "clarity": 70,
            "active_listening": 65,
            "adaptability": 55,
            "positivity": 75,
            "professionalism": 80
        }
        分析完了しました。
        """
        
        result = parse_strength_analysis(response)
        
        assert result["empathy"] == 60
        assert result["positivity"] == 75
    
    def test_範囲外の値の正規化(self):
        """0-100範囲外の値が正規化されるかのテスト"""
        response = json.dumps({
            "empathy": 150,  # 100を超える
            "clarity": -10,  # 0未満
            "active_listening": 50,
            "adaptability": 50,
            "positivity": 50,
            "professionalism": 50
        })
        
        result = parse_strength_analysis(response)
        
        assert result["empathy"] == 100  # 100に制限
        assert result["clarity"] == 0     # 0に制限
        assert result["active_listening"] == 50
    
    def test_不正なJSON形式のフォールバック(self):
        """不正なJSON形式の場合のフォールバックテスト"""
        response = "これは無効なJSONです"
        
        result = parse_strength_analysis(response)
        
        # デフォルト値（50）が返される
        assert all(score == 50 for score in result.values())
        assert len(result) == 6
    
    def test_部分的に欠損したデータの処理(self):
        """一部のキーが欠損している場合のテスト"""
        response = json.dumps({
            "empathy": 70,
            "clarity": 75,
            # 他のキーが欠損
        })
        
        result = parse_strength_analysis(response)
        
        assert result["empathy"] == 70
        assert result["clarity"] == 75
        # 欠損キーはデフォルト値
        assert result["active_listening"] == 50
        assert result["adaptability"] == 50
    
    def test_数値以外の値の処理(self):
        """数値以外の値が含まれる場合のテスト"""
        response = json.dumps({
            "empathy": "高い",  # 文字列
            "clarity": None,    # null
            "active_listening": 60,
            "adaptability": True,  # boolean
            "positivity": 70,
            "professionalism": 80
        })
        
        result = parse_strength_analysis(response)
        
        assert result["empathy"] == 50  # デフォルト値
        assert result["clarity"] == 50   # デフォルト値
        assert result["active_listening"] == 60
        assert result["adaptability"] == 1  # boolean Trueは1になる


class TestGetTopStrengths:
    """get_top_strengths関数のテスト"""
    
    def test_トップ3の強みを正しく取得(self):
        """スコアの高い順にトップ3を取得するテスト"""
        scores = {
            "empathy": 60,
            "clarity": 90,
            "active_listening": 70,
            "adaptability": 55,
            "positivity": 85,
            "professionalism": 75
        }
        
        result = get_top_strengths(scores, top_n=3)
        
        assert len(result) == 3
        assert result[0]["score"] == 90  # clarity
        assert result[1]["score"] == 85  # positivity
        assert result[2]["score"] == 75  # professionalism
    
    def test_強み情報の完全性(self):
        """返される強み情報が完全かのテスト"""
        scores = {"empathy": 80, "clarity": 70}
        
        result = get_top_strengths(scores, top_n=1)
        
        assert len(result) == 1
        strength = result[0]
        assert "name" in strength
        assert "description" in strength
        assert "score" in strength
        assert strength["name"] == STRENGTH_CATEGORIES["empathy"]["name"]
    
    def test_同スコアの場合の処理(self):
        """同じスコアが複数ある場合のテスト"""
        scores = {
            "empathy": 70,
            "clarity": 70,
            "active_listening": 70,
            "adaptability": 60,
            "positivity": 60,
            "professionalism": 60
        }
        
        result = get_top_strengths(scores, top_n=3)
        
        assert len(result) == 3
        assert all(s["score"] == 70 for s in result)