"""
三者（A / B / ユーザー）観戦・参加会話の順番管理
"""

from __future__ import annotations

from typing import Any, Dict, List


class ThreeWayConversationService:
    """
    ユーザーが AI A・B との三者会話に参加するときのターン順と履歴を扱う。
    """

    DEFAULT_TURN_ORDER = ["A", "B", "user"]
    ERR_ALREADY_JOINED = "already_joined"

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def join_conversation(self, user_id: str, watch_history: list) -> dict:
        """
        Returns:
            成功: {"joined": True, "turn_order": list[str]}
            重複: {"joined": False, "error": str, "turn_order": None}
        """
        if user_id in self._sessions:
            return {
                "joined": False,
                "error": self.ERR_ALREADY_JOINED,
                "turn_order": None,
            }

        turn_order = list(self.DEFAULT_TURN_ORDER)
        self._sessions[user_id] = {
            "turn_order": turn_order,
            "watch_history": list(watch_history or []),
        }
        return {"joined": True, "turn_order": turn_order}

    def get_next_speaker(self, history: list, turn_order: List[str]) -> str:
        """
        Returns:
            "A" | "B" | "user" のいずれか（turn_order の次の話者）
        """
        order = list(turn_order) if turn_order else list(self.DEFAULT_TURN_ORDER)
        if not order:
            return "user"

        if not history:
            return order[0]

        last = history[-1]
        if not isinstance(last, dict):
            return order[0]

        role = last.get("role")
        if role not in order:
            return order[0]

        idx = order.index(role)
        return order[(idx + 1) % len(order)]

    def add_user_message(
        self,
        history: list,
        message: str,
        turn_order: List[str],
    ) -> dict:
        """
        Returns:
            {"next_speaker": str, "updated_history": list}
        """
        h: List[dict] = [
            dict(x) if isinstance(x, dict) else {"role": "unknown", "content": str(x)}
            for x in (history or [])
        ]
        h.append({"role": "user", "content": message})
        next_s = self.get_next_speaker(h, turn_order)
        return {"next_speaker": next_s, "updated_history": h}

    def leave_conversation(self, user_id: str) -> dict:
        """
        Returns:
            {"left": bool, "mode": str}
        """
        self._sessions.pop(user_id, None)
        return {"left": True, "mode": "watch"}
