"""
キャラクター画像用プロフィール・プロンプト・ローカルキャッシュ
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Union


class CharacterImageService:
    """シナリオデータからプロフィールを組み立て、キャッシュキーと画像バイトを管理する。"""

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir is not None else Path(".character_image_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get_character_profile(self, scenario_data: Any) -> dict:
        """
        Returns:
            name, age, gender, appearance_prompt
        """
        sd = scenario_data if isinstance(scenario_data, dict) else {}
        char = sd.get("character") if isinstance(sd.get("character"), dict) else {}
        if not char and isinstance(sd.get("npc"), dict):
            char = sd["npc"]

        return {
            "name": str(char.get("name", sd.get("character_name", "")) or ""),
            "age": char.get("age", sd.get("age", "")),
            "gender": str(char.get("gender", sd.get("gender", "")) or ""),
            "appearance_prompt": str(
                char.get("appearance_prompt", sd.get("appearance_prompt", "")) or ""
            ),
        }

    def build_consistent_prompt(self, profile: dict, emotion: str) -> str:
        p = profile or {}
        name = str(p.get("name", "") or "")
        age = p.get("age", "")
        gender = str(p.get("gender", "") or "")
        appearance = str(p.get("appearance_prompt", "") or "")
        em = str(emotion or "").strip()

        parts = [name, f"age:{age}" if age != "" else "", gender, appearance, f"emotion:{em}" if em else ""]
        joined = ", ".join(x for x in parts if x)
        return joined if joined else "character, neutral"

    def get_profile_hash(self, profile: dict) -> str:
        canonical = json.dumps(profile or {}, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _cache_path(self, profile_hash: str, emotion: str) -> Path:
        safe_e = (emotion or "neutral").replace("/", "_").replace("\\", "_")[:80]
        return self._cache_dir / f"{profile_hash}_{safe_e}.bin"

    def get_cached_image(self, profile_hash: str, emotion: str) -> Optional[bytes]:
        path = self._cache_path(profile_hash, emotion)
        if not path.is_file():
            return None
        return path.read_bytes()

    def cache_image(self, profile_hash: str, emotion: str, image_data: bytes) -> None:
        path = self._cache_path(profile_hash, emotion)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_data)
