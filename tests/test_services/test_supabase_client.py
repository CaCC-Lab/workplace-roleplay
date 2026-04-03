"""
SupabaseClientManager のユニットテスト（環境変数は monkeypatch）
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.supabase_client import (
    ENV_SUPABASE_KEY,
    ENV_SUPABASE_URL,
    SupabaseClientManager,
    SupabaseUserDataService,
)
from services.user_data_service import UserDataService


@pytest.fixture
def manager():
    m = SupabaseClientManager()
    m.reset()
    yield m
    m.reset()


class TestIsAvailable:
    def test_available_when_url_and_key_set(self, manager, monkeypatch):
        monkeypatch.setenv(ENV_SUPABASE_URL, "https://example.supabase.co")
        monkeypatch.setenv(ENV_SUPABASE_KEY, "test-key")
        assert manager.is_available() is True

    def test_not_available_when_unset(self, manager, monkeypatch):
        monkeypatch.delenv(ENV_SUPABASE_URL, raising=False)
        monkeypatch.delenv(ENV_SUPABASE_KEY, raising=False)
        assert manager.is_available() is False


class TestGetUserDataServiceJsonFallback:
    def test_returns_plain_user_data_service_when_env_unset(self, manager, monkeypatch):
        monkeypatch.delenv(ENV_SUPABASE_URL, raising=False)
        monkeypatch.delenv(ENV_SUPABASE_KEY, raising=False)
        svc = manager.get_user_data_service()
        assert type(svc) is UserDataService
        assert not hasattr(svc, "_client")


class TestGetClientFallback:
    def test_returns_json_user_data_when_client_fails(self, manager, monkeypatch):
        monkeypatch.setenv(ENV_SUPABASE_URL, "https://example.supabase.co")
        monkeypatch.setenv(ENV_SUPABASE_KEY, "test-key")

        import types

        fake_mod = types.ModuleType("supabase")

        def boom(_url, _key):
            raise RuntimeError("connection failed")

        fake_mod.create_client = boom
        monkeypatch.setitem(sys.modules, "supabase", fake_mod)

        manager.reset()
        assert manager.get_client() is None
        svc = manager.get_user_data_service()
        assert type(svc) is UserDataService


class TestSupabaseUserDataWhenClientOk:
    def test_returns_supabase_user_data_service_with_mock_client(self, manager, monkeypatch):
        monkeypatch.setenv(ENV_SUPABASE_URL, "https://example.supabase.co")
        monkeypatch.setenv(ENV_SUPABASE_KEY, "test-key")

        mock_client = MagicMock(name="supabase_client")

        def fake_create_client(_url, _key):
            return mock_client

        fake_mod = MagicMock()
        fake_mod.create_client = fake_create_client
        monkeypatch.setitem(sys.modules, "supabase", fake_mod)

        manager.reset()
        assert manager.get_client() is mock_client
        svc = manager.get_user_data_service()
        assert isinstance(svc, SupabaseUserDataService)
        assert isinstance(svc, UserDataService)
        assert svc._client is mock_client
