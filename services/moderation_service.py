"""
コンテンツモデレーション（不適切表現・ループ・話題関連性）
"""

from __future__ import annotations

import re
from typing import List, Optional


class ModerationService:
    """メッセージのチェック、ループ検出、話題関連性の判定を行う。"""

    DEFAULT_NG_WORDS = [
        "死ね",
        "殺す",
        "ばか",
        "あほ",
    ]
    LOOP_SUGGESTION = "元の話題に戻りましょう"
    REASON_INAPPROPRIATE = "inappropriate_word"

    def __init__(self, ng_words: Optional[List[str]] = None) -> None:
        self._ng_words = list(ng_words) if ng_words is not None else self.DEFAULT_NG_WORDS.copy()

    def check_message(self, text: str) -> dict:
        """
        Returns:
            {"allowed": bool, "reason": str|None, "filtered_text": str}
        """
        if text is None:
            text = ""
        filtered = text
        hit = False
        for word in sorted(self._ng_words, key=len, reverse=True):
            if word and word in filtered:
                hit = True
                filtered = filtered.replace(word, "*" * len(word))
        if hit:
            return {
                "allowed": False,
                "reason": self.REASON_INAPPROPRIATE,
                "filtered_text": filtered,
            }
        return {"allowed": True, "reason": None, "filtered_text": text}

    def detect_loop(self, history: list, threshold: int = 3) -> bool:
        """
        会話履歴のうち、末尾から連続する同一内容の user メッセージが
        threshold 回以上なら True（同一話題の繰り返しとみなす）。
        """
        if threshold < 1:
            return False
        user_contents: List[str] = []
        for turn in history or []:
            if not isinstance(turn, dict):
                continue
            if turn.get("role") != "user":
                continue
            user_contents.append(str(turn.get("content", "")))

        if len(user_contents) < threshold:
            return False

        last = user_contents[-1]
        run = 0
        for content in reversed(user_contents):
            if content == last:
                run += 1
            else:
                break
        return run >= threshold

    def check_relevance(self, message: str, topic: str) -> dict:
        """
        Returns:
            {"relevant": bool, "suggestion": str|None}
        """
        m = (message or "").strip()
        t = (topic or "").strip()
        if not t:
            return {"relevant": True, "suggestion": None}
        if self._is_relevant_to_topic(m, t):
            return {"relevant": True, "suggestion": None}
        return {"relevant": False, "suggestion": self.LOOP_SUGGESTION}

    def _is_relevant_to_topic(self, message: str, topic: str) -> bool:
        if topic in message:
            return True
        for part in re.split(r"[\s、。．,のをはが]+", topic):
            part = part.strip()
            if len(part) >= 2 and part in message:
                return True
        return False
