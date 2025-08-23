"""
アプリケーション設定モジュール
Pydanticを使用した型安全な設定管理
"""
import os
import json
import warnings
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ValidationError
from functools import lru_cache


class Config(BaseSettings):
    """基本設定クラス"""
    
    # Flask設定
    FLASK_ENV: str = Field(default="development", alias="FLASK_ENV")
    SECRET_KEY: str = Field(
        default="default-secret-key-change-in-production",
        alias="FLASK_SECRET_KEY"
    )
    DEBUG: bool = Field(default=False, alias="FLASK_DEBUG")
    TESTING: bool = Field(default=False, alias="TESTING")
    
    # API設定
    GOOGLE_API_KEY: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    DEFAULT_TEMPERATURE: float = Field(default=0.7, alias="DEFAULT_TEMPERATURE")
    DEFAULT_MODEL: str = Field(
        default="gemini/gemini-1.5-flash",
        alias="DEFAULT_MODEL"
    )
    API_BASE_URL: Optional[str] = Field(default=None, alias="API_BASE_URL")
    
    # セッション設定
    SESSION_TYPE: str = Field(default="filesystem", alias="SESSION_TYPE")
    SESSION_LIFETIME_MINUTES: int = Field(default=30, alias="SESSION_LIFETIME_MINUTES")
    SESSION_FILE_DIR: Optional[str] = Field(default=None, alias="SESSION_FILE_DIR")
    
    # Redis設定（セッションタイプがredisの場合）
    REDIS_HOST: str = Field(default="localhost", alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, alias="REDIS_PORT")
    REDIS_PASSWORD: str = Field(default="", alias="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, alias="REDIS_DB")
    
    # ログ設定
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", alias="LOG_FORMAT")
    
    # アプリケーション設定
    PORT: int = Field(default=5000, alias="PORT")
    HOST: str = Field(default="0.0.0.0", alias="HOST")
    HOT_RELOAD: bool = Field(default=False, alias="HOT_RELOAD")
    WTF_CSRF_ENABLED: bool = Field(default=True, alias="WTF_CSRF_ENABLED")
    SECURE_COOKIES: bool = Field(default=False, alias="SECURE_COOKIES")
    
    # 機能フラグ（段階的無効化）
    ENABLE_MODEL_SELECTION: bool = Field(default=True, alias="ENABLE_MODEL_SELECTION")
    ENABLE_TTS: bool = Field(default=True, alias="ENABLE_TTS")
    ENABLE_LEARNING_HISTORY: bool = Field(default=True, alias="ENABLE_LEARNING_HISTORY")
    ENABLE_STRENGTH_ANALYSIS: bool = Field(default=True, alias="ENABLE_STRENGTH_ANALYSIS")
    
    # その他のフラグ
    ENABLE_DEBUG: bool = Field(default=False, alias="ENABLE_DEBUG")
    
    # 機能フラグ（段階的無効化システム）
    ENABLE_MODEL_SELECTION: bool = Field(default=True, alias="ENABLE_MODEL_SELECTION")
    ENABLE_TTS: bool = Field(default=True, alias="ENABLE_TTS")
    ENABLE_LEARNING_HISTORY: bool = Field(default=True, alias="ENABLE_LEARNING_HISTORY")
    ENABLE_STRENGTH_ANALYSIS: bool = Field(default=True, alias="ENABLE_STRENGTH_ANALYSIS")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "allow",
        "populate_by_name": True
    }
    
    @field_validator("DEFAULT_TEMPERATURE")
    def validate_temperature(cls, v):
        """温度パラメータのバリデーション"""
        if not 0 <= v <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        return v
    
    @field_validator("SESSION_LIFETIME_MINUTES")
    def validate_session_lifetime(cls, v):
        """セッション有効期限のバリデーション"""
        if v <= 0:
            raise ValueError("Session lifetime must be positive")
        return v
    
    @field_validator("DEFAULT_MODEL")
    def validate_model(cls, v):
        """モデル名のバリデーション（動的パターンマッチング対応）"""
        import re
        
        # サポートされているモデルの明示的リスト（2024年12月最新）
        supported_models = [
            # Gemini 2.5系（最新）
            "gemini/gemini-2.5-pro",
            "gemini/gemini-2.5-flash",
            "gemini/gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            
            # Gemini 2.0系（現行）
            "gemini/gemini-2.0-flash",
            "gemini/gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            
            # Gemini 1.5系（レガシー）
            "gemini/gemini-1.5-pro",
            "gemini/gemini-1.5-flash",
            "gemini/gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b"
        ]
        
        # 明示的リストにある場合は即座に許可
        if v in supported_models:
            return v
        
        # 動的パターンマッチング（将来の拡張性）
        # gemini-X.Y-{pro|flash|flash-lite}[-variant]パターンをサポート
        gemini_pattern = re.compile(r'^(gemini/)?gemini-\d+\.\d+-(pro|flash|flash-lite)(-.*)?$')
        if gemini_pattern.match(v):
            warnings.warn(f"Using experimental model pattern: {v}. Please verify compatibility.", UserWarning)
            return v
        
        raise ValueError(f"Unsupported model: {v}")
        return v
    
    @field_validator("API_BASE_URL")
    def validate_url(cls, v):
        """URLのバリデーション"""
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Invalid URL format")
        return v
    
    @field_validator("PORT")
    def validate_port(cls, v):
        """ポート番号のバリデーション"""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """ログレベルのバリデーション"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()
    
    def to_dict(self, mask_secrets: bool = False) -> Dict[str, Any]:
        """設定を辞書形式で出力（機密情報を除外可能）"""
        data = self.model_dump()
        
        # 機密情報のフィールド
        secret_fields = ["SECRET_KEY", "GOOGLE_API_KEY", "REDIS_PASSWORD"]
        
        if mask_secrets:
            for field in secret_fields:
                if field in data and data[field]:
                    data[field] = "***"
        else:
            # 機密情報を完全に除外
            for field in secret_fields:
                data.pop(field, None)
        
        return data
    
    @classmethod
    def from_file(cls, file_path: str) -> "Config":
        """設定ファイルから読み込み"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            if file_path.endswith('.json'):
                file_config = json.load(f)
            else:
                raise ValueError("Only JSON config files are supported")
        
        # 環境変数を優先しつつファイルの値を適用
        # Pydanticは環境変数を自動的に優先するので、
        # ファイルの値は環境変数が設定されていない場合のみ使用される
        for key, value in file_config.items():
            if key not in os.environ:
                os.environ[key] = str(value)
        
        return cls()


class DevelopmentConfig(Config):
    """開発環境設定"""
    
    FLASK_ENV: str = Field(default="development")
    SECRET_KEY: str = Field(default="dev-secret-key-for-development-only", alias="FLASK_SECRET_KEY")
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    HOT_RELOAD: bool = True
    
    @field_validator("SECRET_KEY", mode="before")
    def set_dev_secret_key(cls, v):
        """開発環境用のデフォルトシークレットキー"""
        # 空文字列または None の場合、デフォルト値を設定
        if v is None or v == '':
            v = "dev-secret-key-for-development-only"
        
        # デフォルトキー使用時に警告
        if v in ["dev-secret-key-for-development-only", "default-secret-key-change-in-production"]:
            warnings.warn(
                "Using default SECRET_KEY in development. Never use this in production!",
                UserWarning,
                stacklevel=2
            )
        
        return v


class ProductionConfig(Config):
    """本番環境設定"""
    
    FLASK_ENV: str = Field(default="production")
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    HOT_RELOAD: bool = False
    SECURE_COOKIES: bool = True
    
    @field_validator("GOOGLE_API_KEY", mode="before")
    def require_api_key(cls, v):
        """本番環境ではAPIキーが必須"""
        if not v:
            raise ValueError("GOOGLE_API_KEY is required in production")
        return v
    
    @field_validator("SECRET_KEY", mode="before")
    def require_secret_key(cls, v):
        """本番環境では適切なシークレットキーが必須"""
        if not v or v == "default-secret-key-change-in-production":
            raise ValueError("A secure SECRET_KEY is required in production")
        
        # 最小長チェック（32文字以上推奨）
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long in production")
        
        # 単純なパターンのチェック（完全一致またはキー全体が単純な場合のみ）
        simple_patterns = [
            'password', 'secret', '12345678', 'password123', 'secret123',
            'admin', 'default', 'test', 'demo'
        ]
        # キー全体が単純なパターンの場合、または数字のみの場合
        if v.lower() in simple_patterns or v.isdigit() or len(set(v)) < 4:
            raise ValueError("SECRET_KEY is too simple and predictable")
        
        # 単純な繰り返しパターンのチェック
        if v.lower().startswith(('password', 'secret')) and v.lower().endswith(('123', '1234', '12345')):
            raise ValueError("SECRET_KEY is too simple and predictable")
        
        return v


class ConfigForTesting(Config):
    """テスト環境設定"""
    
    FLASK_ENV: str = Field(default="testing")
    TESTING: bool = Field(default=True)
    WTF_CSRF_ENABLED: bool = Field(default=False)
    SESSION_TYPE: str = Field(default="dict")  # メモリ内セッション
    LOG_LEVEL: str = Field(default="ERROR")  # テスト時は最小限のログ
    
    @field_validator("GOOGLE_API_KEY", mode="before")
    def optional_api_key(cls, v):
        """テスト環境ではAPIキーはオプション"""
        return v or "test-api-key"


def get_config() -> Config:
    """環境に応じた設定インスタンスを取得"""
    env = os.getenv("FLASK_ENV", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return ConfigForTesting()
    else:
        return DevelopmentConfig()

@lru_cache()
def get_cached_config() -> Config:
    """キャッシュされた設定インスタンスを取得"""
    return get_config()


# 機能フラグヘルパー関数
def get_feature_flags() -> dict:
    """現在の機能フラグ設定を取得"""
    config = get_cached_config()
    return {
        "model_selection": config.ENABLE_MODEL_SELECTION,
        "tts": config.ENABLE_TTS,
        "learning_history": config.ENABLE_LEARNING_HISTORY,
        "strength_analysis": config.ENABLE_STRENGTH_ANALYSIS,
        "default_model": config.DEFAULT_MODEL
    }

# エクスポート
__all__ = [
    "Config",
    "DevelopmentConfig",
    "ProductionConfig",
    "ConfigForTesting",
    "get_config",
    "get_cached_config",
    "get_feature_flags"
]