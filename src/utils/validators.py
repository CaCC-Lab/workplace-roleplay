"""バリデーションユーティリティ"""
import re
from typing import Optional


def validate_message(message: str, max_length: int = 5000) -> Optional[str]:
    """メッセージのバリデーション
    
    Args:
        message: メッセージ
        max_length: 最大文字数
        
    Returns:
        エラーメッセージ（問題ない場合はNone）
    """
    if not message:
        return "メッセージが空です"
    
    if not isinstance(message, str):
        return "メッセージは文字列である必要があります"
    
    # 空白のみのチェック
    if not message.strip():
        return "メッセージが空白のみです"
    
    # 長さチェック
    if len(message) > max_length:
        return f"メッセージが長すぎます（最大{max_length}文字）"
    
    # 危険な文字のチェック
    if contains_dangerous_characters(message):
        return "使用できない文字が含まれています"
    
    return None


def validate_model_name(model_name: str, allowed_models: list) -> Optional[str]:
    """モデル名のバリデーション
    
    Args:
        model_name: モデル名
        allowed_models: 許可されたモデルのリスト
        
    Returns:
        エラーメッセージ（問題ない場合はNone）
    """
    if not model_name:
        return "モデル名が指定されていません"
    
    if not isinstance(model_name, str):
        return "モデル名は文字列である必要があります"
    
    if model_name not in allowed_models:
        return f"無効なモデル名です: {model_name}"
    
    return None


def validate_scenario_id(scenario_id: str) -> Optional[str]:
    """シナリオIDのバリデーション
    
    Args:
        scenario_id: シナリオID
        
    Returns:
        エラーメッセージ（問題ない場合はNone）
    """
    if not scenario_id:
        return "シナリオIDが指定されていません"
    
    if not isinstance(scenario_id, str):
        return "シナリオIDは文字列である必要があります"
    
    # 英数字とアンダースコア、ハイフンのみ許可
    if not re.match(r"^[a-zA-Z0-9_-]+$", scenario_id):
        return "シナリオIDに使用できない文字が含まれています"
    
    # 長さチェック
    if len(scenario_id) > 50:
        return "シナリオIDが長すぎます（最大50文字）"
    
    return None


def contains_dangerous_characters(text: str) -> bool:
    """危険な文字が含まれているかチェック
    
    Args:
        text: チェックするテキスト
        
    Returns:
        危険な文字が含まれている場合True
    """
    # Null文字
    if "\x00" in text:
        return True
    
    # 制御文字（改行とタブは除く）
    for char in text:
        if ord(char) < 32 and char not in ["\n", "\r", "\t"]:
            return True
    
    return False


def sanitize_filename(filename: str) -> str:
    """ファイル名をサニタイズ
    
    Args:
        filename: ファイル名
        
    Returns:
        サニタイズされたファイル名
    """
    # 危険な文字を除去
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)
    
    # 制御文字を除去
    filename = "".join(char for char in filename if ord(char) >= 32)
    
    # 先頭と末尾の空白とドットを除去
    filename = filename.strip(". ")
    
    # 空になった場合はデフォルト名
    if not filename:
        filename = "unnamed"
    
    # 長さ制限
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        name = name[:255 - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name
    
    return filename


def validate_email(email: str) -> Optional[str]:
    """メールアドレスのバリデーション
    
    Args:
        email: メールアドレス
        
    Returns:
        エラーメッセージ（問題ない場合はNone）
    """
    if not email:
        return "メールアドレスが指定されていません"
    
    if not isinstance(email, str):
        return "メールアドレスは文字列である必要があります"
    
    # 基本的なメールアドレスパターン
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return "無効なメールアドレス形式です"
    
    # 長さチェック
    if len(email) > 254:
        return "メールアドレスが長すぎます"
    
    return None