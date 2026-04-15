"""
services/model_selector.py の優先順位テスト（Phase B）
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.model_selector import resolve_model


@pytest.fixture
def default_model_config():
    """get_config() が DEFAULT_MODEL="gemini/gemini-2.5-flash" を返すようモック"""
    cfg = MagicMock()
    cfg.DEFAULT_MODEL = "gemini/gemini-2.5-flash"
    with patch("services.model_selector.get_config", return_value=cfg):
        yield cfg


class TestFeedbackModeUsesEnvOnly:
    """feedback は session_selected を無視し FEEDBACK_MODEL → DEFAULT_MODEL"""

    def test_feedbackはUI選択よりFEEDBACK_MODELが優先(self, default_model_config, monkeypatch):
        monkeypatch.setenv("FEEDBACK_MODEL", "ollama/gemma4:31b-cloud")
        result = resolve_model("feedback", session_selected="gemini/gemini-2.5-flash-lite")
        assert result == "ollama/gemma4:31b-cloud"

    def test_feedback_Feedback未設定はDEFAULT_MODEL(self, default_model_config, monkeypatch):
        monkeypatch.delenv("FEEDBACK_MODEL", raising=False)
        result = resolve_model("feedback", session_selected="gemini/gemini-2.5-pro")
        assert result == "gemini/gemini-2.5-flash"


class TestResolveModelPriority:
    """優先順位: session_selected > <MODE>_MODEL env > DEFAULT_MODEL"""

    def test_session_selectedが最優先される(self, default_model_config, monkeypatch):
        monkeypatch.setenv("SCENARIO_MODEL", "ollama/gemma4:31b-cloud")
        result = resolve_model("scenario", session_selected="gemini/gemini-2.5-pro")
        assert result == "gemini/gemini-2.5-pro"

    def test_session_selectedが空文字なら無視される(self, default_model_config, monkeypatch):
        monkeypatch.setenv("SCENARIO_MODEL", "ollama/gemma4:31b-cloud")
        result = resolve_model("scenario", session_selected="   ")
        assert result == "ollama/gemma4:31b-cloud"

    def test_mode別env変数が使われる(self, default_model_config, monkeypatch):
        monkeypatch.setenv("SCENARIO_MODEL", "ollama/gemma4:31b-cloud")
        result = resolve_model("scenario")
        assert result == "ollama/gemma4:31b-cloud"

    def test_env未設定時はDEFAULT_MODELにフォールバック(self, default_model_config, monkeypatch):
        monkeypatch.delenv("SCENARIO_MODEL", raising=False)
        result = resolve_model("scenario")
        assert result == "gemini/gemini-2.5-flash"

    def test_全4モードのenv変数を正しく参照する(self, default_model_config, monkeypatch):
        monkeypatch.setenv("SCENARIO_MODEL", "m-scenario")
        monkeypatch.setenv("CHAT_MODEL", "m-chat")
        monkeypatch.setenv("WATCH_MODEL", "m-watch")
        monkeypatch.setenv("FEEDBACK_MODEL", "m-feedback")

        assert resolve_model("scenario") == "m-scenario"
        assert resolve_model("chat") == "m-chat"
        assert resolve_model("watch") == "m-watch"
        assert resolve_model("feedback") == "m-feedback"

    def test_未知のmodeでValueError(self, default_model_config):
        with pytest.raises(ValueError, match="Unknown mode"):
            resolve_model("unknown_mode")

    def test_モード別envが空文字ならDEFAULT_MODELにフォールバック(self, default_model_config, monkeypatch):
        monkeypatch.setenv("CHAT_MODEL", "")
        result = resolve_model("chat")
        assert result == "gemini/gemini-2.5-flash"


class TestConfigModeFields:
    """Config クラスがモード別フィールドを受理・バリデートすること"""

    def test_全4フィールドがNoneを許可する(self, monkeypatch):
        from config.config import Config

        # 環境変数の汚染を排除（.env や CI 環境変数の影響を受けないようにする）
        for key in ("SCENARIO_MODEL", "CHAT_MODEL", "WATCH_MODEL", "FEEDBACK_MODEL"):
            monkeypatch.delenv(key, raising=False)

        cfg = Config(_env_file=None)
        assert cfg.SCENARIO_MODEL is None
        assert cfg.CHAT_MODEL is None
        assert cfg.WATCH_MODEL is None
        assert cfg.FEEDBACK_MODEL is None

    def test_OllamaモデルをSCENARIO_MODELに設定できる(self):
        from config.config import Config

        cfg = Config(SCENARIO_MODEL="ollama/gemma4:31b-cloud")
        assert cfg.SCENARIO_MODEL == "ollama/gemma4:31b-cloud"

    def test_不正なモデル名は拒否される(self):
        from config.config import Config

        with pytest.raises(ValueError, match="Unsupported model"):
            Config(FEEDBACK_MODEL="invalid/random-model")

    def test_空文字列はNoneとして扱われる(self, monkeypatch):
        """GitHub Secrets 未設定時に '.env' へ 'KEY=' が書き込まれるケース"""
        from config.config import Config

        for key in ("SCENARIO_MODEL", "CHAT_MODEL", "WATCH_MODEL", "FEEDBACK_MODEL"):
            monkeypatch.delenv(key, raising=False)

        cfg = Config(_env_file=None, SCENARIO_MODEL="", CHAT_MODEL="   ")
        assert cfg.SCENARIO_MODEL is None
        assert cfg.CHAT_MODEL is None
