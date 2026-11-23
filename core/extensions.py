"""
Flask extensions initialization module.
Handles Session, Redis, and other extension setup.
"""

import os

from flask import Flask

from flask_session import Session

# Redis関連のインポート
from utils.redis_manager import RedisConnectionError, RedisSessionManager, SessionConfig
from utils.runtime import is_serverless, local_data_dir

# グローバル変数として保持（他のモジュールから参照可能）
redis_session_manager = None


def init_extensions(app: Flask, config=None):
    """
    Flask拡張の初期化

    Args:
        app: Flaskアプリケーションインスタンス
        config: 設定オブジェクト（オプション）

    Returns:
        RedisSessionManager or None: Redisセッションマネージャー（利用可能な場合）
    """
    global redis_session_manager

    # 設定の取得
    if config is None:
        from config import get_cached_config

        config = get_cached_config()

    if config.SESSION_TYPE == "supabase" and _setup_supabase_session(app):
        redis_session_manager = None
    else:
        # セッションストアの初期化
        redis_session_manager = _initialize_session_store(app, config)

        # Flask-Sessionの初期化
        Session(app)

    # Jinja2の自動エスケープを有効化（デフォルトで有効だが明示的に設定）
    app.jinja_env.autoescape = True

    return redis_session_manager


def _setup_supabase_session(app: Flask) -> bool:
    """
    Supabase にセッションを保存する（サーバーレス環境向け）

    Returns:
        bool: Supabase に接続できて設定できた場合 True
    """
    from services.supabase_client import get_supabase_client_manager
    from services.supabase_session import SupabaseSessionInterface

    client = get_supabase_client_manager().get_client()
    if client is None:
        print("⚠️ Supabaseに接続できないため、セッションの保存先を切り替えます")
        return False

    app.session_interface = SupabaseSessionInterface(client)
    if is_serverless():
        app.config["SESSION_COOKIE_SECURE"] = True
    print("✅ Supabaseセッションストアを使用します")
    return True


def _initialize_session_store(app: Flask, config):
    """
    セッションストアの初期化（Redis優先、フォールバック対応）

    Args:
        app: Flaskアプリケーションインスタンス
        config: 設定オブジェクト

    Returns:
        RedisSessionManager or None
    """
    try:
        # Redis設定を試行
        if config.SESSION_TYPE == "redis":
            redis_manager = RedisSessionManager(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                fallback_enabled=True,
            )

            # Redis接続確認
            health = redis_manager.health_check()

            if health["connected"]:
                # Redis設定をFlaskに適用
                redis_config = SessionConfig.get_redis_config(os.getenv("FLASK_ENV"))
                app.config.update(redis_config)
                app.config["SESSION_REDIS"] = redis_manager._client

                print("✅ Redisセッションストアを使用します")
                print(f"   接続先: {redis_manager.host}:{redis_manager.port}")
                return redis_manager
            else:
                print(f"⚠️ Redis接続失敗: {health.get('error', 'Unknown error')}")
                if redis_manager.has_fallback():
                    print("   フォールバック機能が有効です")
                    return redis_manager
                else:
                    raise RedisConnectionError("Redis接続失敗、フォールバック無効")

        # Filesystem フォールバック
        return _setup_filesystem_session(app, config)

    except ImportError as e:
        print(f"❌ Redis依存関係エラー: {str(e)}")
        print("   対処法: pip install redis を実行してください")
        return _setup_filesystem_session(app, config)
    except Exception as e:
        print(f"❌ セッション初期化エラー: {str(e)}")
        return _setup_filesystem_session(app, config)


def _setup_filesystem_session(app: Flask, config):
    """
    ファイルシステムベースのセッションをセットアップ

    Args:
        app: Flaskアプリケーションインスタンス
        config: 設定オブジェクト

    Returns:
        None
    """
    print("📁 Filesystemセッションにフォールバックします")
    app.config["SESSION_TYPE"] = "filesystem"

    default_dir = str(local_data_dir("flask_session")) if is_serverless() else "./flask_session"
    session_dir = getattr(config, "SESSION_FILE_DIR", None) or default_dir

    if not os.path.exists(session_dir):
        try:
            os.makedirs(session_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            print(f"⚠️ セッションディレクトリ作成失敗: {session_dir} - {str(e)}")
            session_dir = default_dir
            os.makedirs(session_dir, exist_ok=True)

    app.config["SESSION_FILE_DIR"] = session_dir
    return None


def get_redis_session_manager():
    """
    Redisセッションマネージャーを取得

    Returns:
        RedisSessionManager or None
    """
    return redis_session_manager
