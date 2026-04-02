"""
バッジ獲得時の通知データ（要件6.4）

参照: .kiro/specs/gamification/requirements.md
"""

from __future__ import annotations

from services.badge_service import BadgeService
from services.gamification_constants import SIX_AXES
from services.user_data_service import UserDataService


class TestBadgeNotification:
    def test_on_scenario_feedback_new_badges_include_title_and_message(self, tmp_path, monkeypatch):
        # Given: 初回シナリオ完了で first_step が付与されるユーザーデータ
        # When: gamification_hooks.on_scenario_feedback
        # Then: new_badges に type / badge_id / title / message を含む通知が入る
        uds_root = tmp_path / "ud"
        uds_root.mkdir()

        def make_uds(*a, **kw):
            return UserDataService(data_dir=str(uds_root))

        monkeypatch.setattr("services.gamification_hooks._get_user_id", lambda: "notify-user-1")
        monkeypatch.setattr("services.gamification_hooks.UserDataService", make_uds)

        from services import gamification_hooks as gh

        scores = {a: 50 for a in SIX_AXES}
        out = gh.on_scenario_feedback(
            scores,
            "scenario_notify_1",
            scenario_data={"difficulty": "beginner"},
            session_id="session-notify-unique-1",
        )
        assert "new_badges" in out
        assert len(out["new_badges"]) >= 1
        n0 = out["new_badges"][0]
        assert n0["type"] == "badge_earned"
        assert n0["badge_id"] == "first_step"
        assert "title" in n0 and n0["title"]
        assert "message" in n0 and n0["message"]

    def test_award_badge_notification_shape(self, tmp_path):
        # Given: BadgeService と未獲得ユーザー
        # When: award_badge
        # Then: 通知に type, badge_id, title, message
        uds = UserDataService(data_dir=str(tmp_path))
        bs = BadgeService(uds)
        res = bs.award_badge("u2", "first_step")
        assert res["already_earned"] is False
        n = res["notification"]
        assert n["type"] == "badge_earned"
        assert n["badge_id"] == "first_step"
        assert n["title"] == "はじめの一歩"
        assert "はじめの一歩" in n["message"]

    def test_award_badge_already_earned_has_no_notification(self, tmp_path):
        # Given: 既に first_step を獲得済み
        # When: award_badge を再度呼ぶ
        # Then: notification は None（通知に含めない）
        uds = UserDataService(data_dir=str(tmp_path))
        bs = BadgeService(uds)
        r1 = bs.award_badge("u3", "first_step")
        assert r1["notification"] is not None
        r2 = bs.award_badge("u3", "first_step")
        assert r2["already_earned"] is True
        assert r2["notification"] is None
