"""
ModerationService のユニットテスト
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.moderation_service import ModerationService


@pytest.fixture
def svc():
    return ModerationService()


class TestCheckMessageAllowed:
    def test_normal_message_is_allowed(self, svc):
        # Given: NG を含まない通常メッセージ
        text = "こんにちは。本日の会議の件で連絡しました。"

        # When: チェックする
        result = svc.check_message(text)

        # Then: 許可され、理由なし、フィルタ後は原文と同じ
        assert result["allowed"] is True
        assert result["reason"] is None
        assert result["filtered_text"] == text


class TestCheckMessageNg:
    def test_ng_word_sets_allowed_false_and_reason(self, svc):
        # Given: デフォルト NG 語を含むメッセージ
        text = "その発言はばかげています。"

        # When: チェックする
        result = svc.check_message(text)

        # Then: 不許可・理由は inappropriate_word
        assert result["allowed"] is False
        assert result["reason"] == "inappropriate_word"

    def test_ng_word_replaced_in_filtered_text(self, svc):
        # Given: NG 語「ばか」を含む
        text = "テストばかりしています。"

        # When: チェックする
        result = svc.check_message(text)

        # Then: filtered_text で NG 語がマスクされている
        assert result["allowed"] is False
        assert "ばか" not in result["filtered_text"]
        assert "*" * 2 in result["filtered_text"] or "***" in result["filtered_text"]


class TestDetectLoop:
    def test_same_user_content_three_times_is_loop(self, svc):
        # Given: 末尾の user が同一内容を 3 回（user のみの連続末尾ラン）
        history = [
            {"role": "user", "content": "同じ発言です"},
            {"role": "assistant", "content": "もう少し詳しく"},
            {"role": "user", "content": "同じ発言です"},
            {"role": "assistant", "content": "了解です"},
            {"role": "user", "content": "同じ発言です"},
        ]

        # When: 閾値 3 でループ検出
        assert svc.detect_loop(history, threshold=3) is True

    def test_two_repetitions_not_loop_at_threshold_three(self, svc):
        # Given: 同一 user 内容が末尾で 2 回のみ
        history = [
            {"role": "user", "content": "繰り返し"},
            {"role": "assistant", "content": "はい"},
            {"role": "user", "content": "繰り返し"},
        ]

        # When: 閾値 3
        # Then: ループではない
        assert svc.detect_loop(history, threshold=3) is False


class TestCheckRelevance:
    def test_related_message_is_relevant(self, svc):
        # Given: 話題のキーワードがメッセージに含まれる
        topic = "プロジェクトの進捗"
        message = "進捗状況について報告します。"

        # When: 関連性を判定
        result = svc.check_relevance(message, topic)

        # Then: 関連あり・提案なし
        assert result["relevant"] is True
        assert result["suggestion"] is None

    def test_unrelated_message_is_not_relevant(self, svc):
        # Given: 話題と無関係な内容
        topic = "会議の準備"
        message = "今日の天気はとても晴れています。"

        # When: 関連性を判定
        result = svc.check_relevance(message, topic)

        # Then: 脱線・固定の提案文
        assert result["relevant"] is False
        assert result["suggestion"] == "元の話題に戻りましょう"
