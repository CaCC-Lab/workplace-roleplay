"""基本設定クラス"""
import os
from datetime import timedelta
from typing import Optional

from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


class Config:
    """基本設定"""
    
    # Flask基本設定
    SECRET_KEY: str = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-this")
    
    # セッション設定
    SESSION_TYPE: str = "filesystem"
    SESSION_FILE_DIR: str = "./flask_session"
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(hours=24)
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    
    # データベース設定
    SQLALCHEMY_DATABASE_URI: Optional[str] = os.environ.get(
        "DATABASE_URL",
        "sqlite:///workplace_roleplay.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    
    # API設定
    GOOGLE_API_KEY: Optional[str] = os.environ.get("GOOGLE_API_KEY")
    API_TIMEOUT: int = 30
    API_MAX_RETRIES: int = 3
    
    # セキュリティ設定
    WTF_CSRF_ENABLED: bool = True
    WTF_CSRF_TIME_LIMIT: Optional[int] = None
    CSRF_ENABLED: bool = True
    
    # アプリケーション設定
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    JSON_AS_ASCII: bool = False
    JSON_SORT_KEYS: bool = False
    
    # ログ設定
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Redis設定（オプション）
    REDIS_URL: Optional[str] = os.environ.get(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )
    
    # キャッシュ設定
    CACHE_TYPE: str = "simple"
    CACHE_DEFAULT_TIMEOUT: int = 300
    
    # モデル設定（固定リスト）
    AVAILABLE_MODELS = [
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
        "gemini/gemini-1.5-pro-latest",
        "gemini/gemini-1.5-flash-latest"
    ]
    
    # デフォルトモデル
    DEFAULT_MODEL: str = "gemini/gemini-1.5-flash"
    
    # その他の設定
    PROPAGATE_EXCEPTIONS: bool = True
    TEMPLATES_AUTO_RELOAD: bool = True