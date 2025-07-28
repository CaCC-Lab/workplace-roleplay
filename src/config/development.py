"""開発環境設定"""
from .base import Config


class DevelopmentConfig(Config):
    """開発環境の設定"""
    
    DEBUG = True
    TESTING = False
    
    # 開発環境では詳細なエラーを表示
    PROPAGATE_EXCEPTIONS = True
    
    # ホットリロード有効
    TEMPLATES_AUTO_RELOAD = True
    
    # セッションクッキーの設定（開発環境）
    SESSION_COOKIE_SECURE = False
    
    # 開発用のログレベル
    LOG_LEVEL = "DEBUG"
    
    # 開発環境では警告を表示
    SQLALCHEMY_ECHO = True
    
    # 開発環境ではCSRFチェックを無効化（テスト用）
    WTF_CSRF_ENABLED = False