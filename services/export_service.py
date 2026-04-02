"""
会話履歴・学習レポートのエクスポート（CSV / JSON）
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, Union


class ExportService:
    """会話と学習データを文字列形式でエクスポートする。対象が空でも例外を出さない。"""

    CSV_COLUMNS = ("user_id", "role", "content")

    def export_conversations_csv(self, user_id: str, history: list) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(list(self.CSV_COLUMNS))
        uid = user_id or ""
        for turn in history or []:
            if isinstance(turn, dict):
                role = str(turn.get("role", ""))
                content = str(turn.get("content", ""))
            else:
                role = ""
                content = str(turn)
            writer.writerow([uid, role, content])
        return buf.getvalue()

    def export_conversations_json(self, user_id: str, history: list) -> str:
        payload = {
            "user_id": user_id or "",
            "conversations": list(history or []),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def export_learning_report(self, user_id: str, user_data: Union[dict, None]) -> dict:
        """
        Returns:
            summary, skill_xp, badges, scenarios_completed を含む dict
        """
        try:
            ud: Dict[str, Any] = user_data if isinstance(user_data, dict) else {}
            summary = self._build_summary(user_id or "", ud)

            skill_xp = ud.get("skill_xp")
            if not isinstance(skill_xp, dict):
                skill_xp = {}

            badges = ud.get("badges")
            if not isinstance(badges, dict):
                badges = {}

            scenarios_completed = self._scenarios_completed_count(ud)

            return {
                "summary": summary,
                "skill_xp": skill_xp,
                "badges": badges,
                "scenarios_completed": scenarios_completed,
            }
        except Exception:
            return {
                "summary": "",
                "skill_xp": {},
                "badges": {},
                "scenarios_completed": 0,
            }

    def _build_summary(self, user_id: str, ud: Dict[str, Any]) -> str:
        if not ud:
            return f"ユーザー {user_id}: 学習データはまだありません。"
        parts = [f"ユーザー {user_id}"]
        stats = ud.get("stats") if isinstance(ud.get("stats"), dict) else {}
        if stats:
            total = stats.get("total_scenarios_completed")
            if isinstance(total, int):
                parts.append(f"完了シナリオ数 {total}")
        return " / ".join(parts)

    def _scenarios_completed_count(self, ud: Dict[str, Any]) -> int:
        stats = ud.get("stats")
        if isinstance(stats, dict):
            t = stats.get("total_scenarios_completed")
            if isinstance(t, int):
                return t
        sc = ud.get("scenario_completions")
        if isinstance(sc, dict):
            return len(sc)
        return 0
