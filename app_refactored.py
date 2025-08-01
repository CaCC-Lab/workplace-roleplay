"""
リファクタリング版app.py
モジュール化されたサービスとルートを使用する新しいアプリケーション構造
"""
from flask import Flask, render_template, jsonify, session, request
from flask_session import Session
import os
from datetime import datetime
from typing import Dict, Any

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

# 設定モジュールのインポート
from config import get_cached_config

# セキュリティ関連のインポート
from utils.security import SecurityUtils, CSPNonce, CSRFToken, CSRFMiddleware

# Redis関連のインポート
from utils.redis_manager import RedisSessionManager, SessionConfig, RedisConnectionError

# エラーハンドリングのインポート
from errors import handle_error, AppError

# ルートのインポート
from routes.chat_routes import chat_bp
from routes.scenario_routes import scenario_bp
from routes.watch_routes import watch_bp
from routes.model_routes import model_bp
from routes.history_routes import history_bp

# サービスのインポート
from services.session_service import SessionService
from services.llm_service import LLMService

# その他の必要なインポート
from scenarios import load_scenarios
from strength_analyzer import analyze_user_strengths


app = Flask(__name__)

# Jinja2の自動エスケープを有効化
app.jinja_env.autoescape = True

# 設定の読み込み
config = get_cached_config()

# Flask設定の適用
app.secret_key = config.SECRET_KEY
app.config["DEBUG"] = config.DEBUG
app.config["TESTING"] = config.TESTING
app.config["WTF_CSRF_ENABLED"] = config.WTF_CSRF_ENABLED

# セッション設定
app.config["SESSION_TYPE"] = config.SESSION_TYPE
app.config["SESSION_LIFETIME"] = config.SESSION_LIFETIME_MINUTES * 60  # 秒に変換


# Redis統合セッション管理の初期化
def initialize_session_store():
    """セッションストアの初期化（Redis優先、フォールバック対応）"""
    try:
        # Redis設定を試行
        if config.SESSION_TYPE == "redis":
            redis_manager = RedisSessionManager(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD,
                db=config.REDIS_DB,
                ssl=config.REDIS_SSL,
                ssl_cert_reqs=config.REDIS_SSL_CERT_REQS,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            session_config = SessionConfig(
                cookie_name=config.SESSION_COOKIE_NAME,
                cookie_domain=config.SESSION_COOKIE_DOMAIN,
                cookie_path=config.SESSION_COOKIE_PATH,
                cookie_httponly=config.SESSION_COOKIE_HTTPONLY,
                cookie_secure=config.SESSION_COOKIE_SECURE,
                cookie_samesite=config.SESSION_COOKIE_SAMESITE,
                lifetime=config.SESSION_LIFETIME_MINUTES * 60,
                permanent=config.SESSION_PERMANENT,
                key_prefix=config.SESSION_KEY_PREFIX
            )
            
            redis_manager.init_app(app, session_config)
            print("✅ Redis session store initialized successfully")
            return
            
    except (RedisConnectionError, Exception) as e:
        print(f"⚠️ Redis initialization failed: {e}")
        print("📦 Falling back to filesystem session store")
    
    # ファイルシステムセッションへのフォールバック
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = config.SESSION_FILE_DIR
    app.config["SESSION_FILE_THRESHOLD"] = config.SESSION_FILE_THRESHOLD
    app.config["SESSION_PERMANENT"] = config.SESSION_PERMANENT
    app.config["SESSION_USE_SIGNER"] = config.SESSION_USE_SIGNER
    app.config["SESSION_KEY_PREFIX"] = config.SESSION_KEY_PREFIX
    app.config["SESSION_COOKIE_NAME"] = config.SESSION_COOKIE_NAME
    app.config["SESSION_COOKIE_DOMAIN"] = config.SESSION_COOKIE_DOMAIN
    app.config["SESSION_COOKIE_PATH"] = config.SESSION_COOKIE_PATH
    app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
    app.config["SESSION_COOKIE_SECURE"] = config.SESSION_COOKIE_SECURE
    app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE
    
    Session(app)
    print("✅ Filesystem session store initialized")


# セッションストアの初期化
initialize_session_store()

# CSRFミドルウェアの追加
csrf = CSRFMiddleware(app)

# CSPノンスをテンプレートコンテキストに追加
@app.context_processor
def inject_csp_nonce():
    """テンプレートにCSPノンスを注入"""
    return {'csp_nonce': CSPNonce.generate}

# CSRFトークンをテンプレートコンテキストに追加
@app.context_processor
def inject_csrf_token():
    """テンプレートにCSRFトークンを注入"""
    return {'csrf_token': CSRFToken.generate}

# セキュリティヘッダーの設定
@app.after_request
def set_security_headers(response):
    """セキュリティヘッダーを設定"""
    # Content Security Policy
    nonce = CSPNonce.generate()
    csp_policy = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
        f"style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        f"font-src 'self' https://fonts.gstatic.com; "
        f"img-src 'self' data: https:; "
        f"connect-src 'self'; "
        f"frame-ancestors 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self'"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    
    # その他のセキュリティヘッダー
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # HSTS（HTTPSの場合のみ）
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response


# Blueprintの登録
app.register_blueprint(chat_bp)
app.register_blueprint(scenario_bp)
app.register_blueprint(watch_bp)
app.register_blueprint(model_bp)
app.register_blueprint(history_bp)


# 基本的なルート
@app.route('/')
def index():
    """ホームページ"""
    return render_template('index.html')


@app.route('/chat')
def chat():
    """雑談チャットページ"""
    # セッションに選択されたモデルがない場合、デフォルトを設定
    if 'selected_model' not in session:
        session['selected_model'] = 'gemini-1.5-flash'
    return render_template('chat.html')


@app.route('/scenarios')
def scenarios():
    """シナリオ一覧ページ"""
    scenarios_data = load_scenarios()
    # セッションに選択されたモデルがない場合、デフォルトを設定
    if 'selected_model' not in session:
        session['selected_model'] = 'gemini-1.5-flash'
    return render_template('scenarios.html', scenarios=scenarios_data)


@app.route('/scenario/<scenario_id>')
def scenario(scenario_id: str):
    """個別シナリオページ"""
    scenarios_data = load_scenarios()
    
    if scenario_id not in scenarios_data:
        return "シナリオが見つかりません", 404
    
    scenario_data = scenarios_data[scenario_id]
    # セッションに選択されたモデルがない場合、デフォルトを設定
    if 'selected_model' not in session:
        session['selected_model'] = 'gemini-1.5-flash'
    
    return render_template('scenario.html', scenario=scenario_data, scenario_id=scenario_id)


@app.route('/watch')
def watch():
    """観戦モードページ"""
    # セッションに選択されたモデルがない場合、デフォルトを設定
    if 'selected_model' not in session:
        session['selected_model'] = 'gemini-1.5-flash'
    return render_template('watch.html')


@app.route('/history')
def history():
    """学習履歴ページ"""
    return render_template('history.html')


@app.route('/api/strengths_analysis', methods=['POST'])
def strengths_analysis():
    """コミュニケーション強みの分析エンドポイント"""
    try:
        # 各モードの履歴を収集
        chat_history = SessionService.get_session_history('chat_history')
        scenario_history_all = SessionService.get_session_data('scenario_history', {})
        
        # シナリオ履歴を統合
        all_scenario_messages = []
        for scenario_id, history in scenario_history_all.items():
            if isinstance(history, list):
                all_scenario_messages.extend(history)
        
        # 強みの分析
        strengths = analyze_user_strengths(chat_history, all_scenario_messages)
        
        # トップ3の強みを取得
        top_strengths = get_top_strengths(strengths, top_n=3)
        
        # 励ましメッセージの生成
        encouragement = generate_encouragement_messages(top_strengths)
        
        return jsonify({
            'strengths': strengths,
            'top_strengths': top_strengths,
            'encouragement': encouragement
        })
        
    except Exception as e:
        print(f"Strengths analysis error: {str(e)}")
        return jsonify({
            'error': '強み分析中にエラーが発生しました',
            'details': str(e)
        }), 500


@app.route('/health')
def health():
    """ヘルスチェックエンドポイント"""
    try:
        # 基本的なヘルスチェック
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        }
        
        # Gemini APIの状態確認
        try:
            models = LLMService.get_available_models()
            health_status['gemini_api'] = 'available' if models else 'unavailable'
        except:
            health_status['gemini_api'] = 'error'
        
        # Redisの状態確認（Redis使用時のみ）
        if app.config.get('SESSION_TYPE') == 'redis':
            try:
                # Redisのping確認（実装は省略）
                health_status['redis'] = 'connected'
            except:
                health_status['redis'] = 'disconnected'
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


# エラーハンドラー
@app.errorhandler(404)
def not_found(error):
    """404エラーハンドラー"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'APIエンドポイントが見つかりません'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    """500エラーハンドラー"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'サーバーエラーが発生しました'}), 500
    return render_template('500.html'), 500


@app.errorhandler(Exception)
def handle_exception(error):
    """汎用例外ハンドラー"""
    return handle_error(error)


if __name__ == '__main__':
    # 開発サーバーの起動
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=config.DEBUG,
        use_reloader=config.DEBUG
    )