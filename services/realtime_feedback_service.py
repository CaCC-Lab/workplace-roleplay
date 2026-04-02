"""
リアルタイム会話フィードバック（シナリオ練習向け）
"""

from __future__ import annotations

import json
import re
from typing import Any, List, Optional

from langchain_core.messages import HumanMessage


def _extract_text_from_llm_response(response: Any) -> str:
    if response is None:
        return ""
    if hasattr(response, "content"):
        c = getattr(response, "content", "")
        return c if isinstance(c, str) else str(c)
    return str(response)


class RealtimeFeedbackService:
    """メッセージ単位のフィードバック候補を生成する。LLM 失敗時は例外を出さない。"""

    def __init__(self, llm: Optional[Any] = None) -> None:
        self._llm = llm

    def analyze_message(
        self,
        user_message: str,
        history: list,
        scenario_context: Any,
    ) -> dict:
        """
        Returns:
            has_feedback: bool
            feedback_type: str | None
            suggestion: str
            alternatives: list[str]
        """
        msg = (user_message or "").strip()
        if not msg:
            return {
                "has_feedback": False,
                "feedback_type": None,
                "suggestion": "",
                "alternatives": [],
            }

        try:
            if self._llm is None:
                return self._empty_analyze()

            prompt = self._build_analyze_prompt(msg, history or [], scenario_context)
            raw = _extract_text_from_llm_response(
                self._llm.invoke([HumanMessage(content=prompt)])
            )
            return self._parse_analyze_response(raw)
        except Exception:
            return self._empty_analyze()

    def generate_alternatives(self, user_message: str, history: list) -> List[str]:
        """代替表現を最大3件まで返す。"""
        msg = (user_message or "").strip()
        if not msg:
            return []

        try:
            if self._llm is None:
                return []

            prompt = (
                "次のユーザー発言に対し、より適切な言い換え候補を日本語で最大3つ、"
                'JSON配列のみで返してください。例: ["案1","案2"]\n\n'
                f"発言: {msg}\n"
            )
            if history:
                lines = []
                for turn in history[-6:]:
                    if isinstance(turn, dict):
                        lines.append(f"{turn.get('role', '')}: {turn.get('content', '')}")
                prompt += "直近の会話:\n" + "\n".join(lines)

            raw = _extract_text_from_llm_response(
                self._llm.invoke([HumanMessage(content=prompt)])
            )
            return self._parse_string_list(raw, max_items=3)
        except Exception:
            return []

    def should_provide_feedback(self, history: list, interval: int = 3) -> bool:
        """
        ユーザー発話の累計が interval の倍数のとき True（例: interval=3 で 3, 6, 9 回目）。
        """
        if interval < 1:
            return False
        n = sum(1 for h in (history or []) if isinstance(h, dict) and h.get("role") == "user")
        return n > 0 and n % interval == 0

    def _build_analyze_prompt(self, user_message: str, history: list, scenario_context: Any) -> str:
        ctx = scenario_context
        if isinstance(ctx, dict):
            ctx_str = json.dumps(ctx, ensure_ascii=False)
        else:
            ctx_str = str(ctx) if ctx is not None else ""

        lines = []
        for turn in history[-10:]:
            if isinstance(turn, dict):
                lines.append(f"{turn.get('role', '')}: {turn.get('content', '')}")

        return (
            "あなたは職場コミュニケーションのコーチです。次のJSONだけを返してください。\n"
            '{"has_feedback":true/false,"feedback_type":"stringまたはnull",'
            '"suggestion":"string","alternatives":["最大3つ"]}\n\n'
            f"シナリオ文脈: {ctx_str}\n"
            f"ユーザー最新発言: {user_message}\n"
            "会話履歴:\n" + ("\n".join(lines) if lines else "(なし)")
        )

    def _parse_analyze_response(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            return self._empty_analyze()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return self._empty_analyze()

        if not isinstance(data, dict):
            return self._empty_analyze()

        has_feedback = bool(data.get("has_feedback"))
        ft = data.get("feedback_type")
        feedback_type = str(ft) if ft is not None else None
        suggestion = str(data.get("suggestion") or "")
        alts = data.get("alternatives") or []
        if not isinstance(alts, list):
            alts = []
        alts_s = [str(x) for x in alts[:3]]

        return {
            "has_feedback": has_feedback,
            "feedback_type": feedback_type,
            "suggestion": suggestion,
            "alternatives": alts_s,
        }

    def _parse_string_list(self, text: str, max_items: int) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [str(x) for x in data[:max_items]]
        return []

    def _empty_analyze(self) -> dict:
        return {
            "has_feedback": False,
            "feedback_type": None,
            "suggestion": "",
            "alternatives": [],
        }
