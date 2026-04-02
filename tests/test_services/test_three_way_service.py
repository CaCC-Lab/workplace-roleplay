"""
ThreeWayConversationService のユニットテスト
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.three_way_service import ThreeWayConversationService


@pytest.fixture
def svc():
    return ThreeWayConversationService()


class TestJoinConversation:
    def test_join_returns_joined_true_and_three_party_turn_order(self, svc):
        # Given: 未参加ユーザー
        uid = "u1"

        # When: 参加する
        r = svc.join_conversation(uid, [])

        # Then: joined・3者の turn_order
        assert r["joined"] is True
        assert "turn_order" in r
        assert r["turn_order"] == ["A", "B", "user"]
        assert len(r["turn_order"]) == 3
        assert set(r["turn_order"]) == {"A", "B", "user"}

    def test_join_with_empty_watch_history_ok(self, svc):
        # Given: 空の watch_history
        # When / Then: 参加できる
        r = svc.join_conversation("u-empty", [])
        assert r["joined"] is True

    def test_second_join_returns_already_joined_error(self, svc):
        # Given: 同一ユーザーが既に参加済み
        uid = "u-dup"
        assert svc.join_conversation(uid, [])["joined"] is True

        # When: 再度参加
        r2 = svc.join_conversation(uid, [])

        # Then: 既に参加済みエラー
        assert r2["joined"] is False
        assert r2.get("error") == "already_joined"
        assert r2.get("turn_order") is None


class TestNextSpeakerAndUserMessage:
    def test_next_speaker_after_user_message(self, svc):
        # Given: 標準のターン順
        order = ["A", "B", "user"]
        history = [{"role": "A", "content": "A1"}, {"role": "B", "content": "B1"}]

        # When: ユーザーが発言した直後の次話者
        after_user = svc.add_user_message(history, "こんにちは", order)

        # Then: ユーザーの次は A
        assert after_user["next_speaker"] == "A"
        assert len(after_user["updated_history"]) == len(history) + 1
        assert after_user["updated_history"][-1]["role"] == "user"

    def test_get_next_speaker_empty_history_first_is_a(self, svc):
        svc = ThreeWayConversationService()
        order = ["A", "B", "user"]
        assert svc.get_next_speaker([], order) == "A"


class TestLeaveConversation:
    def test_leave_returns_mode_watch(self, svc):
        # Given: 参加済み
        svc.join_conversation("u-leave", [])

        # When: 退出
        out = svc.leave_conversation("u-leave")

        # Then
        assert out["left"] is True
        assert out["mode"] == "watch"
