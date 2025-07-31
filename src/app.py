"""Flaskアプリケーションファクトリー"""
import logging
import os
from typing import Optional

from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, AnonymousUserMixin
from flask_session import Session
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from .config import get_config
from .utils.security import SecurityHeaders, CSRFMiddleware

# 拡張機能のインスタンス（初期化は後で）
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()


def create_app(config_name: Optional[str] = None) -> Flask:
    """アプリケーションファクトリー
    
    Args:
        config_name: 設定名（development, production, testing）
        
    Returns:
        Flask: 設定済みのFlaskアプリケーション
    """
    # Flaskアプリケーションの作成
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )
    
    # 設定の読み込み
    config_cls = get_config(config_name)
    app.config.from_object(config_cls)
    
    # ロギングの設定
    configure_logging(app)
    
    # 拡張機能の初期化
    initialize_extensions(app)
    
    # セキュリティの設定
    configure_security(app)
    
    # Blueprintの登録
    register_blueprints(app)
    
    # エラーハンドラーの登録
    register_error_handlers(app)
    
    # シェルコンテキストの設定
    configure_shell_context(app)
    
    # Socket.IOハンドラーの登録
    from .socketio_handlers import register_socketio_handlers
    register_socketio_handlers(socketio)
    
    return app


def configure_logging(app: Flask) -> None:
    """ロギングの設定"""
    log_level = getattr(logging, app.config["LOG_LEVEL"].upper())
    
    # ハンドラーの設定
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    
    # フォーマッターの設定
    formatter = logging.Formatter(app.config["LOG_FORMAT"])
    handler.setFormatter(formatter)
    
    # アプリケーションロガーの設定
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    
    # Werkzeugロガーの設定
    logging.getLogger("werkzeug").setLevel(log_level)


def initialize_extensions(app: Flask) -> None:
    """拡張機能の初期化"""
    # データベース
    db.init_app(app)
    
    # セッション
    Session(app)
    
    # ログイン管理
    login_manager.init_app(app)
    login_manager.anonymous_user = AnonymousUserMixin
    
    # テンプレートコンテキストプロセッサーを追加
    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return dict(current_user=current_user)
    
    # WebSocket
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="threading"
    )
    
    # ユーザーローダー（ダミー実装）
    @login_manager.user_loader
    def load_user(user_id):
        # 認証機能を使用しない場合のダミー実装
        return None


def configure_security(app: Flask) -> None:
    """セキュリティの設定"""
    # セキュリティヘッダー
    SecurityHeaders(app)
    
    # CSRF保護
    CSRFMiddleware(app)


def register_blueprints(app: Flask) -> None:
    """Blueprintの登録"""
    # 認証ブループリント
    from .auth import auth
    app.register_blueprint(auth)
    
    # APIブループリント
    from .api import create_api_blueprint
    api_bp = create_api_blueprint()
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # メインルート
    @app.route("/")
    def index():
        return render_template("index.html")
    
    @app.route("/scenarios")
    def list_scenarios():
        # シナリオデータを読み込む
        from scenarios import load_scenarios
        scenarios_data = load_scenarios()
        
        # モデル情報を取得
        from .services.llm_service import LLMService
        llm_service = LLMService()
        models = llm_service.get_available_models()
        
        return render_template("scenarios_list.html", scenarios=scenarios_data, models=models)
    
    @app.route("/chat")
    def chat():
        return render_template("chat.html", models=[])
    
    @app.route("/watch")
    def watch_mode():
        return render_template("watch.html", models=[])
    
    @app.route("/history")
    def history():
        return render_template("history.html")
    
    @app.route("/journal")
    def view_journal():
        return render_template("journal.html")
    
    @app.route("/logout")
    def logout():
        # 認証システムが実装されるまでのダミー
        return redirect(url_for("index"))
    
    @app.route("/strength-analysis")
    def strength_analysis_page():
        return render_template("strength_analysis.html")
    
    @app.route("/breathing-guide")
    def breathing_guide():
        return render_template("breathing_guide.html")
    
    @app.route("/ambient-sounds")
    def ambient_sounds():
        return render_template("ambient_sounds.html")
    
    @app.route("/growth-tracker")
    def growth_tracker():
        return render_template("growth_tracker.html")
    
    @app.route("/analytics")
    def analytics_dashboard():
        return render_template("analytics.html")
    
    @app.route("/scenario/<scenario_id>")
    def show_scenario(scenario_id):
        # シナリオデータを読み込む
        from scenarios import load_scenarios
        scenarios_data = load_scenarios()
        
        # モデル情報を取得
        from .services.llm_service import LLMService
        llm_service = LLMService()
        models = llm_service.get_available_models()
        
        # 指定されたシナリオを取得
        scenario = scenarios_data.get(scenario_id)
        if not scenario:
            return render_template("errors/404.html", message="シナリオが見つかりません"), 404
        
        return render_template("scenario.html", scenario=scenario, scenario_id=scenario_id, models=models)


def register_error_handlers(app: Flask) -> None:
    """エラーハンドラーの登録"""
    @app.errorhandler(404)
    def not_found(error):
        if hasattr(error, "description"):
            message = error.description
        else:
            message = "ページが見つかりません"
        return render_template("errors/404.html", message=message), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {error}")
        return render_template("errors/500.html"), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error(f"Unhandled exception: {error}", exc_info=True)
        if app.config["DEBUG"]:
            raise
        return render_template("errors/500.html"), 500


def configure_shell_context(app: Flask) -> None:
    """シェルコンテキストの設定"""
    @app.shell_context_processor
    def make_shell_context():
        return {
            "db": db,
            "app": app
        }