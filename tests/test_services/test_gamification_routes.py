"""
ゲーミフィケーション / クイズ API の統合テスト（tasks.md Task 10.4）

参照: .kiro/specs/gamification/requirements.md, design.md, tasks.md
"""

from __future__ import annotations

import json

import pytest

from services.user_data_service import UserDataService


@pytest.fixture
def gamification_app(monkeypatch, tmp_path):
    """user_data を一時ディレクトリに向ける"""
    from routes import gamification_routes as gr
    from routes import quiz_routes as qr

    def _uds(*a, **kw):
        kw = dict(kw)
        kw.setdefault("data_dir", str(tmp_path))
        return UserDataService(*a, **kw)

    monkeypatch.setattr(gr, "UserDataService", _uds)
    monkeypatch.setattr(qr, "UserDataService", _uds)
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def gclient(gamification_app):
    return gamification_app.test_client()


class TestGamificationRoutesIntegration:
    def test_dashboard_growth_quests_badges_unlock_json_shape(self, gclient):
        # Given: セッションに user_id
        # When: 各 GET エンドポイント
        # Then: JSON に主要キーが含まれる（要件2.3, 3.5, 4.4, 6.3）
        with gclient.session_transaction() as s:
            s["user_id"] = "integration-user-1"

        for path, keys in (
            ("/api/gamification/dashboard", ("skill_xp", "quests")),
            ("/api/gamification/growth", ("personal_best", "last_10_average")),
            ("/api/gamification/quests", ("daily", "weekly")),
            ("/api/gamification/badges", ("badges",)),
            ("/api/gamification/unlock-status", ("unlock_status", "scenarios")),
        ):
            rv = gclient.get(path)
            assert rv.status_code == 200, path
            js = rv.get_json()
            for k in keys:
                assert k in js, (path, k)

    def test_flow_xp_quest_badge_unlock(self, gclient, tmp_path):
        # Given: ユーザーデータを操作し、サービスを直接呼び出してフローを模擬
        # When: シナリオ完了相当の XP・クエスト・バッジ・アンロック
        # Then: 例外なく一貫した状態（tasks 10.4 のフロー検証）
        uid = "flow-user"
        with gclient.session_transaction() as s:
            s["user_id"] = uid

        uds = UserDataService(data_dir=str(tmp_path))
        from services.badge_service import BadgeService
        from services.gamification_service import GamificationService
        from services.quest_service import QuestService
        from services.scenario_service import ScenarioService
        from services.unlock_service import UnlockService

        gs = GamificationService(uds)
        qs = QuestService(uds)
        bs = BadgeService(uds)
        us = UnlockService(uds, ScenarioService())

        gs.add_xp(
            uid,
            {a: 5 for a in ["empathy", "clarity", "active_listening", "adaptability", "positivity", "professionalism"]},
            "scenario_completion",
        )
        d = uds.get_user_data(uid)
        d.setdefault("stats", {})["total_scenarios_completed"] = 1
        uds.save_user_data(uid, d)

        qs.check_quest_completion(uid, {"target_key": "scenarios_today", "delta": 1})
        bs.check_badge_eligibility(uid)
        us.check_and_unlock(uid)

        rv = gclient.get("/api/gamification/dashboard")
        assert rv.status_code == 200
        body = rv.get_json()
        assert "skill_xp" in body
        assert body["skill_xp"]["empathy"] >= 5


class TestQuizRoutesIntegration:
    def test_generate_answer_summary(self, gclient):
        # Given: セッション
        # When: POST generate / answer / GET summary
        # Then: クイズ形状とサマリー（要件5.2, 5.5）
        with gclient.session_transaction() as s:
            s["user_id"] = "quiz-user"

        rv = gclient.post(
            "/api/quiz/generate",
            data=json.dumps({"context": []}),
            content_type="application/json",
        )
        assert rv.status_code == 200
        q = rv.get_json()["quiz"]
        assert "choices" in q and 3 <= len(q["choices"]) <= 4

        rv2 = gclient.post(
            "/api/quiz/answer",
            data=json.dumps(
                {
                    "quiz": q,
                    "user_answer": int(q["correct_answer"]),
                    "context": [],
                }
            ),
            content_type="application/json",
        )
        assert rv2.status_code == 200
        assert rv2.get_json()["bonus_xp"] > 0

        rv3 = gclient.get("/api/quiz/summary")
        assert rv3.status_code == 200
        sm = rv3.get_json()
        assert "accuracy" in sm and "total" in sm
