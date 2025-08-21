"""
⚠️  DEPRECATED - 規約違反リスクのため非推奨 ⚠️
このファイルは Google Gemini API利用規約に違反する可能性があります。

問題点:
1. レート制限回避の明示的意図
2. 複数APIキーのローテーション使用
3. Google Cloud Platform利用規約への抵触リスク

代替: compliant_api_manager.py を使用してください

⚠️  DO NOT USE - COMPLIANCE RISK ⚠️
"""

import os
import time
from typing import List, Optional, Dict, Any
from collections import defaultdict
import random


class APIKeyManager:
    """
    複数のAPIキーを管理し、レート制限を回避するためのローテーションを行う
    """
    
    def __init__(self):
        self.api_keys = []
        self.usage_counts = defaultdict(int)  # キーごとの使用回数
        self.last_used = defaultdict(float)  # キーごとの最終使用時刻
        self.error_counts = defaultdict(int)  # キーごとのエラー回数
        self.blocked_until = defaultdict(float)  # キーごとのブロック解除時刻
        
        # 環境変数から複数のAPIキーを読み込む
        self._load_api_keys()
        
        # レート制限の設定
        self.rate_limit_per_minute = 15  # Gemini無料枠: 1分あたり15リクエスト
        self.rate_limit_per_day = 1500  # Gemini無料枠: 1日あたり1500リクエスト
        self.cooldown_period = 60  # エラー後の待機時間（秒）
    
    def _load_api_keys(self):
        """環境変数から複数のAPIキーを読み込む"""
        # メインのAPIキー
        main_key = os.getenv("GOOGLE_API_KEY")
        if main_key:
            self.api_keys.append(main_key)
        
        # 追加のAPIキー（GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ...）
        for i in range(1, 10):  # 最大9個の追加キー
            key = os.getenv(f"GOOGLE_API_KEY_{i}")
            if key:
                self.api_keys.append(key)
                print(f"Loaded additional API key #{i}")
        
        if not self.api_keys:
            raise ValueError("No Google API keys found in environment variables")
        
        print(f"Total API keys loaded: {len(self.api_keys)}")
    
    def get_next_key(self) -> Optional[str]:
        """
        次に使用可能なAPIキーを取得
        レート制限やエラー状態を考慮してキーを選択
        """
        current_time = time.time()
        available_keys = []
        
        for key in self.api_keys:
            # ブロックされているキーはスキップ
            if self.blocked_until[key] > current_time:
                continue
            
            # レート制限のチェック（簡易版）
            time_since_last_use = current_time - self.last_used[key]
            if time_since_last_use < 4:  # 4秒間隔（15リクエスト/分）
                continue
            
            available_keys.append(key)
        
        if not available_keys:
            # 全てのキーが使用不可の場合、最も早く使用可能になるキーを返す
            return self._get_least_blocked_key()
        
        # 使用回数が最も少ないキーを優先
        return min(available_keys, key=lambda k: self.usage_counts[k])
    
    def _get_least_blocked_key(self) -> str:
        """最も早くブロックが解除されるキーを取得"""
        return min(self.api_keys, key=lambda k: self.blocked_until[k])
    
    def record_usage(self, api_key: str):
        """APIキーの使用を記録"""
        self.usage_counts[api_key] += 1
        self.last_used[api_key] = time.time()
    
    def record_error(self, api_key: str, error: Exception):
        """エラーを記録し、必要に応じてキーをブロック"""
        self.error_counts[api_key] += 1
        error_str = str(error)
        
        # レート制限エラーの場合、一時的にブロック
        if "insufficient_quota" in error_str or "429" in error_str:
            self.blocked_until[api_key] = time.time() + self.cooldown_period
            print(f"API key blocked due to rate limit: {api_key[-6:]}...")
    
    def get_status(self) -> Dict[str, Any]:
        """全APIキーの状態を取得"""
        current_time = time.time()
        status = {
            "total_keys": len(self.api_keys),
            "keys": []
        }
        
        for i, key in enumerate(self.api_keys):
            key_status = {
                "index": i,
                "key_suffix": key[-6:],  # セキュリティのため末尾のみ表示
                "usage_count": self.usage_counts[key],
                "error_count": self.error_counts[key],
                "is_blocked": self.blocked_until[key] > current_time,
                "blocked_until": self.blocked_until[key] if self.blocked_until[key] > current_time else None,
                "last_used": self.last_used[key]
            }
            status["keys"].append(key_status)
        
        return status
    
    def reset_daily_counters(self):
        """日次カウンターをリセット（cronジョブなどで実行）"""
        self.usage_counts.clear()
        self.error_counts.clear()
        print("Daily counters reset")


# グローバルインスタンス（遅延初期化）
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """
    APIKeyManagerのインスタンスを取得（遅延初期化）
    初回アクセス時にインスタンスを生成
    """
    global _api_key_manager
    
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    
    return _api_key_manager


def get_google_api_key() -> str:
    """
    アプリケーションから呼び出す関数
    自動的に最適なAPIキーを選択して返す
    """
    manager = get_api_key_manager()
    key = manager.get_next_key()
    if not key:
        raise Exception("No available API keys")
    return key


def handle_api_error(api_key: str, error: Exception):
    """
    APIエラーが発生した際に呼び出す関数
    """
    manager = get_api_key_manager()
    manager.record_error(api_key, error)


def record_api_usage(api_key: str):
    """
    API使用成功時に呼び出す関数
    """
    manager = get_api_key_manager()
    manager.record_usage(api_key)