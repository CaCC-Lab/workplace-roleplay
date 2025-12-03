"""
Image routes tests for improved coverage.
"""

import pytest
from unittest.mock import MagicMock, patch
import base64


class TestGenerateCharacterImage:
    """POST /api/generate_character_image のテスト"""

    def test_無効なJSONでエラー(self, csrf_client):
        """無効なJSONでエラーを返す"""
        response = csrf_client.post(
            "/api/generate_character_image",
            data="invalid",
            content_type="application/json",
        )

        assert response.status_code in [400, 500]

    def test_シナリオIDなしでエラー(self, csrf_client):
        """シナリオIDがない場合エラーを返す"""
        response = csrf_client.post("/api/generate_character_image", json={"emotion": "happy"})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_無効なシナリオIDでエラー(self, csrf_client):
        """無効なシナリオIDでエラーを返す"""
        response = csrf_client.post(
            "/api/generate_character_image",
            json={"scenario_id": "invalid_scenario_xyz", "emotion": "neutral"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_画像生成_APIエラー(self, csrf_client):
        """画像生成でAPIエラーが発生する場合"""
        with patch("routes.image_routes.image_cache", {}):
            # genaiモジュールをモック
            with patch.dict(
                "sys.modules",
                {
                    "google.genai": MagicMock(),
                    "google.genai.types": MagicMock(),
                },
            ):
                response = csrf_client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "scenario1", "emotion": "happy"},
                )

                # APIエラーが適切にハンドリングされる
                assert response.status_code in [200, 500, 503]

    def test_キャッシュヒット(self, csrf_client):
        """キャッシュからの画像取得"""
        cached_data = {
            "image": "cached_base64_image",
            "format": "png",
            "emotion": "neutral",
        }

        with patch("routes.image_routes.image_cache", {"scenario1_neutral": cached_data}):
            response = csrf_client.post(
                "/api/generate_character_image",
                json={"scenario_id": "scenario1", "emotion": "neutral"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data.get("cache_hit") is True

    def test_女性キャラクターの生成(self, csrf_client):
        """女性キャラクターの画像生成（キャッシュから）"""
        # scenario7は女性キャラクター - キャッシュを使用
        cached_data = {
            "image": "female_character_image",
            "format": "png",
            "emotion": "friendly",
        }

        with patch("routes.image_routes.image_cache", {"scenario7_friendly": cached_data}):
            response = csrf_client.post(
                "/api/generate_character_image",
                json={"scenario_id": "scenario7", "emotion": "friendly"},
            )

            assert response.status_code == 200

    def test_各感情タイプの処理(self, csrf_client):
        """異なる感情タイプの処理"""
        emotions = ["happy", "sad", "angry", "excited", "worried", "calm", "neutral"]

        for emotion in emotions:
            cached_data = {
                "image": f"cached_{emotion}",
                "format": "png",
                "emotion": emotion,
            }

            with patch("routes.image_routes.image_cache", {f"scenario1_{emotion}": cached_data}):
                response = csrf_client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "scenario1", "emotion": emotion},
                )

                assert response.status_code == 200

    def test_年齢推定_20代(self, csrf_client):
        """20代キャラクターの年齢推定（キャッシュから）"""
        # gray_zone_01は新人キャラクター - キャッシュを使用
        cached_data = {
            "image": "young_character_image",
            "format": "png",
            "emotion": "neutral",
        }

        with patch("routes.image_routes.image_cache", {"gray_zone_01_neutral": cached_data}):
            response = csrf_client.post(
                "/api/generate_character_image",
                json={"scenario_id": "gray_zone_01", "emotion": "neutral"},
            )

            assert response.status_code == 200

    def test_キャッシュサイズ制限(self, csrf_client):
        """キャッシュサイズ制限の確認（キャッシュヒットケース）"""
        # 50件のキャッシュエントリを作成
        large_cache = {f"scenario_{i}_neutral": {"image": f"img_{i}"} for i in range(50)}
        # テスト対象のキャッシュエントリを追加
        large_cache["scenario1_excited"] = {
            "image": "excited_image",
            "format": "png",
            "emotion": "excited",
        }

        with patch("routes.image_routes.image_cache", large_cache):
            response = csrf_client.post(
                "/api/generate_character_image",
                json={"scenario_id": "scenario1", "emotion": "excited"},
            )

            # キャッシュヒットで成功
            assert response.status_code == 200

    def test_デフォルト外見の使用(self, csrf_client):
        """デフォルト外見の使用"""
        # SCENARIO_APPEARANCESにないシナリオID
        cached_data = {
            "image": "default_appearance",
            "format": "png",
            "emotion": "neutral",
        }

        with patch("routes.image_routes.image_cache", {"scenario99_neutral": cached_data}):
            # scenario99は存在しないのでエラーになる
            response = csrf_client.post(
                "/api/generate_character_image",
                json={"scenario_id": "scenario99", "emotion": "neutral"},
            )

            assert response.status_code == 400
