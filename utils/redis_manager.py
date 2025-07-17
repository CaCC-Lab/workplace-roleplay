# utils/redis_manager.py
import os
import redis
from typing import Optional, Any, Dict
import json
import logging
from datetime import timedelta
from functools import wraps

logger = logging.getLogger(__name__)

class RedisConnectionError(Exception):
    """Redis接続エラー専用例外"""
    pass

class RedisSessionManager:
    """
    Redisセッション管理のラッパークラス
    
    エラーハンドリングの3要素を含む:
    - 何が起きたか（What）
    - なぜ起きたか（Why）
    - どうすればよいか（How）
    """
    
    def __init__(self, 
                 host: str = None, 
                 port: int = None, 
                 db: int = 0,
                 fallback_enabled: bool = True):
        """
        Redis Session Managerの初期化
        
        Args:
            host: Redisサーバーのホスト
            port: Redisサーバーのポート
            db: 使用するRedisデータベース番号
            fallback_enabled: フォールバック機能を有効にするか
        """
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', 6379))
        self.db = db
        self.fallback_enabled = fallback_enabled
        self._client = None
        self._is_connected = False
        self._fallback_storage = {}  # インメモリフォールバック
        
        self._connect()
    
    def _connect(self) -> None:
        """Redisへの接続を確立"""
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                max_connections=10
            )
            # 接続テスト
            self._client.ping()
            self._is_connected = True
            logger.info(f"✅ Redisに接続しました: {self.host}:{self.port}")
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            self._is_connected = False
            error_msg = self._format_connection_error(str(e))
            
            if self.fallback_enabled:
                logger.warning(f"⚠️ Redis接続失敗、フォールバックモードで継続: {error_msg}")
            else:
                logger.error(f"❌ Redis接続失敗: {error_msg}")
                raise RedisConnectionError(error_msg) from e
    
    def _format_connection_error(self, error_detail: str) -> str:
        """接続エラーメッセージを3要素形式でフォーマット"""
        return (
            f"Redisサーバーに接続できません。"
            f"原因: {self.host}:{self.port}のRedisサーバーが起動していない、"
            f"またはネットワーク接続に問題があります（詳細: {error_detail}）。"
            f"対処法: 1) Redisサーバーが起動しているか確認 "
            f"2) docker-compose up -d redis コマンドでRedisを起動 "
            f"3) ファイアウォール設定を確認してください。"
        )
    
    def _with_fallback(func):
        """フォールバック機能付きデコレータ"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                if self._is_connected:
                    return func(self, *args, **kwargs)
                elif self.fallback_enabled:
                    return self._fallback_operation(func.__name__, *args, **kwargs)
                else:
                    raise RedisConnectionError("Redis接続が無効で、フォールバックも無効です")
            except redis.RedisError as e:
                if self.fallback_enabled:
                    logger.warning(f"Redis操作失敗、フォールバックを使用: {str(e)}")
                    return self._fallback_operation(func.__name__, *args, **kwargs)
                else:
                    raise
        return wrapper
    
    def _fallback_operation(self, operation: str, *args, **kwargs) -> Any:
        """フォールバック操作（インメモリストレージ使用）"""
        if operation == 'get':
            key = args[0] if args else kwargs.get('key')
            return self._fallback_storage.get(key)
        elif operation == 'set':
            key = args[0] if args else kwargs.get('key')
            value = args[1] if len(args) > 1 else kwargs.get('value')
            self._fallback_storage[key] = value
            return True
        elif operation == 'delete':
            key = args[0] if args else kwargs.get('key')
            return self._fallback_storage.pop(key, None) is not None
        elif operation == 'exists':
            key = args[0] if args else kwargs.get('key')
            return key in self._fallback_storage
        elif operation == 'clear_pattern':
            pattern = args[0] if args else kwargs.get('pattern')
            keys_to_remove = [k for k in self._fallback_storage.keys() if pattern in k]
            for k in keys_to_remove:
                del self._fallback_storage[k]
            return len(keys_to_remove)
        return None
    
    @_with_fallback
    def get(self, key: str) -> Optional[Any]:
        """キーに対応する値を取得"""
        try:
            value = self._client.get(key)
            if value:
                try:
                    # JSON形式でデシリアライズを試行
                    return json.loads(value)
                except json.JSONDecodeError:
                    # JSONでない場合はそのまま返す
                    return value
            return None
        except redis.RedisError as e:
            self._log_redis_error("データ取得", str(e))
            raise
    
    @_with_fallback
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """キーと値のペアを保存"""
        try:
            # 複雑なオブジェクトはJSON化
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)
            
            if expire:
                return bool(self._client.setex(key, expire, value))
            else:
                return bool(self._client.set(key, value))
        except redis.RedisError as e:
            self._log_redis_error("データ保存", str(e))
            raise
    
    @_with_fallback
    def delete(self, key: str) -> bool:
        """キーを削除"""
        try:
            return bool(self._client.delete(key))
        except redis.RedisError as e:
            self._log_redis_error("データ削除", str(e))
            raise
    
    @_with_fallback
    def exists(self, key: str) -> bool:
        """キーの存在確認"""
        try:
            return bool(self._client.exists(key))
        except redis.RedisError as e:
            return False
    
    @_with_fallback
    def clear_pattern(self, pattern: str) -> int:
        """パターンに一致するキーをすべて削除"""
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except redis.RedisError as e:
            self._log_redis_error("パターン削除", str(e))
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """Redisの健全性チェック"""
        result = {
            'connected': False,
            'fallback_active': not self._is_connected and self.fallback_enabled,
            'error': None
        }
        
        try:
            if self._client:
                self._client.ping()
                result['connected'] = True
                result['info'] = {
                    'host': self.host,
                    'port': self.port,
                    'db': self.db
                }
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def has_fallback(self) -> bool:
        """フォールバック機能が有効かどうか"""
        return self.fallback_enabled
    
    def _log_redis_error(self, operation: str, error_detail: str) -> None:
        """Redis操作エラーのログ出力"""
        error_msg = (
            f"Redis{operation}エラー。"
            f"原因: ネットワーク接続またはRedisサーバーの問題（{error_detail}）。"
            f"対処法: Redisサーバーの状態を確認し、必要に応じて再起動してください。"
        )
        logger.error(error_msg)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """接続情報を取得"""
        return {
            'host': self.host,
            'port': self.port,
            'db': self.db,
            'connected': self._is_connected,
            'fallback_enabled': self.fallback_enabled,
            'fallback_items': len(self._fallback_storage) if self.fallback_enabled else 0
        }


class SessionConfig:
    """Redis Session設定クラス"""
    
    @staticmethod
    def get_redis_config(environment: str = None) -> Dict[str, Any]:
        """環境に応じたRedis設定を返す"""
        env = environment or os.getenv('FLASK_ENV', 'development')
        
        base_config = {
            'SESSION_TYPE': 'redis',
            'SESSION_PERMANENT': False,
            'SESSION_USE_SIGNER': True,
            'SESSION_KEY_PREFIX': 'workplace-roleplay:',
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': timedelta(hours=24)
        }
        
        if env == 'production':
            base_config.update({
                'SESSION_COOKIE_SECURE': True,
                'SESSION_COOKIE_DOMAIN': os.getenv('SESSION_DOMAIN'),
                'PERMANENT_SESSION_LIFETIME': timedelta(hours=12)  # 本番では短く
            })
        else:
            base_config.update({
                'SESSION_COOKIE_SECURE': False,
                'PERMANENT_SESSION_LIFETIME': timedelta(days=7)  # 開発では長く
            })
        
        return base_config
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> None:
        """設定の妥当性を検証"""
        required_keys = ['SESSION_TYPE', 'SESSION_USE_SIGNER', 'SESSION_KEY_PREFIX']
        
        for key in required_keys:
            if key not in config:
                raise ValueError(
                    f"必須設定項目が不足しています: {key}。"
                    f"原因: Redis設定の初期化が不完全です。"
                    f"対処法: SessionConfig.get_redis_config()を使用して設定を取得してください。"
                )
        
        if config.get('SESSION_COOKIE_SECURE') and os.getenv('FLASK_ENV') != 'production':
            logger.warning(
                "開発環境でセキュアクッキーが有効です。"
                "HTTPS接続でない場合、セッションが正常に動作しない可能性があります。"
            )