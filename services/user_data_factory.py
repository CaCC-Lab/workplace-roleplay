"""
UserDataService の取得（環境に応じて JSON 版 / Supabase 版）
"""

from __future__ import annotations

from typing import Union

from services.supabase_client import get_supabase_client_manager
from services.supabase_user_data_service import SupabaseUserDataService
from services.user_data_service import UserDataService


def get_user_data_service() -> Union[UserDataService, SupabaseUserDataService]:
    """
    SUPABASE_URL / SUPABASE_KEY が有効に設定されクライアント生成に成功した場合は
    SupabaseUserDataService、それ以外は JSON ファイル版 UserDataService。
    """
    return get_supabase_client_manager().get_user_data_service()
