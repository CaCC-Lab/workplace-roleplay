"""
ユーザーデータのJSON永続化（ゲーミフィケーション）
"""

from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any, Dict, Optional

from services.gamification_constants import SIX_AXES, utc_now_iso


class UserDataService:
    """JSONファイルベースのユーザーデータ永続化サービス"""

    DATA_DIR = "user_data"

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self._data_dir = data_dir if data_dir is not None else self.DATA_DIR

    def _get_file_path(self, user_id: str) -> str:
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", user_id.strip())
        if not safe:
            safe = "user"
        return os.path.join(self._data_dir, f"{safe}.json")

    def _ensure_dir(self) -> None:
        os.makedirs(self._data_dir, exist_ok=True)

    def _create_default_data(self, user_id: str) -> Dict[str, Any]:
        now = utc_now_iso()
        return {
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "skill_xp": {axis: 0 for axis in SIX_AXES},
            "xp_history": [],
            "scenario_completions": {},
            "unlock_status": {
                "beginner": True,
                "intermediate": False,
                "advanced": False,
            },
            "quests": {"daily": [], "weekly": []},
            "badges": {"earned": []},
            "quiz_history": [],
            "stats": {
                "total_scenarios_completed": 0,
                "total_quizzes_answered": 0,
                "total_quizzes_correct": 0,
                "total_journal_entries": 0,
                "consecutive_days": 0,
                "last_activity_date": None,
                "unique_scenarios_tried": 0,
            },
        }

    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """ユーザーデータを読み込む。存在しない/破損時はデフォルト値を返す"""
        self._ensure_dir()
        path = self._get_file_path(user_id)
        if not os.path.isfile(path):
            return self._create_default_data(user_id)
        try:
            with open(path, encoding="utf-8") as f:
                raw = f.read()
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("root must be object")
            return data
        except (json.JSONDecodeError, OSError, ValueError, TypeError):
            try:
                from services.gamification_vibelogger import get_gamification_vibe_logger

                get_gamification_vibe_logger().warning(
                    operation="UserDataService.get_user_data",
                    message="Corrupt or invalid user JSON; recreating defaults",
                    context={"user_id": user_id, "path": path},
                )
            except Exception:
                pass
            bak = path + ".bak"
            try:
                if os.path.isfile(path):
                    shutil.move(path, bak)
            except OSError:
                pass
            return self._create_default_data(user_id)

    def save_user_data(self, user_id: str, data: Dict[str, Any]) -> None:
        """ユーザーデータをJSONファイルに保存する"""
        if data is None or not isinstance(data, dict):
            raise TypeError("data must be a dict")
        self._ensure_dir()
        path = self._get_file_path(user_id)
        data = dict(data)
        data["user_id"] = user_id
        data["updated_at"] = utc_now_iso()
        if "created_at" not in data:
            data["created_at"] = data["updated_at"]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
