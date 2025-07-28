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
        default=None,  # 環境変数からの読み込みを必須にする
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
    
    # その他のフラグ
    ENABLE_DEBUG: bool = Field(default=False, alias="ENABLE_DEBUG")
    
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
        """モデル名のバリデーション"""
        supported_models = [
            "gemini/gemini-1.5-pro",
            "gemini/gemini-1.5-flash"
        ]
        if v not in supported_models:
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
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    HOT_RELOAD: bool = True
    
    @field_validator("SECRET_KEY", mode="before")
    def validate_dev_secret_key(cls, v):
        """開発環境でもセキュアなシークレットキーを推奨"""
        if not v:
            raise ValueError(
                "SECRET_KEY (FLASK_SECRET_KEY) is required. "
                "Generate one with: python scripts/generate_secret_key.py"
            )
        
        # 弱いキーの検出と警告
        weak_patterns = [
            "dev-secret-key", "default-secret", "test-secret",
            "password", "secret", "12345", "admin", "demo"
        ]
        
        if any(pattern in v.lower() for pattern in weak_patterns):
            warnings.warn(
                f"SECRET_KEY appears to be weak. Consider using a stronger key "
                f"even in development environment.",
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
        if not v:
            raise ValueError(
                "A secure SECRET_KEY (FLASK_SECRET_KEY) is required in production. "
                "Generate one with: python scripts/generate_secret_key.py --length 64"
            )
        
        # 最小長チェック（32文字以上推奨）
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long in production")
        
        # 単純なパターンのチェック（完全一致またはキー全体が単純な場合のみ）
        simple_patterns = [
            'password', 'secret', '12345678', 'password123', 'secret123',
            'admin', 'default', 'test', 'demo', 'dev-secret-key',
            'default-secret-key-change-in-production'
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


# エクスポート
__all__ = [
    "Config",
    "DevelopmentConfig",
    "ProductionConfig",
    "ConfigForTesting",
    "get_config",
    "get_cached_config"
]