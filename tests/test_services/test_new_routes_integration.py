"""
新規 API ルートの統合テスト（Flask test client）

注: アプリ実装では /api/summary/generate と /api/export/* は JSON ボディのため POST。
    仕様で GET とある場合は実装（POST）に合わせて検証する。
"""
import json

import pytest

from services.gamification_constants import SIX_AXES


class TestNewRoutesIntegration:
    """9 エンドポイント: 200 と期待する JSON / Content-Type"""

    def test_post_summary_generate_has_summary_and_key_points(self, client):
        # When（実ルートは POST）
        response = client.post(
            "/api/summary/generate",
            json={
                "history": [{"role": "user", "content": "test"}],
                "mode": "scenario",
            },
        )
        # Then
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        assert "summary" in data
        assert "key_points" in data

    def test_get_analytics_practice_stats(self, client):
        response = client.get("/api/analytics/practice-stats")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_time_minutes" in data
        assert "session_count" in data

    def test_get_analytics_skill_progress_has_six_axes(self, client):
        response = client.get("/api/analytics/skill-progress")
        assert response.status_code == 200
        data = response.get_json()
        for axis in SIX_AXES:
            assert axis in data

    def test_get_analytics_weakness_is_list(self, client):
        response = client.get("/api/analytics/weakness")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_post_export_csv_content_type(self, client):
        response = client.post("/api/export/csv", json={"history": []})
        assert response.status_code == 200
        ct = response.content_type or ""
        assert "text/csv" in ct

    def test_post_export_json_content_type(self, client):
        response = client.post("/api/export/json", json={"history": []})
        assert response.status_code == 200
        ct = response.content_type or ""
        assert "application/json" in ct
        parsed = json.loads(response.data.decode("utf-8"))
        assert "user_id" in parsed
        assert "conversations" in parsed

    def test_get_tutorial_steps_scenario(self, client):
        response = client.get("/api/tutorial/steps?mode=scenario")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_get_tutorial_faq(self, client):
        response = client.get("/api/tutorial/faq")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    def test_post_three_way_join(self, client):
        response = client.post("/api/three-way/join", json={})
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("joined") is True
