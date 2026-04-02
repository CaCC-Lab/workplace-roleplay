"""
ゲーミフィケーションが vibelogger へログ出力することの検証

検証: GAMIFICATION_VIBE_LOG_FILE を tmpdir に向け、JSON 行ログを読み取る。
参照: services/gamification_vibelogger.py（src/ は参照しない）
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.badge_service import BadgeService
from services.gamification_constants import SIX_AXES
from services.gamification_service import GamificationService
from services.quiz_service import QuizService
from services.user_data_service import UserDataService


def _read_vibe_entries(log_path):
    # Given: vibelogger が書き出したファイルパス
    # When: 行ごとに JSON として読む
    # Then: 辞書のリスト
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _has_operation_level(entries, operation: str, level: str) -> bool:
    return any(e.get("operation") == operation and e.get("level") == level for e in entries)


@pytest.fixture
def vibe_log_path(tmp_path, monkeypatch):
    """一時ログファイルに vibelogger を向け、各テストでシングルトンをリセットする"""
    p = tmp_path / "gamification.vibe.log"
    monkeypatch.setenv("GAMIFICATION_VIBE_LOG_FILE", str(p))
    from services import gamification_vibelogger as gv

    gv.reset_gamification_vibe_logger()
    yield p
    gv.reset_gamification_vibe_logger()


class TestGamificationVibeloggerIntegration:
    def test_corrupt_user_file_emits_warning(self, tmp_path, vibe_log_path):
        # Given: 破損した JSON ファイル
        # When: UserDataService.get_user_data
        # Then: WARNING（UserDataService.get_user_data）がログに含まれる
        uds = UserDataService(data_dir=str(tmp_path))
        uid = "badjson"
        fp = Path(uds._get_file_path(uid))
        fp.write_text("{ not json", encoding="utf-8")
        uds.get_user_data(uid)
        entries = _read_vibe_entries(vibe_log_path)
        assert _has_operation_level(entries, "UserDataService.get_user_data", "WARNING")

    def test_add_xp_emits_info(self, tmp_path, vibe_log_path):
        # Given: ユーザーデータと GamificationService
        # When: add_xp
        # Then: INFO（GamificationService.add_xp）
        uds = UserDataService(data_dir=str(tmp_path))
        uid = "xp"
        gs = GamificationService(uds)
        gains = {a: 1 for a in SIX_AXES}
        gains["scenario_id"] = "s1"
        gs.add_xp(uid, gains, "scenario_completion")
        entries = _read_vibe_entries(vibe_log_path)
        assert _has_operation_level(entries, "GamificationService.add_xp", "INFO")

    def test_award_badge_emits_info(self, tmp_path, vibe_log_path):
        # Given: BadgeService
        # When: award_badge（初回付与）
        # Then: INFO（BadgeService.award_badge）
        uds = UserDataService(data_dir=str(tmp_path))
        bs = BadgeService(uds)
        bs.award_badge("u1", "first_step")
        entries = _read_vibe_entries(vibe_log_path)
        assert _has_operation_level(entries, "BadgeService.award_badge", "INFO")

    def test_generate_quiz_llm_failure_emits_warning(self, vibe_log_path):
        # Given: LLM が例外を送出
        # When: generate_quiz
        # Then: WARNING（QuizService.generate_quiz）
        llm = MagicMock()
        llm.generate_quiz_content.side_effect = RuntimeError("llm down")
        svc = QuizService(llm_service=llm)
        svc.generate_quiz([])
        entries = _read_vibe_entries(vibe_log_path)
        assert _has_operation_level(entries, "QuizService.generate_quiz", "WARNING")
        assert any("failed" in e.get("message", "").lower() for e in entries)

    def test_on_scenario_feedback_emits_info(self, tmp_path, vibe_log_path, monkeypatch):
        # Given: フックの依存をテスト用に差し替え
        # When: gamification_hooks.on_scenario_feedback
        # Then: INFO（gamification_hooks.on_scenario_feedback）
        uds_root = tmp_path / "ud"
        uds_root.mkdir()

        def make_uds(*a, **kw):
            return UserDataService(data_dir=str(uds_root))

        monkeypatch.setattr("services.gamification_hooks._get_user_id", lambda: "hook-user")
        monkeypatch.setattr("services.gamification_hooks.UserDataService", make_uds)

        from services import gamification_hooks as gh

        scores = {a: 40 for a in SIX_AXES}
        gh.on_scenario_feedback(
            scores,
            "scenario_hook_1",
            scenario_data={"difficulty": "beginner"},
            session_id="unique-session-vibe-1",
        )
        entries = _read_vibe_entries(vibe_log_path)
        assert _has_operation_level(entries, "gamification_hooks.on_scenario_feedback", "INFO")
