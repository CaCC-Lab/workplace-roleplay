#!/usr/bin/env python3
"""
タイムアウト対応版アプリケーション
API初期化に失敗してもアプリケーションが起動するように修正
"""
from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context, g
from flask_session import Session
from flask_login import LoginManager, login_user, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Iterator, Any, Tuple
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv
import threading

# 環境変数の読み込み
load_dotenv()

# ========== タイムアウト対応のインポート ==========
print("アプリケーション起動中...")

# 基本的なインポート（高速）
from config import get_cached_config
from scenarios import load_scenarios
from strength_analyzer import analyze_user_strengths, get_top_strengths, generate_encouragement_messages
from api_key_manager import get_google_api_key, handle_api_error, record_api_usage, get_api_key_manager
from errors import *
from utils.security import SecurityUtils, CSPNonce, CSRFToken, CSRFMiddleware
from security_utils import secure_endpoint
from utils.redis_manager import RedisSessionManager, SessionConfig, RedisConnectionError

# 遅延インポート用の変数
_langchain_initialized = False
_langchain_modules = {}
_llm_available = False
_initialization_error = None

def initialize_langchain_with_timeout(timeout=10):
    """LangChainモジュールをタイムアウト付きで初期化"""
    global _langchain_initialized, _langchain_modules, _llm_available, _initialization_error
    
    if _langchain_initialized:
        return _llm_available
    
    def _do_import():
        global _langchain_modules, _llm_available, _initialization_error
        try:
            print("LangChainモジュールを初期化中...")
            
            # 必要なモジュールをインポート
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
            
            _llm_available = True
            print("✅ LangChain初期化成功")
            
        except Exception as e:
            _initialization_error = str(e)
            _llm_available = False
            print(f"⚠️ LangChain初期化失敗: {e}")
    
    # タイムアウト付きで実行
    thread = threading.Thread(target=_do_import)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        print("⚠️ LangChain初期化がタイムアウトしました")
        _llm_available = False
        _initialization_error = "Initialization timeout"
    
    _langchain_initialized = True
    return _llm_available

# ========== Flask アプリケーション設定 ==========
app = Flask(__name__)
app.jinja_env.autoescape = True

# 設定の読み込み
config = get_cached_config()
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['DEBUG'] = config.DEBUG

# セッション設定
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session'
Session(app)

# その他の初期化
login_manager = LoginManager()
login_manager.init_app(app)
bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ダミーのuser_loader
@login_manager.user_loader
def load_user(user_id):
    return None

# CSRFMiddleware
csrf_middleware = CSRFMiddleware(app)

# シナリオデータの読み込み
print("シナリオデータを読み込み中...")
scenarios = load_scenarios()
print(f"✅ {len(scenarios)}個のシナリオを読み込みました")

# ========== ルート定義 ==========
@app.route("/")
def index():
    """ホームページ"""
    return render_template("index.html")

@app.route("/scenarios")
def list_scenarios():
    """シナリオ一覧ページ（高速表示）"""
    # 初期表示時はモデル情報なしで表示
    return render_template(
        "scenarios_list.html",
        scenarios=scenarios,
        models=[]
    )

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

@app.route("/api/models", methods=["GET"])
def get_models_endpoint():
    """利用可能なモデル一覧を返すAPI"""
    # LangChainの初期化を試みる（タイムアウト付き）
    if not _langchain_initialized:
        initialize_langchain_with_timeout(timeout=5)
    
    if _llm_available:
        models = [
            {"id": "gemini/gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "gemini/gemini-1.5-flash", "name": "Gemini 1.5 Flash"}
        ]
        return jsonify({"models": models})
    else:
        return jsonify({
            "models": [],
            "error": "LLM service is not available",
            "details": _initialization_error
        }), 503

@app.route("/api/chat", methods=["POST"])
def chat_api():
    """チャットAPI（ダミーレスポンス）"""
    if not _llm_available:
        return jsonify({
            "error": "LLM service is not available. Please check your API key configuration."
        }), 503
    
    # 実際のチャット処理（省略）
    return jsonify({"message": "チャット機能は現在利用できません"})

@app.route("/api/scenario_chat", methods=["POST"])
def scenario_chat_api():
    """シナリオチャットAPI（ダミーレスポンス）"""
    if not _llm_available:
        return jsonify({
            "error": "LLM service is not available. Please check your API key configuration."
        }), 503
    
    # 実際のシナリオチャット処理（省略）
    return jsonify({"message": "シナリオチャット機能は現在利用できません"})

# エラーハンドラー
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "内部エラーが発生しました"}), 500

# ========== メイン起動 ==========
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("アプリケーションを起動します")
    print("=" * 60)
    
    # API Keyの確認
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("\n⚠️  警告: GOOGLE_API_KEY が設定されていません")
        print("   AI機能は利用できませんが、UIは表示されます。")
        print("\n   API Keyを設定するには：")
        print("   1. .env ファイルを作成")
        print("   2. GOOGLE_API_KEY を設定")
        print("   3. アプリケーションを再起動")
    else:
        print("\n✅ GOOGLE_API_KEY が設定されています")
        # バックグラウンドでLangChain初期化を開始
        threading.Thread(target=lambda: initialize_langchain_with_timeout(30), daemon=True).start()
    
    print("\n" + "=" * 60 + "\n")
    
    # サーバー起動
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=config.DEBUG,
        allow_unsafe_werkzeug=True
    )