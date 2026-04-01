"""
チュートリアル・ヘルプ（ステップ案内・進捗・FAQ）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

_MODES = ("scenario", "chat", "watch")

_TUTORIAL_DATA: Dict[str, List[dict]] = {
    "scenario": [
        {
            "step": 1,
            "title": "シナリオを選ぶ",
            "description": "一覧から練習したい職場シナリオを選択します。",
            "target_element": "#scenario-list",
        },
        {
            "step": 2,
            "title": "役割を確認する",
            "description": "設定された状況と自分の役割を読み、会話を始めます。",
            "target_element": "#scenario-role",
        },
        {
            "step": 3,
            "title": "フィードバックを見る",
            "description": "終了後にフィードバックで改善点を確認します。",
            "target_element": "#scenario-feedback",
        },
    ],
    "chat": [
        {
            "step": 1,
            "title": "雑談モードを開く",
            "description": "雑談練習画面に移動します。",
            "target_element": "#chat-mode",
        },
        {
            "step": 2,
            "title": "メッセージを送る",
            "description": "相手役との会話を始めます。",
            "target_element": "#chat-input",
        },
    ],
    "watch": [
        {
            "step": 1,
            "title": "観戦を開始",
            "description": "観戦モードでAI同士の会話を開始します。",
            "target_element": "#watch-start",
        },
        {
            "step": 2,
            "title": "会話を観察",
            "description": "流れを見ながら学びのポイントを拾います。",
            "target_element": "#watch-panel",
        },
    ],
}

_FAQ: List[dict] = [
    {
        "question": "シナリオと雑談の違いは何ですか？",
        "answer": "シナリオは職場の状況が決まったロールプレイ、雑談は自由な会話練習です。",
        "category": "モード",
    },
    {
        "question": "会話履歴は保存されますか？",
        "answer": "セッション中は保存され、学習履歴から確認できる場合があります。",
        "category": "データ",
    },
]


def _default_progress_skeleton() -> dict:
    out: Dict[str, dict] = {}
    for m in _MODES:
        total = len(_TUTORIAL_DATA[m])
        out[m] = {"completed_steps": [], "total_steps": total}
    return out


class TutorialService:
    """チュートリアルステップ・進捗・FAQ・初回訪問フラグを扱う。"""

    def __init__(self, data_dir: Optional[Union[str, Path]] = None) -> None:
        self._data_dir = Path(data_dir) if data_dir is not None else Path(".tutorial_data")
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def get_tutorial_steps(self, mode: str) -> List[dict]:
        m = mode if mode in _TUTORIAL_DATA else "scenario"
        # 参照渡しを避けるためコピー
        return [dict(x) for x in _TUTORIAL_DATA[m]]

    def mark_step_complete(self, user_id: str, mode: str, step: int) -> dict:
        valid_steps = {s["step"] for s in self.get_tutorial_steps(mode)}
        if step not in valid_steps:
            return {"completed": False, "next_step": None}

        prog = self._load_progress(user_id)
        key = mode if mode in _MODES else "scenario"
        done = list(prog[key]["completed_steps"])
        if step not in done:
            done.append(step)
            done.sort()
        prog[key]["completed_steps"] = done
        self._save_progress(user_id, prog)

        remaining = sorted(valid_steps - set(done))
        next_step = remaining[0] if remaining else None
        return {"completed": True, "next_step": next_step}

    def get_user_progress(self, user_id: str) -> dict:
        return self._load_progress(user_id)

    def get_faq(self) -> List[dict]:
        return [dict(x) for x in _FAQ]

    def is_first_visit(self, user_id: str) -> bool:
        flag = self._data_dir / f".first_visit_{self._safe_id(user_id)}"
        if flag.exists():
            return False
        flag.touch()
        return True

    def _safe_id(self, user_id: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)[:200] or "anonymous"

    def _progress_path(self, user_id: str) -> Path:
        return self._data_dir / f"progress_{self._safe_id(user_id)}.json"

    def _load_progress(self, user_id: str) -> dict:
        path = self._progress_path(user_id)
        if not path.exists():
            return _default_progress_skeleton()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return _default_progress_skeleton()
        base = _default_progress_skeleton()
        for m in _MODES:
            if isinstance(data.get(m), dict):
                entry = data[m]
                steps = entry.get("completed_steps", [])
                if isinstance(steps, list):
                    base[m]["completed_steps"] = sorted({int(x) for x in steps if isinstance(x, int)})
        return base

    def _save_progress(self, user_id: str, progress: dict) -> None:
        path = self._progress_path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
