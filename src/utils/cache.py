"""キャッシュユーティリティ"""
from functools import wraps, lru_cache
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional
import hashlib
import json


def timed_cache(seconds: int = 300) -> Callable:
    """時間制限付きキャッシュデコレータ
    
    Args:
        seconds: キャッシュの有効期限（秒）
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        cache: Dict[str, tuple[Any, datetime]] = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # キャッシュキーの生成
            key = _generate_cache_key(func.__name__, args, kwargs)
            
            # キャッシュの確認
            if key in cache:
                result, timestamp = cache[key]
                if datetime.now() - timestamp < timedelta(seconds=seconds):
                    return result
            
            # 関数の実行
            result = func(*args, **kwargs)
            
            # キャッシュに保存
            cache[key] = (result, datetime.now())
            
            # 古いキャッシュの削除
            _cleanup_cache(cache, seconds)
            
            return result
        
        # キャッシュクリア関数を追加
        wrapper.clear_cache = lambda: cache.clear()
        
        return wrapper
    
    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """キャッシュキーを生成
    
    Args:
        func_name: 関数名
        args: 位置引数
        kwargs: キーワード引数
        
    Returns:
        キャッシュキー
    """
    # 引数を文字列化
    key_parts = [func_name]
    
    # 位置引数
    for arg in args:
        key_parts.append(_serialize_arg(arg))
    
    # キーワード引数（ソート済み）
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={_serialize_arg(v)}")
    
    # ハッシュ化
    key_str = "|".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def _serialize_arg(arg: Any) -> str:
    """引数をシリアライズ
    
    Args:
        arg: 引数
        
    Returns:
        シリアライズされた文字列
    """
    if isinstance(arg, (str, int, float, bool, type(None))):
        return str(arg)
    elif isinstance(arg, (list, tuple, dict)):
        return json.dumps(arg, sort_keys=True)
    else:
        # その他のオブジェクトはreprを使用
        return repr(arg)


def _cleanup_cache(
    cache: Dict[str, tuple[Any, datetime]],
    seconds: int
) -> None:
    """期限切れのキャッシュを削除
    
    Args:
        cache: キャッシュ辞書
        seconds: 有効期限（秒）
    """
    now = datetime.now()
    expired_keys = [
        key for key, (_, timestamp) in cache.items()
        if now - timestamp >= timedelta(seconds=seconds)
    ]
    
    for key in expired_keys:
        del cache[key]


# メモリキャッシュクラス
class MemoryCache:
    """シンプルなメモリキャッシュ"""
    
    def __init__(self, default_timeout: int = 300):
        self._cache: Dict[str, tuple[Any, datetime, Optional[int]]] = {}
        self._default_timeout = default_timeout
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュから値を取得
        
        Args:
            key: キャッシュキー
            
        Returns:
            キャッシュされた値（存在しない場合はNone）
        """
        if key not in self._cache:
            return None
        
        value, timestamp, timeout = self._cache[key]
        
        # タイムアウトチェック
        if timeout is not None:
            if datetime.now() - timestamp > timedelta(seconds=timeout):
                del self._cache[key]
                return None
        
        return value
    
    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None
    ) -> None:
        """キャッシュに値を設定
        
        Args:
            key: キャッシュキー
            value: 値
            timeout: タイムアウト（秒）
        """
        if timeout is None:
            timeout = self._default_timeout
        
        self._cache[key] = (value, datetime.now(), timeout)
    
    def delete(self, key: str) -> bool:
        """キャッシュから削除
        
        Args:
            key: キャッシュキー
            
        Returns:
            削除に成功した場合True
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """キャッシュをクリア"""
        self._cache.clear()
    
    def cleanup(self) -> int:
        """期限切れのエントリを削除
        
        Returns:
            削除されたエントリ数
        """
        now = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp, timeout) in self._cache.items():
            if timeout is not None:
                if now - timestamp > timedelta(seconds=timeout):
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)