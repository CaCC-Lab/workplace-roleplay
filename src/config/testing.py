"""テスト環境設定"""
from .base import Config


class TestingConfig(Config):
    """テスト環境の設定"""
    
    TESTING = True
    DEBUG = True
    
    # テスト用のデータベース（インメモリ）
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    
    # テスト用の設定
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True
    
    # テスト用のシークレットキー
    SECRET_KEY = "test-secret-key"
    
    # テスト用のAPIキー（ダミー）
    GOOGLE_API_KEY = "test-api-key"
    
    # ログレベル
    LOG_LEVEL = "ERROR"