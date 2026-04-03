"""
SupabaseUserDataService のユニットテスト（Supabase クライアントは Mock）
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.gamification_constants import SIX_AXES
from services.supabase_user_data_service import SupabaseUserDataService


@pytest.fixture
def mock_table():
    return MagicMock()


@pytest.fixture
def mock_client(mock_table):
    c = MagicMock()
    c.table.return_value = mock_table
    return c


class TestGetUserData:
    def test_fetch_success_returns_db_payload(self, mock_client, mock_table):
        stored = {"user_id": "u1", "skill_xp": {a: 10 for a in SIX_AXES}}
        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"data": stored}]
        )
        svc = SupabaseUserDataService(mock_client)
        out = svc.get_user_data("u1")
        assert out == stored
        mock_client.table.assert_called_with("user_data")

    def test_unregistered_returns_default_structure(self, mock_client, mock_table):
        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        svc = SupabaseUserDataService(mock_client)
        out = svc.get_user_data("new-user")
        assert out["user_id"] == "new-user"
        assert isinstance(out.get("skill_xp"), dict)
        assert all(axis in out["skill_xp"] for axis in SIX_AXES)

    def test_save_then_get_matches(self, mock_client, mock_table):
        """UPSERT 後に同じ内容が select で返る想定"""
        saved = {}

        def upsert_exec():
            row = mock_table.upsert.call_args[0][0]
            saved["payload"] = row
            return MagicMock()

        def select_exec():
            if "payload" not in saved:
                return MagicMock(data=[])
            d = saved["payload"]["data"]
            return MagicMock(data=[{"data": d}])

        mock_table.select.return_value.eq.return_value.limit.return_value.execute.side_effect = select_exec
        mock_table.upsert.return_value.execute.side_effect = upsert_exec

        svc = SupabaseUserDataService(mock_client)
        default = svc.get_user_data("persist")
        default["stats"] = default.get("stats") or {}
        default["stats"]["total_scenarios_completed"] = 3

        svc.save_user_data("persist", default)
        got = svc.get_user_data("persist")
        assert got["stats"]["total_scenarios_completed"] == 3


class TestSaveUserData:
    def test_rejects_none_data(self, mock_client):
        svc = SupabaseUserDataService(mock_client)
        with pytest.raises(TypeError, match="data must be a dict"):
            svc.save_user_data("u1", None)  # type: ignore[arg-type]
