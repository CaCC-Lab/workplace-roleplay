"""
Flask アプリケーションファクトリー
"""
from flask import Flask
from flask_session import Session
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
from typing import Optional, Type

from config_settings import Config, get_config
from models import db
from utils.security import SecurityUtils, CSRFMiddleware, CSPNonce, CSRFToken
from utils.redis_manager import RedisSessionManager, SessionConfig, RedisConnectionError
from errors import AppError, ValidationError


# グローバル拡張機能
login_manager = LoginManager()
bcrypt = Bcrypt()
socketio = SocketIO()
flask_session = Session()


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Flaskアプリケーションファクトリー
    
    Args:
        config_name: 設定名（'development', 'production', 'testing'）
        
    Returns:
        設定済みのFlaskアプリケーションインスタンス
    """
    app = Flask(__name__)
    
    # 設定の読み込み
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # 拡張機能の初期化
    init_extensions(app)
    
    # セキュリティ設定
    init_security(app)
    
    # エラーハンドラーの登録
    register_error_handlers(app)
    
    # Blueprintの登録
    register_blueprints(app)
    
    # コンテキストプロセッサーの登録
    register_context_processors(app)
    
    # CLIコマンドの登録
    register_cli_commands(app)
    
    # テンプレートフィルターの登録
    register_template_filters(app)
    
    return app


def init_extensions(app: Flask) -> None:
    """拡張機能の初期化"""
    # データベース
    db.init_app(app)
    
    # ログイン管理
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'このページにアクセスするにはログインが必要です。'
    
    # user_loaderコールバックを設定
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # パスワードハッシュ化
    bcrypt.init_app(app)
    
    # セッション管理
    initialize_session_store(app)
    
    # WebSocket
    socketio.init_app(
        app,
        cors_allowed_origins=app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '*'),
        async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading')
    )


def initialize_session_store(app: Flask) -> None:
    """セッションストアの初期化"""
    session_type = app.config.get('SESSION_TYPE', 'filesystem')
    
    if session_type == 'redis':
        try:
            redis_url = app.config.get('REDIS_URL')
            if not redis_url:
                app.logger.warning("REDIS_URL not configured. Falling back to filesystem session.")
                app.config['SESSION_TYPE'] = 'filesystem'
                return
            redis_manager = RedisSessionManager(redis_url)
            
            session_config = SessionConfig(
                ttl=3600,  # 1時間
                key_prefix=app.config.get('SESSION_KEY_PREFIX', 'workplace_roleplay:')
            )
            
            if redis_manager.initialize(session_config):
                app.config['SESSION_REDIS'] = redis_manager.redis_client
                app.logger.info("Redisセッションが正常に初期化されました")
            else:
                app.logger.warning("Redisの初期化に失敗しました。ファイルシステムにフォールバックします")
                app.config['SESSION_TYPE'] = 'filesystem'
                
        except (ImportError, RedisConnectionError) as e:
            app.logger.warning(f"Redisセッションの初期化エラー: {e}")
            app.config['SESSION_TYPE'] = 'filesystem'
    
    flask_session.init_app(app)


def init_security(app: Flask) -> None:
    """セキュリティ設定の初期化"""
    # CSRFミドルウェアの初期化（init_appメソッドが自動的にbefore_requestを登録）
    csrf_middleware = CSRFMiddleware(app)
    
    # セキュリティヘッダー
    @app.after_request
    def set_security_headers(response):
        # X-Content-Type-Options
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options
        response.headers['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response


def register_error_handlers(app: Flask) -> None:
    """エラーハンドラーの登録"""
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return jsonify({"error": str(error)}), error.status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        return jsonify({"error": str(error), "field": error.field}), 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({"error": "リソースが見つかりません"}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        return jsonify({"error": "内部サーバーエラーが発生しました"}), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.error(f"予期しないエラー: {error}")
        return jsonify({"error": "予期しないエラーが発生しました"}), 500


def register_blueprints(app: Flask) -> None:
    """Blueprintの登録"""
    # 認証
    from auth import auth_bp
    app.register_blueprint(auth_bp)
    
    # チャットAPI
    from api.chat import chat_bp
    app.register_blueprint(chat_bp, url_prefix='/api')
    
    # シナリオAPI
    from api.scenarios import scenarios_bp
    app.register_blueprint(scenarios_bp, url_prefix='/api')
    
    # 観戦モードAPI
    from api.watch import watch_bp
    app.register_blueprint(watch_bp, url_prefix='/api/watch')
    
    # フィードバックAPI
    from api.feedback import feedback_bp
    app.register_blueprint(feedback_bp, url_prefix='/api')
    
    # 非同期チャット
    from api.async_chat import async_chat_bp
    app.register_blueprint(async_chat_bp, url_prefix='/api')
    
    # タスク進捗
    from routes.task_progress import progress_bp
    app.register_blueprint(progress_bp, url_prefix='/api/progress')
    
    # アナリティクス
    from api.analytics import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    
    # レコメンデーション
    from api.recommendations import recommendations_bp
    app.register_blueprint(recommendations_bp, url_prefix='/api')
    
    # ペルソナシナリオ
    from api.persona_scenarios import persona_scenarios_bp
    app.register_blueprint(persona_scenarios_bp, url_prefix='/api')
    
    # リアルタイムフィードバック
    from api.realtime_feedback import realtime_feedback_bp
    app.register_blueprint(realtime_feedback_bp, url_prefix='/api')
    
    # メインルート
    from routes.main import main_bp
    app.register_blueprint(main_bp)


def register_context_processors(app: Flask) -> None:
    """コンテキストプロセッサーの登録"""
    @app.context_processor
    def inject_security_utils():
        return {
            'CSPNonce': CSPNonce,
            'CSRFToken': CSRFToken
        }


def register_cli_commands(app: Flask) -> None:
    """CLIコマンドの登録"""
    @app.cli.command("init-db")
    def init_db_command():
        """データベースを初期化します。"""
        from database import init_database, create_initial_data
        init_database()
        create_initial_data()
        print("データベースが初期化されました。")


def register_template_filters(app: Flask) -> None:
    """テンプレートフィルターの登録"""
    @app.template_filter('datetime')
    def format_datetime(value):
        """日時を人間が読める形式にフォーマット"""
        if value is None:
            return ""
        
        if isinstance(value, str):
            try:
                from datetime import datetime
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        
        now = datetime.now()
        diff = now - value
        
        if diff.days > 7:
            return value.strftime('%Y年%m月%d日')
        elif diff.days > 0:
            return f"{diff.days}日前"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}時間前"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}分前"
        else:
            return "たった今"


# 必要なインポートを追加
from flask import request, jsonify, render_template