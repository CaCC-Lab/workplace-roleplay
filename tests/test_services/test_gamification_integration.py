"""
ゲーミフィケーション統合テスト（要件2.1, 3.2, 3.3, 4.3, 6.1 / tasks.md Task 10.3）

シナリオ完了フック相当の処理をサービス層で連結し、例外なく完走することを検証する。
参照: .kiro/specs/gamification/requirements.md, tasks.md（src/ は参照しない）
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from services.badge_service import BadgeService
from services.gamification_constants import SIX_AXES
from services.gamification_service import GamificationService
from services.quest_service import QuestService
from services.unlock_service import UnlockService
from services.user_data_service import UserDataService


def _scenario_service_stub() -> MagicMock:
    m = MagicMock()
    m.get_all_scenarios.return_value = {
        "sc_beg": {"difficulty": "beginner"},
        "sc_int": {"difficulty": "intermediate"},
    }
    m.get_scenario_by_id.side_effect = lambda sid: m.get_all_scenarios.return_value.get(sid, {"difficulty": "beginner"})
    return m


def _record_scenario_completion(
    uds: UserDataService,
    user_id: str,
    scenario_id: str,
    *,
    difficulty: str = "beginner",
) -> None:
    """シナリオ完了時に scenario_completions / stats を更新する（Task 10.3 のフック相当）"""
    data = uds.get_user_data(user_id)
    now = datetime.now(timezone.utc).isoformat()
    sc = data.setdefault("scenario_completions", {})
    if scenario_id not in sc:
        sc[scenario_id] = {
            "count": 0,
            "first_completed_at": now,
            "last_completed_at": now,
            "best_scores": {},
            "difficulty": difficulty,
        }
    sc[scenario_id]["count"] = int(sc[scenario_id]["count"]) + 1
    sc[scenario_id]["last_completed_at"] = now
    sc[scenario_id]["difficulty"] = difficulty
    st = data.setdefault("stats", {})
    st["total_scenarios_completed"] = int(st.get("total_scenarios_completed", 0) or 0) + 1
    uds.save_user_data(user_id, data)


@pytest.fixture
def uds(tmp_path):
    # Given: 一時ディレクトリにユーザーデータを保存する UserDataService
    return UserDataService(data_dir=str(tmp_path))


class TestGamificationIntegrationHooks:
    """Task 10.3: フィードバック後XP → 完了記録 → クエスト → バッジ → アンロック"""

    def test_feedback_scores_increase_skill_xp(self, uds):
        # Given: フィードバック由来の6軸スコア（要件2.1: スコアからXP計算）
        # When: calculate_xp_from_scores → add_xp
        # Then: skill_xp が増加する
        uid = "u-xp"
        gs = GamificationService(uds)
        before = uds.get_user_data(uid)["skill_xp"]["empathy"]
        scores = {a: 72 for a in SIX_AXES}
        gains = gs.calculate_xp_from_scores(scores, "normal")
        gains["scores_snapshot"] = scores
        gains["scenario_id"] = "sc1"
        gs.add_xp(uid, gains, "scenario_completion")
        after = uds.get_user_data(uid)["skill_xp"]["empathy"]
        assert after == before + 72

    def test_scenario_completion_updates_scenario_completions(self, uds):
        # Given: ユーザーとシナリオID
        # When: 完了を記録する
        # Then: scenario_completions と total_scenarios_completed が更新される
        uid = "u-sc"
        _record_scenario_completion(uds, uid, "scenario_a", difficulty="beginner")
        d = uds.get_user_data(uid)
        assert "scenario_a" in d["scenario_completions"]
        assert d["scenario_completions"]["scenario_a"]["count"] == 1
        assert d["scenario_completions"]["scenario_a"]["difficulty"] == "beginner"
        assert d["stats"]["total_scenarios_completed"] == 1

    def test_three_beginner_completions_unlock_intermediate(self, uds):
        # Given: beginner シナリオを規定数（3）完了相当のデータ
        # When: check_and_unlock
        # Then: intermediate がアンロック（要件3.2, 3.3）
        uid = "u-unlock"
        unlock = UnlockService(uds, _scenario_service_stub())
        for i in range(3):
            _record_scenario_completion(uds, uid, f"beg{i}", difficulty="beginner")
        newly = unlock.check_and_unlock(uid)
        assert "intermediate" in newly
        assert uds.get_user_data(uid)["unlock_status"]["intermediate"] is True

    def test_after_xp_quest_progress_updates_via_activity(self, uds):
        # Given: アクティブなデイリークエスト（scenarios_today）
        # When: シナリオ活動に相当する check_quest_completion
        # Then: 該当クエストの current_value が増える（要件4.3）
        uid = "u-q"
        qs = QuestService(uds)
        qs.get_active_quests(uid)
        before = None
        for q in uds.get_user_data(uid)["quests"]["daily"]:
            if q.get("target_key") == "scenarios_today":
                before = int(q.get("current_value", 0) or 0)
                break
        assert before is not None
        qs.check_quest_completion(uid, {"target_key": "scenarios_today", "delta": 1})
        after = None
        for q in uds.get_user_data(uid)["quests"]["daily"]:
            if q.get("target_key") == "scenarios_today":
                after = int(q.get("current_value", 0) or 0)
                break
        assert after == before + 1

    def test_badge_eligibility_returns_candidate_when_condition_met(self, uds):
        # Given: 初回シナリオ完了相当の統計（要件6.1）
        # When: check_badge_eligibility
        # Then: first_step が候補に含まれる
        uid = "u-badge"
        _record_scenario_completion(uds, uid, "once", difficulty="beginner")
        bs = BadgeService(uds)
        cand = bs.check_badge_eligibility(uid)
        ids = {b["badge_id"] for b in cand}
        assert "first_step" in ids

    def test_full_chain_add_xp_quest_badge_unlock_no_exception(self, uds):
        # Given: 全サービスと同一ユーザー
        # When: add_xp → 完了記録 → クエスト → バッジ判定 → アンロック（3回で中級解放）
        # Then: 例外なく完走し、最終状態が一貫する
        uid = "u-chain"
        gs = GamificationService(uds)
        qs = QuestService(uds)
        bs = BadgeService(uds)
        unlock = UnlockService(uds, _scenario_service_stub())

        qs.get_active_quests(uid)

        for i in range(3):
            scores = {a: 60 + i for a in SIX_AXES}
            gains = gs.calculate_xp_from_scores(scores, "normal")
            gains["scores_snapshot"] = scores
            gains["scenario_id"] = f"chain{i}"
            gs.add_xp(uid, gains, "scenario_completion")
            _record_scenario_completion(uds, uid, f"chain{i}", difficulty="beginner")
            qs.check_quest_completion(uid, {"target_key": "scenarios_today", "delta": 1})
            bs.check_badge_eligibility(uid)
            unlock.check_and_unlock(uid)

        final = uds.get_user_data(uid)
        assert final["unlock_status"]["intermediate"] is True
        assert final["stats"]["total_scenarios_completed"] == 3
        assert sum(final["skill_xp"].values()) > 0
