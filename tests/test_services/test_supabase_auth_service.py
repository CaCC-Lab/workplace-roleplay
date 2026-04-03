"""
SupabaseAuthService のユニットテスト（Supabase クライアントは Mock）
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.supabase_auth_service import SupabaseAuthService


@pytest.fixture
def mock_auth():
    return MagicMock()


@pytest.fixture
def mock_client(mock_auth):
    c = MagicMock()
    c.auth = mock_auth
    return c


@pytest.fixture
def auth_svc(mock_client):
    return SupabaseAuthService(mock_client)


class TestSignUp:
    def test_sign_up_success(self, auth_svc, mock_auth):
        mock_user = {"id": "u1", "email": "a@b.com"}
        mock_res = MagicMock()
        mock_res.user = mock_user
        mock_res.error = None
        mock_auth.sign_up.return_value = mock_res

        r = auth_svc.sign_up("a@b.com", "secret123")
        assert r["error"] is None
        assert r["user"] == mock_user
        mock_auth.sign_up.assert_called_once()


class TestSignIn:
    def test_sign_in_success(self, auth_svc, mock_auth):
        mock_res = MagicMock()
        mock_res.user = {"id": "u1"}
        mock_res.session = {"access_token": "tok"}
        mock_res.error = None
        mock_auth.sign_in_with_password.return_value = mock_res

        r = auth_svc.sign_in("a@b.com", "secret123")
        assert r["error"] is None
        assert r["user"] is not None
        assert r["session"] is not None


class TestSignOut:
    def test_sign_out_success(self, auth_svc, mock_auth):
        mock_auth.sign_out.return_value = None
        r = auth_svc.sign_out()
        assert r["success"] is True
        mock_auth.sign_out.assert_called_once()


class TestGetCurrentUser:
    def test_invalid_token_returns_none(self, auth_svc, mock_auth):
        mock_auth.get_user.side_effect = Exception("invalid jwt")
        assert auth_svc.get_current_user("bad") is None

    def test_empty_password_sign_up_error(self, auth_svc, mock_auth):
        r = auth_svc.sign_up("a@b.com", "")
        assert r["user"] is None
        assert r["error"] is not None
        mock_auth.sign_up.assert_not_called()

    def test_empty_password_sign_in_error(self, auth_svc, mock_auth):
        r = auth_svc.sign_in("a@b.com", "   ")
        assert r["user"] is None
        assert r["error"] is not None
        mock_auth.sign_in_with_password.assert_not_called()
