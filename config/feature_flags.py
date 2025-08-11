"""
フィーチャーフラグ管理
A/Bテストや段階的ロールアウトのための機能切り替え設定
"""
import os
from typing import Dict, Any
from enum import Enum

class ServiceMode(Enum):
    """サービスモード"""
    LEGACY = "legacy"      # 既存実装のみ
    PARALLEL = "parallel"  # 並行稼働（A/Bテスト）
    CANARY = "canary"      # カナリアリリース（一部ユーザー）
    NEW = "new"           # 新実装のみ

class FeatureFlags:
    """フィーチャーフラグ管理クラス"""
    
    def __init__(self):
        """環境変数から設定を読み込み"""
        # サービスモード
        self.service_mode = ServiceMode(
            os.getenv('SERVICE_MODE', ServiceMode.LEGACY.value)
        )
        
        # 個別機能のフラグ
        self.use_new_chat_service = self._get_bool_env('USE_NEW_CHAT_SERVICE', False)
        self.use_new_scenario_service = self._get_bool_env('USE_NEW_SCENARIO_SERVICE', False)
        self.use_new_watch_service = self._get_bool_env('USE_NEW_WATCH_SERVICE', False)
        
        # A/Bテスト設定
        self.ab_test_enabled = self._get_bool_env('AB_TEST_ENABLED', True)
        self.ab_test_ratio = float(os.getenv('AB_TEST_RATIO', '0.1'))  # 10%のユーザーで新サービス
        
        # デバッグ設定
        self.compare_mode = self._get_bool_env('COMPARE_MODE', True)  # 新旧比較モード
        self.log_differences = self._get_bool_env('LOG_DIFFERENCES', True)  # 差分をログ出力
        
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """環境変数からブール値を取得"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def should_use_new_service(self, service_name: str, user_id: str = None) -> bool:
        """新サービスを使用すべきか判定"""
        if self.service_mode == ServiceMode.NEW:
            return True
        
        if self.service_mode == ServiceMode.LEGACY:
            return False
        
        if self.service_mode == ServiceMode.CANARY and user_id:
            # ユーザーIDのハッシュ値で一貫した振り分け（SHA-256使用）
            from utils.security import SecurityUtils
            hash_hex = SecurityUtils.hash_user_id(user_id)
            # 最初の8文字を使用して数値化
            hash_value = int(hash_hex[:8], 16)
            return (hash_value % 100) < (self.ab_test_ratio * 100)
        
        # 個別フラグをチェック
        if service_name == 'chat':
            return self.use_new_chat_service
        elif service_name == 'scenario':
            return self.use_new_scenario_service
        elif service_name == 'watch':
            return self.use_new_watch_service
        
        return False
    
    def get_config(self) -> Dict[str, Any]:
        """現在の設定を取得"""
        return {
            'service_mode': self.service_mode.value,
            'ab_test_enabled': self.ab_test_enabled,
            'ab_test_ratio': self.ab_test_ratio,
            'compare_mode': self.compare_mode,
            'features': {
                'chat': self.use_new_chat_service,
                'scenario': self.use_new_scenario_service,
                'watch': self.use_new_watch_service
            }
        }

# シングルトンインスタンス
feature_flags = FeatureFlags()