"""
会話要約サービス（シナリオ / 雑談 / 観戦）
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage

_VALID_MODES = frozenset({"scenario", "chat", "watch"})


def _extract_text_from_llm_response(response: Any) -> str:
    if response is None:
        return ""
    if hasattr(response, "content"):
        c = getattr(response, "content", "")
        return c if isinstance(c, str) else str(c)
    return str(response)


class SummaryService:
    """会話履歴から要約を生成する。LLM 失敗時はフォールバック要約を返す。"""

    def __init__(self, llm: Optional[Any] = None) -> None:
        """
        Args:
            llm: LangChain 互換（invoke(messages) を持つ）モデル。None の場合はフォールバックのみ。
        """
        self._llm = llm

    def generate_summary(self, history: list, mode: str) -> dict:
        """
        Args:
            history: [{"role": str, "content": str}, ...]
            mode: "scenario" | "chat" | "watch"

        Returns:
            {"summary": str, "key_points": list[str], "learning_points": list[str]}
        """
        if not history:
            return {"summary": "", "key_points": [], "learning_points": []}

        m = mode if mode in _VALID_MODES else "scenario"

        try:
            if self._llm is None:
                return self._fallback_summary(history, m)

            prompt = self._build_user_prompt(history, m)
            messages = [HumanMessage(content=prompt)]
            raw = _extract_text_from_llm_response(self._llm.invoke(messages))
            return self._parse_llm_text(raw, history, m)
        except Exception:
            return self._fallback_summary(history, m)

    def _build_user_prompt(self, history: list, mode: str) -> str:
        lines = []
        for turn in history:
            role = turn.get("role", "")
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")
        joined = "\n".join(lines)
        label = {"scenario": "シナリオロールプレイ", "chat": "雑談", "watch": "観戦モード"}[mode]
        return (
            f"以下は{label}の会話ログです。JSONのみで返してください。"
            f'形式: {{"summary":"文字列","key_points":["..."],"learning_points":["..."]}}\n\n'
            f"{joined}"
        )

    def _parse_llm_text(self, text: str, history: list, mode: str) -> dict:
        text = (text or "").strip()
        if not text:
            return self._fallback_summary(history, mode)
        # ```json ... ``` を剥がす
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return self._fallback_summary(history, mode)

        if not isinstance(data, dict):
            return self._fallback_summary(history, mode)

        summary = str(data.get("summary", "") or "")
        kp = data.get("key_points") or []
        lp = data.get("learning_points") or []
        if not isinstance(kp, list):
            kp = []
        if not isinstance(lp, list):
            lp = []
        kp_s = [str(x) for x in kp]
        lp_s = [str(x) for x in lp]

        if not summary and not kp_s and not lp_s:
            return self._fallback_summary(history, mode)

        return {"summary": summary, "key_points": kp_s, "learning_points": lp_s}

    def _fallback_summary(self, history: list, mode: str) -> dict:
        n = len(history)
        label = {"scenario": "シナリオ", "chat": "雑談", "watch": "観戦"}[mode]
        snippet = []
        for turn in history[-3:]:
            snippet.append(f"{turn.get('role', '?')}: {str(turn.get('content', ''))[:120]}")
        preview = " / ".join(snippet) if snippet else ""
        return {
            "summary": f"[フォールバック] {label}モードの会話{n}件。{preview}",
            "key_points": ["LLM要約を利用できなかったため簡易要約を表示しています"],
            "learning_points": ["会話の振り返りと次回への改善点の整理が有効です"],
        }
