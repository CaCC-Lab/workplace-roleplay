"""本番環境設定"""
import os
from .base import Config


class ProductionConfig(Config):
    """本番環境の設定"""
    
    DEBUG = False
    TESTING = False
    
    # 本番環境のセキュリティ設定
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    
    # 本番環境のログレベル
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")
    
    # SQLAlchemyの設定
    SQLALCHEMY_ECHO = False
    
    # 本番環境では必須
    if not Config.SECRET_KEY or Config.SECRET_KEY == "dev-secret-key-change-this":
        raise ValueError("SECRET_KEY must be set in production")
    
    # API Keyの確認
    if not Config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY must be set in production")