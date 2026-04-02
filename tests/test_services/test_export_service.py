"""
ExportService のユニットテスト
"""
import csv
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.export_service import ExportService


@pytest.fixture
def svc():
    return ExportService()


class TestExportCsv:
    def test_csv_contains_header_and_data_rows(self, svc):
        # Given: 会話履歴
        uid = "user-1"
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

        # When
        csv_text = svc.export_conversations_csv(uid, history)

        # Then: ヘッダとデータ行
        rows = list(csv.reader(io.StringIO(csv_text)))
        assert rows[0] == ["user_id", "role", "content"]
        assert rows[1] == ["user-1", "user", "hello"]
        assert rows[2] == ["user-1", "assistant", "hi"]

    def test_empty_history_csv_has_header_only(self, svc):
        csv_text = svc.export_conversations_csv("u", [])
        rows = list(csv.reader(io.StringIO(csv_text)))
        assert len(rows) == 1
        assert rows[0] == ["user_id", "role", "content"]


class TestExportJson:
    def test_json_is_parseable(self, svc):
        history = [{"role": "user", "content": "x"}]
        js = svc.export_conversations_json("uid-json", history)
        data = json.loads(js)
        assert data["user_id"] == "uid-json"
        assert data["conversations"] == history

    def test_empty_history_json_parseable(self, svc):
        js = svc.export_conversations_json("u-empty", [])
        data = json.loads(js)
        assert data["conversations"] == []


class TestLearningReport:
    def test_learning_report_has_required_keys(self, svc):
        user_data = {
            "skill_xp": {"axis1": 10},
            "badges": {"earned": ["b1"]},
            "stats": {"total_scenarios_completed": 2},
        }
        r = svc.export_learning_report("u1", user_data)
        assert "summary" in r
        assert "skill_xp" in r
        assert "badges" in r
        assert "scenarios_completed" in r
        assert r["skill_xp"]["axis1"] == 10
        assert r["badges"]["earned"] == ["b1"]
        assert r["scenarios_completed"] == 2

    def test_no_export_target_does_not_raise(self, svc):
        # Given: 空・None・不正に近い入力
        assert svc.export_conversations_csv("", None) is not None
        assert json.loads(svc.export_conversations_json("", None))["conversations"] == []

        r = svc.export_learning_report("x", None)
        assert r["scenarios_completed"] == 0
        assert isinstance(r["summary"], str)

        r2 = svc.export_learning_report("y", {})
        assert r2["skill_xp"] == {}
        assert r2["badges"] == {}
