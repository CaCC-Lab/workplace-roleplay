"""
Helpers utility tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage


class TestExtractContent:
    """extract_content関数のテスト"""

    def test_AIMessageからコンテンツを抽出(self):
        """AIMessageからコンテンツを抽出"""
        from utils.helpers import extract_content

        msg = AIMessage(content="こんにちは")
        result = extract_content(msg)

        assert result == "こんにちは"

    def test_文字列からコンテンツを抽出(self):
        """文字列はそのまま返す"""
        from utils.helpers import extract_content

        result = extract_content("テスト")

        assert result == "テスト"

    def test_空リストからコンテンツを抽出(self):
        """空リストの場合はデフォルトメッセージ"""
        from utils.helpers import extract_content

        result = extract_content([])

        assert "空" in result

    def test_リストからコンテンツを抽出(self):
        """リストの最後の要素からコンテンツを抽出"""
        from utils.helpers import extract_content

        result = extract_content(["first", "last"])

        assert result == "last"

    def test_辞書のcontentキーからコンテンツを抽出(self):
        """辞書のcontentキーからコンテンツを抽出"""
        from utils.helpers import extract_content

        result = extract_content({"content": "コンテンツ"})

        assert result == "コンテンツ"

    def test_辞書のtextキーからコンテンツを抽出(self):
        """辞書のtextキーからコンテンツを抽出"""
        from utils.helpers import extract_content

        result = extract_content({"text": "テキスト"})

        assert result == "テキスト"

    def test_辞書のmessageキーからコンテンツを抽出(self):
        """辞書のmessageキーからコンテンツを抽出"""
        from utils.helpers import extract_content

        result = extract_content({"message": "メッセージ"})

        assert result == "メッセージ"

    def test_辞書のresponseキーからコンテンツを抽出(self):
        """辞書のresponseキーからコンテンツを抽出"""
        from utils.helpers import extract_content

        result = extract_content({"response": "レスポンス"})

        assert result == "レスポンス"

    def test_その他の型は文字列に変換(self):
        """その他の型は文字列に変換"""
        from utils.helpers import extract_content

        result = extract_content(123)

        assert result == "123"


class TestFormatConversationHistory:
    """format_conversation_history関数のテスト"""

    def test_会話履歴をフォーマット(self):
        """会話履歴をフォーマット（ユーザーの発言のみ）"""
        from utils.helpers import format_conversation_history

        history = [
            {"human": "こんにちは", "ai": "こんにちは！"},
            {"human": "元気ですか", "ai": "元気です"},
        ]

        result = format_conversation_history(history)

        assert "ユーザー: こんにちは" in result
        assert "ユーザー: 元気ですか" in result
        assert "AI:" not in result

    def test_空の履歴(self):
        """空の履歴"""
        from utils.helpers import format_conversation_history

        result = format_conversation_history([])

        assert result == ""


class TestFormatConversationHistoryForFeedback:
    """format_conversation_history_for_feedback関数のテスト"""

    def test_フィードバック用にフォーマット(self):
        """フィードバック用に両方の発言をフォーマット"""
        from utils.helpers import format_conversation_history_for_feedback

        history = [
            {"human": "こんにちは", "ai": "こんにちは！"},
            {"human": "元気ですか", "ai": "元気です"},
        ]

        result = format_conversation_history_for_feedback(history)

        assert "ユーザー: こんにちは" in result
        assert "AI: こんにちは！" in result

    def test_開始メッセージを除外(self):
        """開始メッセージを除外"""
        from utils.helpers import format_conversation_history_for_feedback

        history = [
            {"human": "[シナリオ開始]", "ai": "はじめまして"},
            {"human": "こんにちは", "ai": "こんにちは！"},
        ]

        result = format_conversation_history_for_feedback(history)

        assert "[シナリオ開始]" not in result
        assert "ユーザー: こんにちは" in result

    def test_雑談開始メッセージを除外(self):
        """雑談開始メッセージを除外"""
        from utils.helpers import format_conversation_history_for_feedback

        history = [
            {"human": "[雑談開始]", "ai": "こんにちは"},
            {"human": "良い天気ですね", "ai": "そうですね"},
        ]

        result = format_conversation_history_for_feedback(history)

        assert "[雑談開始]" not in result


class TestGetPartnerDescription:
    """get_partner_description関数のテスト"""

    def test_同僚の説明(self):
        """同僚の説明を取得"""
        from utils.helpers import get_partner_description

        result = get_partner_description("colleague")

        assert "同僚" in result

    def test_先輩の説明(self):
        """先輩の説明を取得"""
        from utils.helpers import get_partner_description

        result = get_partner_description("senior")

        assert "先輩" in result

    def test_後輩の説明(self):
        """後輩の説明を取得"""
        from utils.helpers import get_partner_description

        result = get_partner_description("junior")

        assert "後輩" in result

    def test_上司の説明(self):
        """上司の説明を取得"""
        from utils.helpers import get_partner_description

        result = get_partner_description("boss")

        assert "課長" in result

    def test_クライアントの説明(self):
        """クライアントの説明を取得"""
        from utils.helpers import get_partner_description

        result = get_partner_description("client")

        assert "取引先" in result

    def test_不明なタイプはデフォルト(self):
        """不明なタイプはデフォルトの説明"""
        from utils.helpers import get_partner_description

        result = get_partner_description("unknown")

        assert result == "同僚"


class TestGetSituationDescription:
    """get_situation_description関数のテスト"""

    def test_ランチの説明(self):
        """ランチの説明を取得"""
        from utils.helpers import get_situation_description

        result = get_situation_description("lunch")

        assert "ランチ" in result or "カフェテリア" in result

    def test_休憩の説明(self):
        """休憩の説明を取得"""
        from utils.helpers import get_situation_description

        result = get_situation_description("break")

        assert "休憩" in result

    def test_朝の説明(self):
        """朝の説明を取得"""
        from utils.helpers import get_situation_description

        result = get_situation_description("morning")

        assert "朝" in result

    def test_夕方の説明(self):
        """夕方の説明を取得"""
        from utils.helpers import get_situation_description

        result = get_situation_description("evening")

        assert "終業" in result or "退社" in result

    def test_懇親会の説明(self):
        """懇親会の説明を取得"""
        from utils.helpers import get_situation_description

        result = get_situation_description("party")

        assert "懇親会" in result

    def test_不明なタイプはデフォルト(self):
        """不明なタイプはデフォルトの説明"""
        from utils.helpers import get_situation_description

        result = get_situation_description("unknown")

        assert result == "オフィスで"


class TestGetTopicDescription:
    """get_topic_description関数のテスト"""

    def test_一般的な話題の説明(self):
        """一般的な話題の説明を取得"""
        from utils.helpers import get_topic_description

        result = get_topic_description("general")

        assert "天気" in result or "一般的" in result

    def test_趣味の説明(self):
        """趣味の説明を取得"""
        from utils.helpers import get_topic_description

        result = get_topic_description("hobby")

        assert "趣味" in result

    def test_ニュースの説明(self):
        """ニュースの説明を取得"""
        from utils.helpers import get_topic_description

        result = get_topic_description("news")

        assert "ニュース" in result

    def test_食べ物の説明(self):
        """食べ物の説明を取得"""
        from utils.helpers import get_topic_description

        result = get_topic_description("food")

        assert "ランチ" in result or "食事" in result

    def test_仕事の説明(self):
        """仕事の説明を取得"""
        from utils.helpers import get_topic_description

        result = get_topic_description("work")

        assert "仕事" in result

    def test_不明なタイプはデフォルト(self):
        """不明なタイプはデフォルトの説明"""
        from utils.helpers import get_topic_description

        result = get_topic_description("unknown")

        assert result == "一般的な話題"


class TestAddMessagesFromHistory:
    """add_messages_from_history関数のテスト"""

    def test_履歴からメッセージを追加(self):
        """履歴からメッセージリストを構築"""
        from utils.helpers import add_messages_from_history

        messages = []
        history = [
            {"human": "こんにちは", "ai": "こんにちは！"},
            {"human": "元気ですか", "ai": "元気です"},
        ]

        result = add_messages_from_history(messages, history)

        assert len(result) == 4
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)

    def test_空の履歴(self):
        """空の履歴の場合"""
        from utils.helpers import add_messages_from_history

        messages = []
        result = add_messages_from_history(messages, [])

        assert len(result) == 0

    def test_最大エントリ数制限(self):
        """最大エントリ数を超える場合は最新のみ"""
        from utils.helpers import add_messages_from_history

        messages = []
        history = [{"human": f"msg{i}", "ai": f"resp{i}"} for i in range(10)]

        result = add_messages_from_history(messages, history, max_entries=3)

        # 最新3件 × 2（human + ai）= 6メッセージ
        assert len(result) == 6

    def test_humanのみのエントリ(self):
        """humanのみのエントリ"""
        from utils.helpers import add_messages_from_history

        messages = []
        history = [{"human": "テスト"}]

        result = add_messages_from_history(messages, history)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
