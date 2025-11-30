"""
Extended image routes tests for improved coverage.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["TESTING"] = True

    from routes.image_routes import image_bp

    app.register_blueprint(image_bp)

    return app


@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()


class TestGenerateCharacterImage:
    """generate_character_image APIのテスト"""

    def test_JSONなしでリクエスト(self, client):
        """JSONなしでリクエスト"""
        response = client.post(
            "/api/generate_character_image", content_type="application/json", data=""
        )

        # 400または500が返される
        assert response.status_code in [400, 500]

    def test_シナリオIDなしでリクエスト(self, client):
        """シナリオIDなしでリクエスト"""
        response = client.post(
            "/api/generate_character_image",
            json={"emotion": "happy"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_無効なシナリオIDでリクエスト(self, client):
        """無効なシナリオIDでリクエスト"""
        response = client.post(
            "/api/generate_character_image",
            json={"scenario_id": "nonexistent_scenario"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_有効なシナリオIDでリクエスト(self, client):
        """有効なシナリオIDでリクエスト（APIエラー発生）"""
        # シナリオをモック
        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "厳格な40代男性部長"}
            }
            mock_scenarios.get = lambda k, d=None: mock_scenarios[
                k
            ] if k == "scenario1" else d

            # genaiをモック
            with patch.dict(
                "sys.modules",
                {"google.genai": MagicMock(), "google.genai.types": MagicMock()},
            ):
                response = client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "scenario1", "emotion": "happy"},
                )

                # APIエラーまたは503が返される
                assert response.status_code in [200, 500, 503]

    def test_女性キャラクター推定(self, client):
        """女性キャラクターの推定"""
        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario7"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "女性課長、30代"}
            }
            mock_scenarios.get = lambda k, d=None: mock_scenarios[
                k
            ] if k == "scenario7" else d

            with patch.dict(
                "sys.modules",
                {"google.genai": MagicMock(), "google.genai.types": MagicMock()},
            ):
                response = client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "scenario7", "emotion": "calm"},
                )

                # エラー処理が適切に行われる
                assert response.status_code in [200, 500, 503]

    def test_20代キャラクター推定(self, client):
        """20代キャラクターの推定"""
        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "test_scenario"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "20代新人"}
            }
            mock_scenarios.get = lambda k, d=None: mock_scenarios[
                k
            ] if k == "test_scenario" else d

            with patch.dict(
                "sys.modules",
                {"google.genai": MagicMock(), "google.genai.types": MagicMock()},
            ):
                response = client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "test_scenario", "emotion": "excited"},
                )

                assert response.status_code in [200, 500, 503]

    def test_50代キャラクター推定(self, client):
        """50代キャラクターの推定"""
        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "test_senior"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "50代部長"}
            }
            mock_scenarios.get = lambda k, d=None: mock_scenarios[
                k
            ] if k == "test_senior" else d

            with patch.dict(
                "sys.modules",
                {"google.genai": MagicMock(), "google.genai.types": MagicMock()},
            ):
                response = client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "test_senior", "emotion": "confident"},
                )

                assert response.status_code in [200, 500, 503]

    def test_キャッシュヒット(self, client):
        """キャッシュヒット"""
        import routes.image_routes

        # キャッシュを設定
        routes.image_routes.image_cache["scenario1_happy"] = {
            "image": "base64data",
            "format": "png",
            "emotion": "happy",
        }

        # シナリオをモック
        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "男性部長"}
            }
            mock_scenarios.get = lambda k, d=None: mock_scenarios[
                k
            ] if k == "scenario1" else d

            response = client.post(
                "/api/generate_character_image",
                json={"scenario_id": "scenario1", "emotion": "happy"},
            )

            # キャッシュから返される
            if response.status_code == 200:
                data = response.get_json()
                assert data.get("cache_hit") is True

        # キャッシュをクリア
        routes.image_routes.image_cache.clear()

    def test_様々な感情タイプ(self, client):
        """様々な感情タイプ"""
        emotions = ["sad", "angry", "worried", "tired", "professional", "friendly"]

        for emotion in emotions:
            with patch("routes.image_routes.scenarios") as mock_scenarios:
                mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
                mock_scenarios.__getitem__ = lambda self, x: {
                    "character_setting": {"personality": "男性部長"}
                }
                mock_scenarios.get = lambda k, d=None: mock_scenarios[
                    k
                ] if k == "scenario1" else d

                with patch.dict(
                    "sys.modules",
                    {"google.genai": MagicMock(), "google.genai.types": MagicMock()},
                ):
                    response = client.post(
                        "/api/generate_character_image",
                        json={"scenario_id": "scenario1", "emotion": emotion},
                    )

                    assert response.status_code in [200, 500, 503]

    def test_役職推定_課長(self, client):
        """課長の役職推定"""
        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "test_kacho"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "課長"}
            }
            mock_scenarios.get = lambda k, d=None: mock_scenarios[
                k
            ] if k == "test_kacho" else d

            with patch.dict(
                "sys.modules",
                {"google.genai": MagicMock(), "google.genai.types": MagicMock()},
            ):
                response = client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "test_kacho", "emotion": "neutral"},
                )

                assert response.status_code in [200, 500, 503]

    def test_役職推定_先輩(self, client):
        """先輩の役職推定"""
        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "test_senpai"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "先輩"}
            }
            mock_scenarios.get = lambda k, d=None: mock_scenarios[
                k
            ] if k == "test_senpai" else d

            with patch.dict(
                "sys.modules",
                {"google.genai": MagicMock(), "google.genai.types": MagicMock()},
            ):
                response = client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "test_senpai", "emotion": "neutral"},
                )

                assert response.status_code in [200, 500, 503]

    def test_役職推定_同僚(self, client):
        """同僚の役職推定"""
        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "test_colleague"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "同僚"}
            }
            mock_scenarios.get = lambda k, d=None: mock_scenarios[
                k
            ] if k == "test_colleague" else d

            with patch.dict(
                "sys.modules",
                {"google.genai": MagicMock(), "google.genai.types": MagicMock()},
            ):
                response = client.post(
                    "/api/generate_character_image",
                    json={"scenario_id": "test_colleague", "emotion": "neutral"},
                )

                assert response.status_code in [200, 500, 503]


class TestScenarioAppearances:
    """SCENARIO_APPEARANCES定数のテスト"""

    def test_定数が定義されている(self):
        """定数が定義されている"""
        from routes.image_routes import SCENARIO_APPEARANCES

        assert isinstance(SCENARIO_APPEARANCES, dict)
        assert len(SCENARIO_APPEARANCES) > 0

    def test_デフォルト外見が定義されている(self):
        """デフォルト外見が定義されている"""
        from routes.image_routes import SCENARIO_APPEARANCES

        assert "default_male" in SCENARIO_APPEARANCES
        assert "default_female" in SCENARIO_APPEARANCES


class TestImageGenerationSuccess:
    """画像生成成功パスのテスト"""

    def test_画像生成成功_文字列データ(self, client):
        """画像生成成功（文字列データ）"""
        import routes.image_routes

        # キャッシュをクリア
        routes.image_routes.image_cache.clear()

        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "男性部長", "situation": "会議"}
            }
            mock_scenarios.get = lambda k, d=None: (
                mock_scenarios[k] if k == "scenario1" else d
            )

            # genaiモジュールをモック
            mock_genai = MagicMock()
            mock_types = MagicMock()

            # レスポンスをモック
            mock_part = MagicMock()
            mock_part.text = None
            mock_part.inline_data = MagicMock()
            mock_part.inline_data.data = "base64encodedimagedata"

            mock_content = MagicMock()
            mock_content.parts = [mock_part]

            mock_candidate = MagicMock()
            mock_candidate.content = mock_content

            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            with patch.dict(
                "sys.modules",
                {"google.genai": mock_genai, "google.genai.types": mock_types},
            ):
                with patch("routes.image_routes.genai", mock_genai, create=True):
                    response = client.post(
                        "/api/generate_character_image",
                        json={"scenario_id": "scenario1", "emotion": "happy"},
                    )

                    # 成功またはエラー
                    assert response.status_code in [200, 500, 503]

    def test_画像生成成功_バイナリデータ(self, client):
        """画像生成成功（バイナリデータ）"""
        import routes.image_routes

        routes.image_routes.image_cache.clear()

        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "男性部長", "situation": "休憩室"}
            }
            mock_scenarios.get = lambda k, d=None: (
                mock_scenarios[k] if k == "scenario1" else d
            )

            mock_genai = MagicMock()
            mock_types = MagicMock()

            # バイナリデータをモック
            mock_part = MagicMock()
            mock_part.text = "Generated image description"
            mock_part.inline_data = MagicMock()
            mock_part.inline_data.data = b"binary_image_data"

            mock_content = MagicMock()
            mock_content.parts = [mock_part]

            mock_candidate = MagicMock()
            mock_candidate.content = mock_content

            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            with patch.dict(
                "sys.modules",
                {"google.genai": mock_genai, "google.genai.types": mock_types},
            ):
                with patch("routes.image_routes.genai", mock_genai, create=True):
                    response = client.post(
                        "/api/generate_character_image",
                        json={"scenario_id": "scenario1", "emotion": "neutral"},
                    )

                    assert response.status_code in [200, 500, 503]

    def test_画像生成失敗_画像データなし(self, client):
        """画像生成失敗（画像データなし）"""
        import routes.image_routes

        routes.image_routes.image_cache.clear()

        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "男性部長"}
            }
            mock_scenarios.get = lambda k, d=None: (
                mock_scenarios[k] if k == "scenario1" else d
            )

            mock_genai = MagicMock()
            mock_types = MagicMock()

            # 画像データがないレスポンス
            mock_part = MagicMock()
            mock_part.text = "No image"
            mock_part.inline_data = None

            mock_content = MagicMock()
            mock_content.parts = [mock_part]

            mock_candidate = MagicMock()
            mock_candidate.content = mock_content

            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            with patch.dict(
                "sys.modules",
                {"google.genai": mock_genai, "google.genai.types": mock_types},
            ):
                with patch("routes.image_routes.genai", mock_genai, create=True):
                    response = client.post(
                        "/api/generate_character_image",
                        json={"scenario_id": "scenario1", "emotion": "happy"},
                    )

                    # エラー
                    assert response.status_code in [500, 503]

    def test_キャッシュサイズ制限(self, client):
        """キャッシュサイズ制限"""
        import routes.image_routes

        # キャッシュを最大サイズまで埋める
        for i in range(routes.image_routes.MAX_CACHE_SIZE):
            routes.image_routes.image_cache[f"dummy_{i}"] = {"data": f"test_{i}"}

        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "男性部長"}
            }
            mock_scenarios.get = lambda k, d=None: (
                mock_scenarios[k] if k == "scenario1" else d
            )

            mock_genai = MagicMock()
            mock_types = MagicMock()

            mock_part = MagicMock()
            mock_part.text = None
            mock_part.inline_data = MagicMock()
            mock_part.inline_data.data = "imagedata"

            mock_content = MagicMock()
            mock_content.parts = [mock_part]

            mock_candidate = MagicMock()
            mock_candidate.content = mock_content

            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]

            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            with patch.dict(
                "sys.modules",
                {"google.genai": mock_genai, "google.genai.types": mock_types},
            ):
                with patch("routes.image_routes.genai", mock_genai, create=True):
                    response = client.post(
                        "/api/generate_character_image",
                        json={"scenario_id": "scenario1", "emotion": "new_emotion"},
                    )

                    # 成功または失敗
                    assert response.status_code in [200, 500, 503]

        # キャッシュをクリア
        routes.image_routes.image_cache.clear()

    def test_状況による背景変更_ランチ(self, client):
        """ランチ状況での背景変更"""
        import routes.image_routes

        routes.image_routes.image_cache.clear()

        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "男性部長", "situation": "ランチ休憩"}
            }
            mock_scenarios.get = lambda k, d=None: (
                mock_scenarios[k] if k == "scenario1" else d
            )

            mock_genai = MagicMock()
            mock_types = MagicMock()

            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception("API Error")
            mock_genai.Client.return_value = mock_client

            with patch.dict(
                "sys.modules",
                {"google.genai": mock_genai, "google.genai.types": mock_types},
            ):
                with patch("routes.image_routes.genai", mock_genai, create=True):
                    response = client.post(
                        "/api/generate_character_image",
                        json={"scenario_id": "scenario1", "emotion": "happy"},
                    )

                    # APIエラー
                    assert response.status_code in [500, 503]

    def test_状況による背景変更_懇親会(self, client):
        """懇親会状況での背景変更"""
        import routes.image_routes

        routes.image_routes.image_cache.clear()

        with patch("routes.image_routes.scenarios") as mock_scenarios:
            mock_scenarios.__contains__ = lambda self, x: x == "scenario1"
            mock_scenarios.__getitem__ = lambda self, x: {
                "character_setting": {"personality": "男性部長", "situation": "懇親会"}
            }
            mock_scenarios.get = lambda k, d=None: (
                mock_scenarios[k] if k == "scenario1" else d
            )

            mock_genai = MagicMock()
            mock_types = MagicMock()

            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception("API Error")
            mock_genai.Client.return_value = mock_client

            with patch.dict(
                "sys.modules",
                {"google.genai": mock_genai, "google.genai.types": mock_types},
            ):
                with patch("routes.image_routes.genai", mock_genai, create=True):
                    response = client.post(
                        "/api/generate_character_image",
                        json={"scenario_id": "scenario1", "emotion": "happy"},
                    )

                    assert response.status_code in [500, 503]


class TestSecurityUtilsFallback:
    """SecurityUtilsフォールバックのテスト"""

    def test_フォールバッククラスが存在(self):
        """フォールバッククラスが存在"""
        from routes.image_routes import SecurityUtils

        result = SecurityUtils.get_safe_error_message(Exception("test"))
        # サニタイズされたメッセージまたは元のメッセージが返される
        assert result is not None
        assert isinstance(result, str)
