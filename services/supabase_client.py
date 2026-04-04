"""
Supabase クライアント管理（未設定・接続失敗時は JSON 版 UserDataService にフォールバック）
"""

from __future__ import annotations

import os
from typing import Any, Optional, Union

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from services.supabase_user_data_service import SupabaseUserDataService
from services.user_data_service import UserDataService

# 環境変数名（プロジェクトで統一）
ENV_SUPABASE_URL = "SUPABASE_URL"
ENV_SUPABASE_KEY = "SUPABASE_KEY"
ENV_SUPABASE_SERVICE_KEY = "SUPABASE_SERVICE_KEY"

_supabase_client_manager_instance: Optional["SupabaseClientManager"] = None


def get_supabase_client_manager() -> "SupabaseClientManager":
    """アプリ全体で共有する SupabaseClientManager（クライアントキャッシュを一元化）。"""
    global _supabase_client_manager_instance
    if _supabase_client_manager_instance is None:
        _supabase_client_manager_instance = SupabaseClientManager()
    return _supabase_client_manager_instance


class SupabaseClientManager:
    """Supabase クライアントの遅延生成と UserDataService の選択。"""

    def __init__(self) -> None:
        self._client_cache: Optional[Any] = None
        self._client_attempted = False

    def reset(self) -> None:
        """テスト用: キャッシュをクリア"""
        self._client_cache = None
        self._client_attempted = False

    @staticmethod
    def _env_configured() -> bool:
        url = (os.environ.get(ENV_SUPABASE_URL) or "").strip()
        key = (os.environ.get(ENV_SUPABASE_KEY) or "").strip()
        return bool(url and key)

    def is_available(self) -> bool:
        """SUPABASE_URL / SUPABASE_KEY がともに非空なら True（接続可否とは独立）。"""
        return self._env_configured()

    def get_client(self) -> Optional[Any]:
        """
        supabase.Client を返す。未設定・import 失敗・create_client 失敗時は None。
        """
        if not self._env_configured():
            return None
        if self._client_cache is not None:
            return self._client_cache
        if self._client_attempted:
            return None
        self._client_attempted = True
        try:
            from supabase import create_client  # type: ignore
        except ImportError:
            self._client_cache = None
            return None
        try:
            url = os.environ[ENV_SUPABASE_URL].strip()
            # サーバーサイドはservice_role keyでRLSバイパス（未設定ならanon key）
            key = (os.environ.get(ENV_SUPABASE_SERVICE_KEY) or os.environ.get(ENV_SUPABASE_KEY, "")).strip()
            self._client_cache = create_client(url, key)
        except Exception:
            self._client_cache = None
        return self._client_cache

    def get_user_data_service(self) -> Union[UserDataService, SupabaseUserDataService]:
        """
        クライアント取得に成功した場合は SupabaseUserDataService、
        それ以外は JSON ファイル版 UserDataService。
        """
        client = self.get_client()
        if client is None:
            return UserDataService()
        return SupabaseUserDataService(client)
