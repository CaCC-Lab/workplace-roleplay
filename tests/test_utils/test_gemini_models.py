import pytest

"""utils.gemini_models のテスト"""
from unittest.mock import MagicMock, patch

from utils.gemini_models import (
    DEFAULT_GEMINI_MODEL,
    FALLBACK_GEMINI_MODELS,
    list_gemini_model_ids,
    is_valid_gemini_model_name,
    supports_sampling_parameters,
)


def _model(name, actions=("generateContent",)):
    model = MagicMock(supported_actions=list(actions))
    model.name = name
    return model


class TestListGeminiModelIds:
    def test_会話用モデルだけを返す(self):
        models = [
            _model("models/gemini-2.5-flash"),
            _model("models/gemini-2.5-pro"),
            _model("models/gemini-2.5-flash-preview-tts"),
            _model("models/gemini-2.5-flash-image"),
            _model("models/gemini-embedding-001", actions=("embedContent",)),
            _model("models/imagen-4.0-generate-001", actions=("predict",)),
            _model("models/gemini-2.0-flash-thinking", actions=("countTokens",)),
        ]
        with patch("google.genai.Client") as mock_client:
            mock_client.return_value.models.list.return_value = models

            result = list_gemini_model_ids("test-key")

        mock_client.assert_called_once_with(api_key="test-key")
        assert result == ["gemini/gemini-2.5-flash", "gemini/gemini-2.5-pro"]

    def test_APIキーがない場合は空リスト(self):
        with patch("google.genai.Client") as mock_client:
            assert list_gemini_model_ids(None) == []
            assert list_gemini_model_ids("") == []
        mock_client.assert_not_called()


class TestDefaults:
    def test_既定モデルは提供中の世代(self):
        assert DEFAULT_GEMINI_MODEL == "gemini-3.8-flash"
        assert f"gemini/{DEFAULT_GEMINI_MODEL}" in FALLBACK_GEMINI_MODELS


class TestModelNameValidation:
    @pytest.mark.parametrize(
        "name",
        [
            "gemini-3.8-flash",
            "gemini/gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-4-neon",
            "gemini-2.0-flash-001",
        ],
    )
    def test_Geminiの命名規則に合うモデル名は許可(self, name):
        assert is_valid_gemini_model_name(name)

    @pytest.mark.parametrize(
        "name",
        [
            "gpt-4",
            "unknown-model",
            "gemini-",
            "gemini-3.8-flash; DROP TABLE users;",
            "../gemini-3.8-flash",
            "Gemini-3.8-Flash",
        ],
    )
    def test_不正なモデル名は拒否(self, name):
        assert not is_valid_gemini_model_name(name)


class TestSamplingParameters:
    @pytest.mark.parametrize(
        "name,expected", [("gemini-2.5-flash-lite", True), ("gemini-3.8-flash", False), ("gemini-4-neon", False)]
    )
    def test_Gemini3以降はtemperatureを渡さない(self, name, expected):
        assert supports_sampling_parameters(name) is expected
