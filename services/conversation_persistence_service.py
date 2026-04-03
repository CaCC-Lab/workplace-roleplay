"""
会話履歴の永続化（Supabase テーブル想定）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ConversationPersistenceService:
    TABLE = "conversations"

    def __init__(self, client: Any) -> None:
        self._client = client

    def save_conversation(
        self,
        user_id: str,
        mode: str,
        history: List[Any],
        scenario_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "user_id": user_id,
            "mode": mode,
            "history": history or [],
        }
        if scenario_id is not None:
            row["scenario_id"] = scenario_id
        res = self._client.table(self.TABLE).insert(row).execute()
        data = getattr(res, "data", None)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            rid = data[0].get("id")
            if rid is not None:
                return {"id": rid}
        return {"id": None}

    def get_conversations(self, user_id: str, mode: str, limit: int) -> List[Dict[str, Any]]:
        lim = max(1, int(limit))
        res = (
            self._client.table(self.TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("mode", mode)
            .limit(lim)
            .execute()
        )
        data = getattr(res, "data", None)
        return list(data) if isinstance(data, list) else []

    def search_conversations(self, user_id: str, keyword: str) -> List[Dict[str, Any]]:
        kw = (keyword or "").strip()
        res = self._client.table(self.TABLE).select("*").eq("user_id", user_id).execute()
        data = getattr(res, "data", None)
        if not isinstance(data, list):
            return []
        if not kw:
            return list(data)
        out: List[Dict[str, Any]] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            blob = str(row.get("history", "")) + str(row.get("mode", "")) + str(row.get("scenario_id", ""))
            if kw.lower() in blob.lower():
                out.append(row)
        return out
