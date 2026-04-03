"""
ConversationPersistenceService のユニットテスト（Supabase クライアントは Mock）
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.conversation_persistence_service import ConversationPersistenceService


@pytest.fixture
def mock_table():
    return MagicMock()


@pytest.fixture
def mock_client(mock_table):
    c = MagicMock()
    c.table.return_value = mock_table
    return c


@pytest.fixture
def svc(mock_client):
    return ConversationPersistenceService(mock_client)


class TestSaveConversation:
    def test_save_success_returns_id(self, svc, mock_table):
        # Given: insert が返す行に id が含まれる
        # When: save_conversation を呼ぶ
        # Then: dict(id) が返り insert が1回呼ばれる
        mock_table.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "row-1", "user_id": "u1", "mode": "chat"}]
        )
        r = svc.save_conversation("u1", "chat", [{"role": "user", "content": "hi"}], None)
        assert r == {"id": "row-1"}
        mock_table.insert.assert_called_once()

    def test_empty_history_allowed(self, svc, mock_table):
        # Given: 空の history を許容する insert 応答
        # When: history=[] で保存する
        # Then: id が返り payload の history は []
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "e1"}])
        r = svc.save_conversation("u1", "scenario", [], "sc1")
        assert r["id"] == "e1"
        call = mock_table.insert.call_args[0][0]
        assert call["history"] == []


class TestGetConversations:
    def test_filter_by_mode(self, svc, mock_table):
        # Given: user_id/mode で絞った select の結果が1件
        # When: get_conversations(user_id, mode, limit)
        # Then: 返却行の mode が一致する
        mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "1", "mode": "chat"}]
        )
        rows = svc.get_conversations("u1", "chat", 10)
        assert len(rows) == 1
        assert rows[0]["mode"] == "chat"

    def test_limit_applied(self, svc, mock_table):
        # Given: limit チェーンのモック
        # When: limit=5 で取得
        # Then: limit(5) が呼ばれる
        lim_mock = mock_table.select.return_value.eq.return_value.eq.return_value.limit
        lim_mock.return_value.execute.return_value = MagicMock(data=[])
        svc.get_conversations("u1", "watch", 5)
        lim_mock.assert_called_with(5)


class TestSearchConversations:
    def test_keyword_filter(self, svc, mock_table):
        # Given: 全件取得相当のデータにキーワード一致/不一致が混在
        # When: search_conversations(user_id, keyword)
        # Then: キーワードを含むメッセージのみ残る
        mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"id": "a", "history": [{"content": "hello world"}], "mode": "chat"},
                {"id": "b", "history": [{"content": "zzz"}], "mode": "chat"},
            ]
        )
        rows = svc.search_conversations("u1", "hello")
        assert len(rows) == 1
        assert rows[0]["id"] == "a"
