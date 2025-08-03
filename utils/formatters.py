"""
データのフォーマット関連のユーティリティ関数
"""
import json
from datetime import datetime, timedelta
from typing import Any, Optional


def escape_for_json(text: str) -> str:
    """
    JSONで安全に使用できるように文字列をエスケープ
    
    Args:
        text: エスケープする文字列
        
    Returns:
        エスケープされた文字列
    """
    if not isinstance(text, str):
        return str(text)
    
    # JSONエンコードしてからデコード（ダブルクォートを除去）
    escaped = json.dumps(text)[1:-1]
    return escaped


def format_datetime(value: Optional[str]) -> str:
    """
    ISO形式の日時文字列をより読みやすい形式に変換
    
    Args:
        value: ISO形式の日時文字列
        
    Returns:
        フォーマットされた日時文字列
    """
    if not value:
        return "なし"
    
    try:
        # ISO形式の文字列をdatetimeオブジェクトに変換
        dt = datetime.fromisoformat(value)
        # 日本語形式でフォーマット
        return dt.strftime('%Y年%m月%d日 %H:%M')
    except (ValueError, TypeError):
        return str(value)


def format_duration(seconds: Optional[float]) -> str:
    """
    秒数を人間が読みやすい形式に変換
    
    Args:
        seconds: 秒数
        
    Returns:
        フォーマットされた時間文字列
    """
    if seconds is None:
        return "不明"
    
    if seconds < 60:
        return f"{int(seconds)}秒"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        remaining_seconds = int(seconds % 60)
        if remaining_seconds > 0:
            return f"{minutes}分{remaining_seconds}秒"
        return f"{minutes}分"
    else:
        hours = int(seconds / 3600)
        remaining_minutes = int((seconds % 3600) / 60)
        if remaining_minutes > 0:
            return f"{hours}時間{remaining_minutes}分"
        return f"{hours}時間"


def format_file_size(bytes_size: int) -> str:
    """
    バイト数を人間が読みやすい形式に変換
    
    Args:
        bytes_size: バイト数
        
    Returns:
        フォーマットされたサイズ文字列
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    長いテキストを切り詰める
    
    Args:
        text: 切り詰めるテキスト
        max_length: 最大文字数
        suffix: 末尾に追加する文字列
        
    Returns:
        切り詰められたテキスト
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix