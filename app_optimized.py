#!/usr/bin/env python3
"""
最適化されたアプリケーション起動ファイル
重いモジュールの遅延読み込みとキャッシングを実装
"""
# 🚨 CodeRabbit指摘対応: 未使用importを削除
from flask import Flask, render_template, request, jsonify, session, g
from flask_session import Session
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
import requests
import os
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta
from pydantic import SecretStr  # 追加
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time

# ========== 遅延インポートのためのグローバル変数 ==========
_genai = None
_langchain_modules = None
_GENAI_AVAILABLE = None
_LANGCHAIN_AVAILABLE = None

def get_genai():
    """Google Generative AIを遅延インポート"""
    global _genai, _GENAI_AVAILABLE
    if _genai is None:
        try:
            print("Google Generative AIを初期化中...")
            import google.generativeai as genai
            _genai = genai
            _GENAI_AVAILABLE = True
        except ImportError as e:
            print(f"Warning: Google Generative AI import failed: {e}")
            _GENAI_AVAILABLE = False
    return _genai

def get_langchain_modules():
    """LangChainモジュールを遅延インポート"""
    global _langchain_modules, _LANGCHAIN_AVAILABLE
    if _langchain_modules is None:
        try:
            print("LangChainを初期化中...")
            from langchain_core.callbacks.manager import CallbackManager
            from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
            from langchain.memory import ConversationBufferMemory
            from langchain.chains import ConversationChain
            from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
            from langchain_core.output_parsers import StrOutputParser
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            _langchain_modules = {
                'CallbackManager': CallbackManager,
                'StreamingStdOutCallbackHandler': StreamingStdOutCallbackHandler,
                'ConversationBufferMemory': ConversationBufferMemory,
                'ConversationChain': ConversationChain,
                'BaseMessage': BaseMessage,
                'SystemMessage': SystemMessage,
                'HumanMessage': HumanMessage,
                'AIMessage': AIMessage,
                'ChatPromptTemplate': ChatPromptTemplate,
                'MessagesPlaceholder': MessagesPlaceholder,
                'StrOutputParser': StrOutputParser,
                'ChatGoogleGenerativeAI': ChatGoogleGenerativeAI
            }
            _LANGCHAIN_AVAILABLE = True
        except ImportError as e:
            print(f"Warning: LangChain import failed: {e}")
            print("Running in limited mode without LangChain features")
            _LANGCHAIN_AVAILABLE = False
            # ダミークラスを定義
            class BaseMessage:
                pass
            class SystemMessage(BaseMessage):
                pass
            class HumanMessage(BaseMessage):
                pass
            class AIMessage(BaseMessage):
                pass
            _langchain_modules = {
                'BaseMessage': BaseMessage,
                'SystemMessage': SystemMessage,
                'HumanMessage': HumanMessage,
                'AIMessage': AIMessage
            }
    return _langchain_modules

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

# 設定モジュールのインポート
from config import get_cached_config

# 既存のimport文の下に追加
from scenarios import load_scenarios
from strength_analyzer import (
    analyze_user_strengths,
    get_top_strengths,
    generate_encouragement_messages
)
from api_key_manager import (
    get_google_api_key,
    handle_api_error,
    record_api_usage,
    get_api_key_manager
)

# エラーハンドリングのインポート
from errors import (
    AppError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ExternalAPIError,
    RateLimitError,
    TimeoutError,
    handle_error,
    handle_llm_specific_error,
    with_error_handling
)

# セキュリティ関連のインポート
from utils.security import SecurityUtils, CSPNonce, CSRFToken, CSRFMiddleware
from security_utils import secure_endpoint

# Redis関連のインポート
from utils.redis_manager import RedisSessionManager, SessionConfig, RedisConnectionError

# データベース関連のインポート（遅延初期化）
_database_initialized = False
_db = None
_User = None

def get_database_modules():
    """データベースモジュールを遅延インポート"""
    global _database_initialized, _db, _User
    if not _database_initialized:
        from database import init_database, create_initial_data
        from models import User, db
        _db = db
        _User = User
        _database_initialized = True
    return _db, _User

# サービスレイヤーのインポート（遅延初期化）
_service_layer = None

def get_service_layer():
    """サービスレイヤーを遅延インポート"""
    global _service_layer
    if _service_layer is None:
        from service_layer import (
            create_scenario_initial_message,
            create_scenario_prompt,
            create_watch_prompt,
            generate_scenario_response,
            create_chat_prompt,
            create_watch_scene_description,
            extract_content,
            fallback_response,
            ScenarioService,
            ConversationService,
            AnalyticsService,
            UserService,
            JournalService,
            FeedbackWidgetService,
            WatchService
        )
        _service_layer = {
            'create_scenario_initial_message': create_scenario_initial_message,
            'create_scenario_prompt': create_scenario_prompt,
            'create_watch_prompt': create_watch_prompt,
            'generate_scenario_response': generate_scenario_response,
            'create_chat_prompt': create_chat_prompt,
            'create_watch_scene_description': create_watch_scene_description,
            'extract_content': extract_content,
            'fallback_response': fallback_response,
            'ScenarioService': ScenarioService,
            'ConversationService': ConversationService,
            'AnalyticsService': AnalyticsService,
            'UserService': UserService,
            'JournalService': JournalService,
            'FeedbackWidgetService': FeedbackWidgetService,
            'WatchService': WatchService
        }
    return _service_layer

# ========== Flask設定 ==========
app = Flask(__name__)
# Jinja2の自動エスケープを有効化（デフォルトで有効だが明示的に設定）
app.jinja_env.autoescape = True

# 設定の読み込み
config = get_cached_config()
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['DEBUG'] = config.DEBUG
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=config.SESSION_LIFETIME_MINUTES)

# ========== メモリキャッシュ設定 ==========
# シナリオデータのキャッシュ（起動時に1回だけ読み込み）
print("シナリオデータを読み込み中...")
scenarios = load_scenarios()
print(f"✅ {len(scenarios)}個のシナリオを読み込みました")

# ========== セッション設定 ==========
# セッションストアの設定
redis_manager = None
redis_available = False

if config.SESSION_TYPE == 'redis':
    try:
        redis_manager = RedisSessionManager(fallback_enabled=True)
        session_config = SessionConfig(
            ttl=3600,  # 1時間
            key_prefix='workplace_roleplay:'
        )
        
        if redis_manager.initialize(session_config):
            app.config['SESSION_TYPE'] = 'redis'
            app.config['SESSION_REDIS'] = redis_manager.redis_client
            app.config['SESSION_KEY_PREFIX'] = session_config.key_prefix
            redis_available = True
            print("✅ Redisセッションストアを使用")
        else:
            print("⚠️ Redis接続失敗、ファイルシステムにフォールバック")
            app.config['SESSION_TYPE'] = 'filesystem'
    except Exception as e:
        print(f"Redis初期化エラー: {e}")
        app.config['SESSION_TYPE'] = 'filesystem'
else:
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = config.SESSION_FILE_DIR or './flask_session'
    print("📁 Filesystemセッションにフォールバックします")

# セッション初期化
Session(app)

# ========== 認証設定（使用しない場合でも初期化） ==========
login_manager = LoginManager()
login_manager.init_app(app)
bcrypt = Bcrypt(app)

# Flask-Loginのuser_loader設定（ダミー）
@login_manager.user_loader
def load_user(user_id):
    # 認証機能を使用しない場合でも、Flask-Loginはuser_loaderを要求する
    # ここではNoneを返すことで、常に匿名ユーザーとして扱う
    return None

# Flask-SocketIO初期化
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# CSRFMiddlewareの適用
csrf_middleware = CSRFMiddleware(app)

# ========== ルート定義 ==========
@app.route("/")
def index():
    """ホームページ"""
    return render_template("index.html")

@app.route("/scenarios")
def list_scenarios():
    """シナリオ一覧ページ"""
    # モデル情報は必要になった時点で取得
    return render_template(
        "scenarios_list.html",
        scenarios=scenarios,
        models=[]  # 初期表示では空配列
    )

@app.route("/api/models", methods=["GET"])
def get_models_endpoint():
    """利用可能なモデル一覧を返すAPI（遅延実行）"""
    try:
        # 実際にAPIが呼ばれた時点でLangChainを初期化
        langchain_modules = get_langchain_modules()
        if not langchain_modules:
            return jsonify({"models": [], "error": "LangChain not available"}), 503
        
        # モデル情報を返す
        models = [
            {"id": "gemini/gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "gemini/gemini-1.5-flash", "name": "Gemini 1.5 Flash"}
        ]
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"models": [], "error": str(e)}), 500

# その他の基本的なルートのみ定義
@app.route("/chat")
def chat():
    """雑談練習ページ"""
    return render_template("chat.html", models=[])

@app.route("/watch")
def watch():
    """会話観戦ページ"""
    return render_template("watch.html", models=[])

@app.route("/history")
def history():
    """学習履歴ページ"""
    return render_template("history.html")

# ========== エラーハンドラー ==========
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "内部エラーが発生しました"}), 500

# ========== メイン起動 ==========
if __name__ == "__main__":
    # データベース初期化をスキップ
    print("📌 軽量モードで起動（データベース・重いモジュールの遅延読み込み）")
    
    # WebSocketサーバーを起動
    # ポート番号を環境変数から取得（デフォルト5000）
    port = int(os.environ.get('PORT', 5000))
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=config.DEBUG,
        allow_unsafe_werkzeug=True
    )