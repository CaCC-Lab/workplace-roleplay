"""
Supabase 上のユーザーデータ（user_data テーブル想定）
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.gamification_constants import utc_now_iso
from services.user_data_service import UserDataService


class SupabaseUserDataService(UserDataService):
    """user_id + data(JSON) を UPSERT で永続化する UserDataService。"""

    TABLE = "user_data"

    def __init__(self, client: Any, data_dir: Optional[str] = None) -> None:
        super().__init__(data_dir=data_dir)
        self._client = client

    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        try:
            res = (
                self._client.table(self.TABLE)
                .select("data")
                .eq("user_id", user_id.strip())
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None)
            if isinstance(rows, list) and len(rows) > 0:
                row = rows[0]
                if isinstance(row, dict):
                    d = row.get("data")
                    if isinstance(d, dict):
                        return d
            return self._create_default_data(user_id)
        except Exception:
            return self._create_default_data(user_id)

    def save_user_data(self, user_id: str, data: Dict[str, Any]) -> None:
        if data is None or not isinstance(data, dict):
            raise TypeError("data must be a dict")
        payload = dict(data)
        payload["user_id"] = user_id
        payload["updated_at"] = utc_now_iso()
        if "created_at" not in payload:
            payload["created_at"] = payload["updated_at"]
        row = {
            "user_id": user_id,
            "data": payload,
        }
        self._client.table(self.TABLE).upsert(row).execute()
