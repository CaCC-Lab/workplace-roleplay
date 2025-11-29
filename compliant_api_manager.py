"""
規約準拠APIキー管理システム
Google Gemini API利用規約に完全準拠した実装
"""

import os
import time
from typing import Optional, Dict, Any, Tuple
import asyncio
from collections import defaultdict


class CompliantAPIManager:
    """
    Google Gemini API利用規約に完全準拠したAPIキー管理システム
    - レート制限の厳格遵守
    - 単一APIキーでの適切な使用
    - エラー時の適切な待機処理
    """
    
    def __init__(self):
        self.api_key = self._load_single_api_key()
        self.request_history = []  # リクエスト履歴（時刻のリスト）
        self.last_error_time = 0
        self.consecutive_errors = 0
        
        # 規約準拠のレート制限設定（保守的な値）
        self.max_requests_per_minute = 10  # 公式制限より低く設定
        self.max_requests_per_hour = 600   # 公式制限より低く設定
        self.error_backoff_base = 2        # エラー時のバックオフ基底値（秒）
        self.max_backoff_seconds = 300     # 最大待機時間（5分）
    
    def _load_single_api_key(self) -> str:
        """
        単一のAPIキーを環境変数から読み込む
        規約準拠: 複数キーのローテーション使用を避ける
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is required. "
                "Please obtain a single API key from Google AI Studio."
            )
        return api_key
    
    def _clean_old_requests(self):
        """古いリクエスト履歴をクリーンアップ"""
        current_time = time.time()
        # 1時間より古い履歴を削除
        self.request_history = [
            timestamp for timestamp in self.request_history
            if current_time - timestamp < 3600
        ]
    
    def _can_make_request(self) -> Tuple[bool, Optional[float]]:
        """
        リクエスト可能かチェック
        Returns:
            (can_request, wait_seconds)
        """
        current_time = time.time()
        self._clean_old_requests()
        
        # エラー発生後のバックオフ期間チェック
        if self.consecutive_errors > 0:
            backoff_time = min(
                self.error_backoff_base ** self.consecutive_errors,
                self.max_backoff_seconds
            )
            time_since_error = current_time - self.last_error_time
            if time_since_error < backoff_time:
                return False, backoff_time - time_since_error
        
        # 分単位のレート制限チェック
        recent_requests = [
            t for t in self.request_history
            if current_time - t < 60  # 過去1分間
        ]
        if len(recent_requests) >= self.max_requests_per_minute:
            # 最も古いリクエストから1分経過するまで待機
            wait_time = 60 - (current_time - min(recent_requests))
            return False, wait_time
        
        # 時間単位のレート制限チェック
        if len(self.request_history) >= self.max_requests_per_hour:
            # 最も古いリクエストから1時間経過するまで待機
            wait_time = 3600 - (current_time - min(self.request_history))
            return False, wait_time
        
        return True, None
    
    def get_api_key(self) -> str:
        """
        規約準拠のAPIキー取得
        レート制限を厳格に遵守
        """
        can_request, wait_seconds = self._can_make_request()
        
        if not can_request and wait_seconds:
            raise RateLimitException(
                f"Rate limit exceeded. Please wait {wait_seconds:.1f} seconds. "
                f"This helps maintain compliance with Google's terms of service."
            )
        
        # リクエスト履歴に記録
        self.request_history.append(time.time())
        return self.api_key
    
    def record_success(self):
        """
        API呼び出し成功時に呼び出す
        エラーカウンターをリセット
        """
        self.consecutive_errors = 0
    
    def record_error(self, error: Exception):
        """
        APIエラー発生時の適切な処理
        規約準拠: エラー時は適切な待機を行う
        """
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        
        error_str = str(error).lower()
        
        # レート制限エラーの場合、特に長い待機時間を設定
        if any(keyword in error_str for keyword in [
            'rate limit', '429', 'quota exceeded', 'too many requests'
        ]):
            # Google推奨: Exponential backoffを実装
            self.consecutive_errors = min(self.consecutive_errors, 5)  # 最大5回まで
            
        print(f"API error recorded. Consecutive errors: {self.consecutive_errors}")
        print(f"Implementing exponential backoff as per Google's best practices.")
    
    def record_successful_request(self, api_key: str) -> None:
        """
        成功したリクエストを記録
        
        Args:
            api_key: 使用したAPIキー（互換性のため保持、現在は単一キーのみ使用）
        """
        # リクエスト履歴に追加（get_api_key()で既に追加されているが、明示的に記録）
        current_time = time.time()
        if not self.request_history or self.request_history[-1] != current_time:
            self.request_history.append(current_time)
        
        # 連続エラー回数をリセット
        self.consecutive_errors = 0
    
    def record_failed_request(self, api_key: str, error: Exception) -> None:
        """
        失敗したリクエストを記録
        
        Args:
            api_key: 使用したAPIキー（互換性のため保持、現在は単一キーのみ使用）
            error: 発生したエラー
        """
        # 連続エラー回数をインクリメント
        self.consecutive_errors += 1
        
        # 最終エラー時刻を更新
        self.last_error_time = time.time()
        
        # エラーの種類に応じた処理
        error_str = str(error).lower()
        
        # レート制限エラーの場合、特に長い待機時間を設定
        if any(keyword in error_str for keyword in [
            'rate limit', '429', 'quota exceeded', 'too many requests'
        ]):
            # Google推奨: Exponential backoffを実装
            self.consecutive_errors = min(self.consecutive_errors, 5)  # 最大5回まで
        
        print(f"API failed request recorded. Consecutive errors: {self.consecutive_errors}")
        print(f"Implementing exponential backoff as per Google's best practices.")
    
    def get_status(self) -> Dict[str, Any]:
        """現在の状態情報を取得"""
        current_time = time.time()
        self._clean_old_requests()
        
        can_request, wait_seconds = self._can_make_request()
        
        recent_requests_1min = len([
            t for t in self.request_history
            if current_time - t < 60
        ])
        
        return {
            "api_key_suffix": self.api_key[-6:] if self.api_key else "None",
            "can_make_request": can_request,
            "wait_seconds": wait_seconds,
            "requests_last_minute": recent_requests_1min,
            "requests_last_hour": len(self.request_history),
            "consecutive_errors": self.consecutive_errors,
            "compliant_implementation": True,
            "rate_limits": {
                "per_minute": self.max_requests_per_minute,
                "per_hour": self.max_requests_per_hour
            }
        }


class RateLimitException(Exception):
    """レート制限エラーを表す例外クラス"""
    pass


# 使用例とベストプラクティス
def create_compliant_gemini_client():
    """
    規約準拠のGemini APIクライアント作成例
    """
    manager = CompliantAPIManager()
    
    try:
        api_key = manager.get_api_key()
        # GoogleのChatGoogleGenerativeAIクライアントを作成
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        client = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",  # 推奨モデル
            google_api_key=api_key,
            temperature=0.7,
            max_tokens=1000,
            timeout=30,  # 適切なタイムアウト設定
            max_retries=2,  # Google推奨の再試行回数
        )
        
        manager.record_success()
        return client, manager
        
    except RateLimitException as e:
        print(f"Rate limit compliance: {e}")
        raise
    except Exception as e:
        manager.record_error(e)
        print(f"API error: {e}")
        raise


# グローバル管理インスタンス
_compliant_manager: Optional[CompliantAPIManager] = None


def get_compliant_api_manager() -> CompliantAPIManager:
    """規約準拠のAPIマネージャーを取得"""
    global _compliant_manager
    if _compliant_manager is None:
        _compliant_manager = CompliantAPIManager()
    return _compliant_manager


def get_compliant_google_api_key() -> str:
    """
    規約準拠のGoogle API キー取得
    レート制限を厳格に遵守
    """
    manager = get_compliant_api_manager()
    return manager.get_api_key()


def record_compliant_api_usage():
    """API使用成功をマネージャーに記録"""
    manager = get_compliant_api_manager()
    manager.record_success()


def handle_compliant_api_error(error: Exception):
    """規約準拠のエラーハンドリング"""
    manager = get_compliant_api_manager()
    manager.record_error(error)