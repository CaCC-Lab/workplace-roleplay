"""
CharacterImageService のユニットテスト（tmpdir でキャッシュ）
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.character_image_service import CharacterImageService


@pytest.fixture
def svc(tmpdir):
    return CharacterImageService(cache_dir=str(tmpdir))


def _scenario_a():
    return {
        "character": {
            "name": "山田",
            "age": 32,
            "gender": "female",
            "appearance_prompt": "黒髪ショート",
        }
    }


def _scenario_b():
    return {
        "character": {
            "name": "佐藤",
            "age": 28,
            "gender": "male",
            "appearance_prompt": "眼鏡",
        }
    }


class TestCharacterProfile:
    def test_profile_includes_name_age_gender(self, svc):
        p = svc.get_character_profile(_scenario_a())
        assert p["name"] == "山田"
        assert p["age"] == 32
        assert p["gender"] == "female"
        assert "appearance_prompt" in p


class TestProfileHash:
    def test_same_profile_same_hash(self, svc):
        p1 = svc.get_character_profile(_scenario_a())
        p2 = svc.get_character_profile(_scenario_a())
        assert svc.get_profile_hash(p1) == svc.get_profile_hash(p2)

    def test_different_profile_different_hash(self, svc):
        h1 = svc.get_profile_hash(svc.get_character_profile(_scenario_a()))
        h2 = svc.get_profile_hash(svc.get_character_profile(_scenario_b()))
        assert h1 != h2


class TestConsistentPrompt:
    def test_prompt_contains_profile_and_emotion(self, svc):
        profile = svc.get_character_profile(_scenario_a())
        text = svc.build_consistent_prompt(profile, "happy")
        assert "山田" in text
        assert "female" in text or "32" in text
        assert "emotion:happy" in text


class TestCache:
    def test_cache_roundtrip_same_bytes(self, svc):
        profile = svc.get_character_profile(_scenario_a())
        h = svc.get_profile_hash(profile)
        data = b"\x89PNG fake"
        svc.cache_image(h, "neutral", data)
        assert svc.get_cached_image(h, "neutral") == data

    def test_cache_miss_returns_none(self, svc):
        assert svc.get_cached_image("no_such_hash", "neutral") is None
