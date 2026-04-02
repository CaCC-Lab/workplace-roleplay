"""
TutorialService のユニットテスト（tmpdir で永続化）
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.tutorial_service import TutorialService


@pytest.fixture
def svc(tmpdir):
    return TutorialService(data_dir=str(tmpdir))


class TestGetTutorialSteps:
    def test_scenario_steps_include_step_title_description(self, svc):
        # Given: シナリオモード
        # When: ステップ一覧を取得
        steps = svc.get_tutorial_steps("scenario")

        # Then: 各要素に step / title / description / target_element がある
        assert isinstance(steps, list)
        assert len(steps) >= 1
        for item in steps:
            assert "step" in item
            assert "title" in item
            assert "description" in item
            assert "target_element" in item
            assert isinstance(item["step"], int)
            assert isinstance(item["title"], str)
            assert len(item["title"]) > 0
            assert isinstance(item["description"], str)
            assert len(item["description"]) > 0

    def test_all_three_modes_return_steps(self, svc):
        # Given: scenario / chat / watch
        # When: それぞれ取得
        for mode in ("scenario", "chat", "watch"):
            steps = svc.get_tutorial_steps(mode)
            # Then: 空でないリスト
            assert isinstance(steps, list)
            assert len(steps) >= 1
            assert all("step" in s for s in steps)


class TestProgressAndMarkComplete:
    def test_mark_complete_updates_progress(self, tmpdir):
        # Given: 一時ディレクトリ上のサービスとユーザー
        svc = TutorialService(data_dir=str(tmpdir))
        uid = "user-progress-1"

        # When: シナリオのステップ1を完了にする
        r = svc.mark_step_complete(uid, "scenario", 1)

        # Then: 完了結果と progress に反映される（シナリオは複数ステップなので次ステップあり）
        assert r["completed"] is True
        assert r["next_step"] == 2

        prog = svc.get_user_progress(uid)
        assert "scenario" in prog
        assert 1 in prog["scenario"]["completed_steps"]
        assert prog["scenario"]["total_steps"] == len(svc.get_tutorial_steps("scenario"))


class TestFaq:
    def test_faq_non_empty_with_fields(self, svc):
        # When: FAQ を取得
        faq = svc.get_faq()

        # Then: 空でなく question / answer / category を含む
        assert isinstance(faq, list)
        assert len(faq) >= 1
        for row in faq:
            assert "question" in row
            assert "answer" in row
            assert "category" in row
            assert isinstance(row["question"], str)
            assert isinstance(row["answer"], str)
            assert isinstance(row["category"], str)


class TestFirstVisit:
    def test_first_visit_true_then_false(self, tmpdir):
        # Given: 同一 tmpdir・同一ユーザー
        svc = TutorialService(data_dir=str(tmpdir))
        uid = "user-visit-1"

        # When: 初回・2回目
        first = svc.is_first_visit(uid)
        second = svc.is_first_visit(uid)

        # Then: 初回 True、2回目以降 False
        assert first is True
        assert second is False
