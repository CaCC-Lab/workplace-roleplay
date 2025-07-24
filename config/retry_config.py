"""
リトライ機構の設定ファイル
"""
import os
from typing import Dict, Any

class RetryConfiguration:
    """リトライ設定を管理するクラス"""
    
    def __init__(self):
        # 環境変数から設定を読み込み
        self.RETRY_ENABLED = os.getenv('CELERY_RETRY_ENABLED', 'true').lower() == 'true'
        
        # デフォルトリトライ設定
        self.DEFAULT_MAX_RETRIES = int(os.getenv('CELERY_DEFAULT_MAX_RETRIES', '3'))
        self.DEFAULT_BASE_DELAY = int(os.getenv('CELERY_DEFAULT_BASE_DELAY', '2'))
        self.DEFAULT_MAX_DELAY = int(os.getenv('CELERY_DEFAULT_MAX_DELAY', '300'))
        self.DEFAULT_BACKOFF_MULTIPLIER = float(os.getenv('CELERY_DEFAULT_BACKOFF_MULTIPLIER', '2.0'))
        
        # エラータイプ別設定
        self.ERROR_TYPE_CONFIGS = {
            'RateLimitError': {
                'max_retries': int(os.getenv('RETRY_RATE_LIMIT_MAX_RETRIES', '5')),
                'base_delay': int(os.getenv('RETRY_RATE_LIMIT_BASE_DELAY', '60')),
                'max_delay': int(os.getenv('RETRY_RATE_LIMIT_MAX_DELAY', '600')),
                'backoff_multiplier': float(os.getenv('RETRY_RATE_LIMIT_BACKOFF', '1.5')),
            },
            'NetworkError': {
                'max_retries': int(os.getenv('RETRY_NETWORK_MAX_RETRIES', '4')),
                'base_delay': int(os.getenv('RETRY_NETWORK_BASE_DELAY', '1')),
                'max_delay': int(os.getenv('RETRY_NETWORK_MAX_DELAY', '30')),
                'backoff_multiplier': float(os.getenv('RETRY_NETWORK_BACKOFF', '2.0')),
            },
            'ServiceUnavailableError': {
                'max_retries': int(os.getenv('RETRY_SERVICE_MAX_RETRIES', '3')),
                'base_delay': int(os.getenv('RETRY_SERVICE_BASE_DELAY', '30')),
                'max_delay': int(os.getenv('RETRY_SERVICE_MAX_DELAY', '300')),
                'backoff_multiplier': float(os.getenv('RETRY_SERVICE_BACKOFF', '2.0')),
            }
        }
        
        # 部分レスポンス設定
        self.PARTIAL_RESPONSE_TTL = int(os.getenv('PARTIAL_RESPONSE_TTL', '3600'))  # 1時間
        self.PARTIAL_RESPONSE_ENABLED = os.getenv('PARTIAL_RESPONSE_ENABLED', 'true').lower() == 'true'
        
        # 進捗監視設定
        self.PROGRESS_MONITORING_TIMEOUT = int(os.getenv('PROGRESS_MONITORING_TIMEOUT', '600'))  # 10分
        self.PROGRESS_CLEANUP_INTERVAL = int(os.getenv('PROGRESS_CLEANUP_INTERVAL', '3600'))   # 1時間
        
        # Redis設定
        self.REDIS_KEY_PREFIX = os.getenv('REDIS_RETRY_PREFIX', 'retry:')
        self.REDIS_PROGRESS_PREFIX = os.getenv('REDIS_PROGRESS_PREFIX', 'task_progress:')
        self.REDIS_PARTIAL_PREFIX = os.getenv('REDIS_PARTIAL_PREFIX', 'partial_response:')
        
        # ログ設定
        self.LOG_RETRY_ATTEMPTS = os.getenv('LOG_RETRY_ATTEMPTS', 'true').lower() == 'true'
        self.LOG_PARTIAL_RESPONSES = os.getenv('LOG_PARTIAL_RESPONSES', 'false').lower() == 'true'
        
        # メトリクス設定
        self.COLLECT_RETRY_METRICS = os.getenv('COLLECT_RETRY_METRICS', 'true').lower() == 'true'
        self.METRICS_RETENTION_DAYS = int(os.getenv('METRICS_RETENTION_DAYS', '30'))
    
    def get_error_config(self, error_type: str) -> Dict[str, Any]:
        """エラータイプに応じた設定を取得"""
        return self.ERROR_TYPE_CONFIGS.get(error_type, {
            'max_retries': self.DEFAULT_MAX_RETRIES,
            'base_delay': self.DEFAULT_BASE_DELAY,
            'max_delay': self.DEFAULT_MAX_DELAY,
            'backoff_multiplier': self.DEFAULT_BACKOFF_MULTIPLIER,
        })
    
    def is_retry_enabled(self) -> bool:
        """リトライ機能が有効かどうか"""
        return self.RETRY_ENABLED
    
    def get_redis_key(self, key_type: str, identifier: str) -> str:
        """Redis キーを生成"""
        prefixes = {
            'retry': self.REDIS_KEY_PREFIX,
            'progress': self.REDIS_PROGRESS_PREFIX,
            'partial': self.REDIS_PARTIAL_PREFIX,
        }
        
        prefix = prefixes.get(key_type, self.REDIS_KEY_PREFIX)
        return f"{prefix}{identifier}"
    
    def to_dict(self) -> Dict[str, Any]:
        """設定を辞書形式で取得（デバッグ用）"""
        return {
            'retry_enabled': self.RETRY_ENABLED,
            'default_max_retries': self.DEFAULT_MAX_RETRIES,
            'default_base_delay': self.DEFAULT_BASE_DELAY,
            'default_max_delay': self.DEFAULT_MAX_DELAY,
            'default_backoff_multiplier': self.DEFAULT_BACKOFF_MULTIPLIER,
            'error_type_configs': self.ERROR_TYPE_CONFIGS,
            'partial_response_ttl': self.PARTIAL_RESPONSE_TTL,
            'partial_response_enabled': self.PARTIAL_RESPONSE_ENABLED,
            'progress_monitoring_timeout': self.PROGRESS_MONITORING_TIMEOUT,
            'collect_retry_metrics': self.COLLECT_RETRY_METRICS,
        }


# グローバル設定インスタンス
retry_config = RetryConfiguration()


def validate_configuration():
    """設定の妥当性をチェック"""
    errors = []
    
    # 数値設定の妥当性チェック
    if retry_config.DEFAULT_MAX_RETRIES < 0:
        errors.append("DEFAULT_MAX_RETRIES must be >= 0")
    
    if retry_config.DEFAULT_BASE_DELAY < 1:
        errors.append("DEFAULT_BASE_DELAY must be >= 1")
    
    if retry_config.DEFAULT_MAX_DELAY < retry_config.DEFAULT_BASE_DELAY:
        errors.append("DEFAULT_MAX_DELAY must be >= DEFAULT_BASE_DELAY")
    
    if retry_config.DEFAULT_BACKOFF_MULTIPLIER < 1.0:
        errors.append("DEFAULT_BACKOFF_MULTIPLIER must be >= 1.0")
    
    # エラータイプ別設定のチェック
    for error_type, config in retry_config.ERROR_TYPE_CONFIGS.items():
        if config['max_retries'] < 0:
            errors.append(f"{error_type}.max_retries must be >= 0")
        
        if config['base_delay'] < 1:
            errors.append(f"{error_type}.base_delay must be >= 1")
        
        if config['max_delay'] < config['base_delay']:
            errors.append(f"{error_type}.max_delay must be >= base_delay")
    
    return errors


if __name__ == '__main__':
    # 設定の妥当性チェック
    validation_errors = validate_configuration()
    
    if validation_errors:
        print("設定エラー:")
        for error in validation_errors:
            print(f"  - {error}")
    else:
        print("設定は正常です")
        
        # 設定内容を表示
        import json
        print(json.dumps(retry_config.to_dict(), indent=2, ensure_ascii=False))