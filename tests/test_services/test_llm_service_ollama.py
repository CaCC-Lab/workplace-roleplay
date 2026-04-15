"""
LLMService の Ollama Cloud 経路テスト（Phase A）

スコープ:
- create_ollama_llm() のキー未設定時エラー
- create_ollama_llm() の正常初期化
- initialize_llm() の ollama/ 分岐
- Gemini 経路のリグレッションが無いこと
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from services.llm_service import LLMService


@pytest.fixture
def service():
    """GOOGLE_API_KEY が無くても初期化できるよう genai.configure をスキップ"""
    with patch("services.llm_service.genai.configure"):
        with patch("services.llm_service.CompliantAPIManager"):
            yield LLMService()


class TestCreateOllamaLlm:
    def test_APIキー未設定でRuntimeErrorが発生する(self, service, monkeypatch):
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OLLAMA_API_KEY"):
            service.create_ollama_llm("gemma4:31b-cloud")

    def test_APIキー設定時にChatOpenAIが生成される(self, service, monkeypatch):
        monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        with patch("services.llm_service.ChatOpenAI") as mock_chat:
            mock_chat.return_value = MagicMock()
            service.create_ollama_llm("gemma4:31b-cloud")
            mock_chat.assert_called_once()
            kwargs = mock_chat.call_args.kwargs
            assert kwargs["model"] == "gemma4:31b-cloud"
            assert kwargs["api_key"] == "test-key"
            assert kwargs["base_url"] == "https://ollama.com/v1"
            assert kwargs["streaming"] is True

    def test_OLLAMA_BASE_URLで上書きできる(self, service, monkeypatch):
        monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
        monkeypatch.setenv("OLLAMA_BASE_URL", "https://custom.example.com/v1")
        with patch("services.llm_service.ChatOpenAI") as mock_chat:
            mock_chat.return_value = MagicMock()
            service.create_ollama_llm("gemma4:31b-cloud")
            assert mock_chat.call_args.kwargs["base_url"] == "https://custom.example.com/v1"

    def test_langchain_openai未インストール時にRuntimeError(self, service, monkeypatch):
        monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
        with patch("services.llm_service.ChatOpenAI", None):
            with pytest.raises(RuntimeError, match="langchain-openai"):
                service.create_ollama_llm("gemma4:31b-cloud")


class TestInitializeLlmRouting:
    def test_ollamaプレフィックスでOllama経路に分岐する(self, service, monkeypatch):
        monkeypatch.setenv("OLLAMA_API_KEY", "test-key")
        with patch.object(service, "create_ollama_llm") as mock_ollama, \
             patch.object(service, "create_gemini_llm") as mock_gemini:
            mock_ollama.return_value = MagicMock()
            service.initialize_llm("ollama/gemma4:31b-cloud")
            mock_ollama.assert_called_once_with("gemma4:31b-cloud")
            mock_gemini.assert_not_called()

    def test_geminiプレフィックスでGemini経路に分岐する(self, service):
        with patch.object(service, "create_ollama_llm") as mock_ollama, \
             patch.object(service, "create_gemini_llm") as mock_gemini:
            mock_gemini.return_value = MagicMock()
            service.initialize_llm("gemini/gemini-2.5-flash")
            mock_gemini.assert_called_once_with("gemini-2.5-flash")
            mock_ollama.assert_not_called()

    def test_プレフィックスなしでGemini経路に分岐する(self, service):
        with patch.object(service, "create_ollama_llm") as mock_ollama, \
             patch.object(service, "create_gemini_llm") as mock_gemini:
            mock_gemini.return_value = MagicMock()
            service.initialize_llm("gemini-2.5-flash-lite")
            mock_gemini.assert_called_once_with("gemini-2.5-flash-lite")
            mock_ollama.assert_not_called()


class TestConfigValidateModel:
    """config.Config の validate_model が ollama/* を受理することを確認"""

    def test_ollama_gemma4が許可される(self):
        from config.config import Config

        cfg = Config(DEFAULT_MODEL="ollama/gemma4:31b-cloud")
        assert cfg.DEFAULT_MODEL == "ollama/gemma4:31b-cloud"

    def test_ollama_qwen2_5が許可される(self):
        from config.config import Config

        cfg = Config(DEFAULT_MODEL="ollama/qwen2.5:72b-cloud")
        assert cfg.DEFAULT_MODEL == "ollama/qwen2.5:72b-cloud"

    def test_未サポートプロバイダは拒否される(self):
        from config.config import Config

        with pytest.raises(ValueError, match="Unsupported model"):
            Config(DEFAULT_MODEL="anthropic/claude-3-opus")
