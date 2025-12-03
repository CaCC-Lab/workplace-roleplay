# -*- coding: utf-8 -*-
"""
シークレットキーのセキュリティ検証テスト
TDD原則に従い、本番環境でのセキュアなシークレットキー管理を保証
"""
import os
import pytest
import warnings
from unittest.mock import patch
from config.config import Config, ProductionConfig, DevelopmentConfig, ConfigForTesting


class TestSecretKeyValidation:
    """シークレットキーのセキュリティ検証テスト"""

    @pytest.fixture(autouse=True)
    def clean_env(self):
        """各テストの前後で環境変数をクリーンに保つ"""
        original_env = os.environ.copy()
        yield
        os.environ.clear()
        os.environ.update(original_env)

    def test_production_rejects_default_secret_key(self):
        """本番環境でデフォルトシークレットキーを拒否することを確認"""
        with patch.dict(
            os.environ,
            {
                "FLASK_ENV": "production",
                "FLASK_SECRET_KEY": "default-secret-key-change-in-production",
                "GOOGLE_API_KEY": "valid-api-key",
            },
            clear=True,
        ):
            # 本番設定の作成を試みて、エラーになることを確認
            with pytest.raises(ValueError, match="A secure SECRET_KEY is required in production"):
                ProductionConfig()

    def test_production_rejects_empty_secret_key(self):
        """本番環境で空のシークレットキーを拒否することを確認"""
        with patch.dict(
            os.environ,
            {"FLASK_ENV": "production", "FLASK_SECRET_KEY": "", "GOOGLE_API_KEY": "valid-api-key"},
            clear=True,
        ):
            with pytest.raises(ValueError, match="A secure SECRET_KEY is required in production"):
                ProductionConfig()

    def test_production_accepts_custom_secret_key(self):
        """本番環境でカスタムシークレットキーを受け入れることを確認"""
        secure_key = "my-very-secure-production-key-with-enough-length-123456789"
        with patch.dict(
            os.environ,
            {"FLASK_ENV": "production", "FLASK_SECRET_KEY": secure_key, "GOOGLE_API_KEY": "valid-api-key"},
            clear=True,
        ):
            config = ProductionConfig()
            assert config.SECRET_KEY == secure_key

    def test_development_warns_on_default_secret_key(self):
        """開発環境でデフォルトシークレットキー使用時に警告を出すことを確認"""
        with patch.dict(
            os.environ,
            {"FLASK_ENV": "development", "FLASK_SECRET_KEY": "dev-secret-key-for-development-only"},
            clear=True,
        ):
            # 警告が発生することを確認
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                config = DevelopmentConfig()

                # 警告が記録されているか確認
                assert len(w) > 0
                assert "Using default SECRET_KEY in development" in str(w[0].message)

    def test_secret_key_minimum_length_requirement(self):
        """シークレットキーの最小長要件をチェック"""
        with patch.dict(
            os.environ,
            {"FLASK_ENV": "production", "FLASK_SECRET_KEY": "short", "GOOGLE_API_KEY": "valid-api-key"},  # 短すぎるキー
            clear=True,
        ):
            with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 characters long"):
                ProductionConfig()

    def test_production_rejects_simple_patterns(self):
        """本番環境で単純なパターンのキーを拒否することを確認"""
        simple_patterns = [
            "password123password123password123password123",  # 単純な繰り返し
            "secret123secret123secret123secret123",  # 単純な繰り返し
            "12345678901234567890123456789012345678",  # 数字のみ
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",  # 同じ文字の繰り返し
        ]

        for pattern in simple_patterns:
            with patch.dict(
                os.environ,
                {"FLASK_ENV": "production", "FLASK_SECRET_KEY": pattern, "GOOGLE_API_KEY": "valid-api-key"},
                clear=True,
            ):
                with pytest.raises(ValueError, match="SECRET_KEY is too simple and predictable"):
                    ProductionConfig()

    def test_development_uses_default_key_when_not_set(self):
        """開発環境で環境変数が未設定の場合、デフォルトキーを使用"""

        # .envファイルを読み込まないテスト用クラスを作成
        class TestDevelopmentConfig(DevelopmentConfig):
            model_config = {**DevelopmentConfig.model_config, "env_file": None}  # .envファイルを読み込まない

        # 環境変数をクリアしてテスト
        with patch.dict(os.environ, {"FLASK_ENV": "development"}, clear=True):
            # 警告をキャッチしつつ設定を作成
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                config = TestDevelopmentConfig()

                # DevelopmentConfigのset_dev_secret_keyで設定される値
                assert config.SECRET_KEY == "dev-secret-key-for-development-only"
                # 警告が発生していることも確認
                assert len(w) > 0
                assert "Using default SECRET_KEY in development" in str(w[0].message)

    def test_testing_environment_uses_safe_defaults(self):
        """テスト環境では安全なデフォルト値を使用"""
        with patch.dict(os.environ, {"FLASK_ENV": "testing"}, clear=True):
            config = ConfigForTesting()
            # テスト環境では検証を緩和
            assert config.SECRET_KEY is not None
            assert len(config.SECRET_KEY) > 0
