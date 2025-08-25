from flask import Flask, render_template, request, jsonify, session, stream_with_context, send_from_directory, url_for
from flask_session import Session
import requests
import re
import os
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from pydantic import SecretStr  # 追加
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time

# Google API固有の例外をインポート
try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    # フォールバック定義（本来のGoogle API例外が利用できない場合）
    class ResourceExhausted(Exception):
        pass

# LangChain関連
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

# 設定モジュールのインポート
from config import get_cached_config
from config.feature_flags import (
    FeatureFlags,
    FeatureDisabledException,
    is_model_selection_enabled,
    is_tts_enabled,
    is_learning_history_enabled,
    is_strength_analysis_enabled,
    get_feature_flags,
    require_feature
)

# 既存のimport文の下に追加
from scenarios import load_scenarios
from scenarios.category_manager import (
    get_categorized_scenarios,
    get_scenario_category_summary,
    is_harassment_scenario
)
from strength_analyzer import (
    analyze_user_strengths,
    get_top_strengths,
    generate_encouragement_messages
)
# COMPLIANCE FIX: 規約準拠APIマネージャーに移行
from compliant_api_manager import (
    get_compliant_google_api_key,
    handle_compliant_api_error,
    record_compliant_api_usage,
    get_compliant_api_manager
)
# 旧版（規約違反リスク）をコメントアウト
# from api_key_manager import (
#     get_google_api_key,
#     handle_api_error,
#     record_api_usage,
#     get_api_key_manager
# )

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
    with_error_handling,
    secure_error_handler
)

# セキュリティ関連のインポート
# セキュリティ関連のインポート（存在するものだけ）
try:
    from utils.security import SecurityUtils, CSRFProtection, RateLimiter, rate_limiter
except ImportError as e:
    print(f"Warning: Some security modules not found: {e}")
    # フォールバック用のダミークラス
    class SecurityUtils:
        @staticmethod
        def escape_html(content):
            # 基本的なHTMLエスケープのフォールバック
            import html
            return html.escape(str(content))

        @staticmethod
        def sanitize_input(text):
            # サニタイズのフォールバックとして、何もしない
            return text

        @staticmethod
        def validate_scenario_id(scenario_id):
            # バリデーションのフォールバックとして、常にTrueを返す
            print(f"Warning: Using fallback for validate_scenario_id. Validation skipped for '{scenario_id}'.")
            return True

        @staticmethod
        def validate_model_name(model_name):
            # バリデーションのフォールバックとして、常にTrueを返す
            print(f"Warning: Using fallback for validate_model_name. Validation skipped for '{model_name}'.")
            return True
    CSRFProtection = None
    RateLimiter = None
    rate_limiter = None

# Redis関連のインポート
from utils.redis_manager import RedisSessionManager, SessionConfig, RedisConnectionError

"""
要件:
1. Google Gemini APIを使用したAIチャット
2. ユーザごとに会話メモリを保持
3. Geminiテキスト読み上げ機能の統合
4. Flaskを使ったプロトタイプ（Jinja2テンプレート）
"""

app = Flask(__name__)

# Jinja2の自動エスケープを有効化（デフォルトで有効だが明示的に設定）
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
                db=config.REDIS_DB,
                fallback_enabled=True
            )
            
            # Redis接続確認
            health = redis_manager.health_check()
            
            if health['connected']:
                # Redis設定をFlaskに適用
                redis_config = SessionConfig.get_redis_config(os.getenv('FLASK_ENV'))
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
        print("📁 Filesystemセッションにフォールバックします")
        app.config["SESSION_TYPE"] = "filesystem"
        if config.SESSION_FILE_DIR:
            if not os.path.exists(config.SESSION_FILE_DIR):
                try:
                    os.makedirs(config.SESSION_FILE_DIR, exist_ok=True)
                except (OSError, PermissionError) as e:
                    print(f"⚠️ セッションディレクトリ作成失敗: {config.SESSION_FILE_DIR} - {str(e)}")
                    config.SESSION_FILE_DIR = "./flask_session"
            app.config["SESSION_FILE_DIR"] = config.SESSION_FILE_DIR
        else:
            app.config["SESSION_FILE_DIR"] = "./flask_session"
            
        return None
        
    except ImportError as e:
        print(f"❌ Redis依存関係エラー: {str(e)}")
        print("   対処法: pip install redis を実行してください")
        app.config["SESSION_TYPE"] = "filesystem"
        app.config["SESSION_FILE_DIR"] = "./flask_session"
        return None
    except Exception as e:
        print(f"❌ セッション初期化エラー: {str(e)}")
        app.config["SESSION_TYPE"] = "filesystem"
        app.config["SESSION_FILE_DIR"] = "./flask_session"
        return None

# セッションマネージャーの初期化
redis_session_manager = initialize_session_store()

Session(app)

# CSRF対策ミドルウェアの初期化
# CSRFミドルウェアの初期化（利用可能な場合）
if CSRFProtection:
    # CSRFProtectionを使用
    pass  # Flask-WTFまたはカスタム実装を使用
else:
    print("Warning: CSRF protection not available")

# ========== エラーハンドラーの登録 ==========
@app.errorhandler(AppError)
def handle_app_error(error: AppError):
    """アプリケーション固有のエラーハンドラー"""
    return handle_error(error)

@app.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError):
    """バリデーションエラーのハンドラー"""
    return handle_error(error)

@app.errorhandler(404)
def handle_not_found(error):
    """404エラーのハンドラー"""
    # favicon.icoの場合は204 No Contentを返す
    if request.path == '/favicon.ico':
        return '', 204
    
    if request.path.startswith('/api/'):
        # APIエンドポイントの場合はJSON形式で返す
        return handle_error(NotFoundError("APIエンドポイント", request.path))
    
    # 通常のページの場合は404ページを表示（フォールバック付き）
    try:
        return render_template('404.html'), 404
    except:
        # 404.htmlが存在しない場合のフォールバック
        return jsonify({'error': 'Page not found', 'path': request.path}), 404

@app.errorhandler(500)
def handle_internal_error(error):
    """500エラーのハンドラー"""
    return handle_error(Exception("内部エラーが発生しました"))

@app.errorhandler(Exception)
def handle_unexpected_error(error: Exception):
    """予期しないエラーのハンドラー"""
    return handle_error(error)

# カスタムJinjaフィルターの追加
@app.template_filter('datetime')
def format_datetime(value):
    """ISO形式の日時文字列をより読みやすい形式に変換"""
    if not value:
        return "なし"
    try:
        # ISO形式の文字列をdatetimeオブジェクトに変換
        dt = datetime.fromisoformat(value)
        # 日本語形式でフォーマット
        return dt.strftime('%Y年%m月%d日 %H:%M')
    except (ValueError, TypeError):
        return str(value)

# ========== 設定値・初期化 ==========
# Gemini APIキー (設定から取得)
GOOGLE_API_KEY = config.GOOGLE_API_KEY
# テスト環境ではAPIキーがなくても起動できるようにする
if not GOOGLE_API_KEY and not config.TESTING:
    raise ValueError("GOOGLE_API_KEY is not configured")

# LLMの温度やその他パラメータ
DEFAULT_TEMPERATURE = config.DEFAULT_TEMPERATURE

# デフォルトモデルの設定
DEFAULT_MODEL = config.DEFAULT_MODEL

# Gemini APIの初期化
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Gemini API initialization error: {e}")

def get_available_gemini_models():
    """
    利用可能なGeminiモデルのリストを返す
    廃止されたモデルを除外し、代替モデルを提供する
    """
    try:
        # Gemini APIの設定を確認
        if not GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY is not set")
            return []
            
        # 利用可能なモデルを取得
        models = genai.list_models()
        
        # 廃止されたモデルと代替モデルのマッピング
        deprecated_models = {
            'gemini-1.0-pro-vision': 'gemini-1.5-flash',
            'gemini-1.0-pro-vision-latest': 'gemini-1.5-flash-latest'
        }
        
        # Geminiモデルをフィルタリング
        gemini_models = []
        for model in models:
            if "gemini" in model.name.lower():
                # モデル名を取得
                model_short_name = model.name.split('/')[-1]
                
                # 廃止されたモデルの場合は代替を使用
                if model_short_name in deprecated_models:
                    alternative = deprecated_models[model_short_name]
                    print(f"Replacing deprecated model {model_short_name} with {alternative}")
                    model_name = f"gemini/{alternative}"
                    # 代替モデルを追加（重複を避けるため）
                    if model_name not in gemini_models:
                        gemini_models.append(model_name)
                else:
                    # モデル名を整形（gemini/プレフィックスを追加）
                    model_name = f"gemini/{model_short_name}"
                    gemini_models.append(model_name)
        
        print(f"Available Gemini models: {gemini_models}")
        return gemini_models
        
    except Exception as e:
        print(f"Error fetching Gemini models: {str(e)}")
        # エラー時は最新のモデルリストを返す（廃止されたモデルを除外）
        return [
            "gemini/gemini-1.5-pro",
            "gemini/gemini-1.5-flash"
        ]

def create_gemini_llm(model_name: str = "gemini-1.5-flash"):
    """
    LangChainのGemini Chat modelインスタンス生成
    廃止されたモデルを自動的に代替モデルに置き換える
    """
    try:
        # 廃止されたモデルと代替モデルのマッピング
        deprecated_models = {
            'gemini-pro-vision': 'gemini-1.5-flash',
            'gemini-1.0-pro-vision': 'gemini-1.5-flash',
            'gemini-1.0-pro-vision-latest': 'gemini-1.5-flash-latest'
        }
        
        # モデル名からgemini/プレフィックスを削除
        if model_name.startswith("gemini/"):
            model_name = model_name.replace("gemini/", "")
        
        # 廃止されたモデルの場合は代替モデルを使用
        original_model = model_name
        if model_name in deprecated_models:
            model_name = deprecated_models[model_name]
            print(f"Switching from deprecated model {original_model} to {model_name}")
        
        print(f"Initializing Gemini with model: {model_name}")
        
        if not GOOGLE_API_KEY:
            raise AuthenticationError("GOOGLE_API_KEY環境変数が設定されていません")
            
        # APIキーの形式を検証
        if not GOOGLE_API_KEY.startswith("AI"):
            raise ValidationError("Google APIキーの形式が無効です。'AI'で始まる必要があります", field="api_key")
        
        # APIキーをSecretStr型に変換
        api_key = SecretStr(GOOGLE_API_KEY)
        
        # Gemini APIの設定を初期化
        genai.configure(api_key=GOOGLE_API_KEY)
        
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=DEFAULT_TEMPERATURE,
            api_key=api_key,
            convert_system_message_to_human=True,  # システムメッセージの互換性対応
        )
        
        # テスト呼び出しで接続確認
        test_response = llm.invoke("test")
        if not test_response:
            raise ExternalAPIError("Gemini", "APIからの応答がありません")
            
        print("Gemini model initialized successfully")
        return llm
        
    except (AuthenticationError, ValidationError, ExternalAPIError):
        # 既にアプリケーションエラーの場合はそのまま再スロー
        raise
    except Exception as e:
        # 特定のエラーメッセージをチェック
        error_msg = str(e)
        if "404" in error_msg and "deprecated" in error_msg.lower():
            # 廃止されたモデルによるエラーの場合、代替モデルで再試行
            try:
                print(f"Error with model {model_name}: {error_msg}")
                fallback_model = "gemini-1.5-flash"
                print(f"Falling back to {fallback_model} due to deprecated model error")
                
                # 再帰的に代替モデルで試行
                return create_gemini_llm(fallback_model)
            except Exception as fallback_error:
                # フォールバックも失敗した場合はLLM固有のエラーに変換
                raise handle_llm_specific_error(fallback_error, "Gemini")
        
        # その他のエラーはLLM固有のエラーに変換
        raise handle_llm_specific_error(e, "Gemini")

# ========== LLM生成ユーティリティ ==========

# ========== シナリオ（職場のあなた再現シートを想定したデータ） ==========
# 実際にはデータベースや外部ファイルなどで管理するのがおすすめ
try:
    scenarios = load_scenarios()
    print(f"✅ シナリオロード成功: {len(scenarios)}個")
except Exception as e:
    print(f"❌ シナリオロードエラー: {e}")
    scenarios = {}  # 空辞書でフォールバック

def get_categorized_scenarios():
    """シナリオをカテゴリ別に分類する"""
    regular_scenarios = {}
    harassment_scenarios = {}
    
    for scenario_id, scenario_data in scenarios.items():
        # YAMLファイルのcategoryフィールドを最優先で確認
        if scenario_data and isinstance(scenario_data, dict):
            category = scenario_data.get('category', '').lower()
            if category in ['harassment', 'harassment_prevention']:
                # categoryフィールドで明示的にハラスメント関連と指定されている
                harassment_scenarios[scenario_id] = scenario_data
                continue
        
        # 既存のハラスメント関連シナリオの判定（後方互換性のため）
        if (scenario_id.startswith('scenario') and 
            scenario_id[-2:].isdigit() and 
            int(scenario_id[-2:]) >= 34):
            # scenario34以降はハラスメント関連
            harassment_scenarios[scenario_id] = scenario_data
        elif 'harassment' in scenario_id.lower():
            # IDにharassmentを含むものもハラスメント関連
            harassment_scenarios[scenario_id] = scenario_data
        elif scenario_data and isinstance(scenario_data, dict):
            # タグでの判定
            tags = scenario_data.get('tags', [])
            if any('ハラスメント' in str(tag) or 'グレーゾーン' in str(tag) or 'パワハラ' in str(tag) for tag in tags):
                harassment_scenarios[scenario_id] = scenario_data
            else:
                regular_scenarios[scenario_id] = scenario_data
        else:
            # その他は通常シナリオ
            regular_scenarios[scenario_id] = scenario_data
    
    return regular_scenarios, harassment_scenarios

def get_scenario_category_summary():
    """シナリオのカテゴリ別サマリーを返す"""
    regular, harassment = get_categorized_scenarios()
    
    return {
        "total": len(scenarios),
        "regular": {
            "count": len(regular),
            "scenarios": list(regular.keys())
        },
        "harassment": {
            "count": len(harassment),
            "scenarios": list(harassment.keys())
        }
    }

# ========== Flaskルート ==========
@app.route("/health")
@secure_error_handler
def health_check():
    """ヘルスチェックエンドポイント"""
    # 基本的なヘルスチェック
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "checks": {
            "database": "N/A",  # DBを使用していない
            "llm": "ready" if llm else "not configured"
        }
    }
    return jsonify(health_status), 200

@app.route("/")
def index():
    """トップページ"""
    # 共通関数を使用してモデル情報を取得
    model_info = get_all_available_models()
    available_models = model_info["models"]
    
    # モデル選択機能の有効/無効を制御するフラグ
    enable_model_selection = os.getenv('ENABLE_MODEL_SELECTION', 'true').lower() == 'true'
    
    return render_template("index.html", 
                         models=available_models,
                         enable_model_selection=enable_model_selection)

@app.route("/chat")
def chat():
    """
    自由会話ページ
    """
    # feature_flagsを取得
    feature_flags = get_feature_flags()
    # モデル一覧の取得を削除
    return render_template("chat.html", 
                         default_model=DEFAULT_MODEL,
                         feature_flags=feature_flags.to_dict())

# 既存のhandle_llm_error関数を削除（errors.pyの機能に置き換え）

def create_model_and_get_response(model_name: str, messages_or_prompt, extract=True):
    """
    指定されたモデルでLLMを初期化し、応答を取得する共通関数
    
    Args:
        model_name: 使用するモデル名
        messages_or_prompt: メッセージリストまたはプロンプト文字列
        extract: 応答からコンテンツを抽出するかどうか
        
    Returns:
        レスポンス（抽出するかそのまま）
    """
    try:
        llm = initialize_llm(model_name)
        response = llm.invoke(messages_or_prompt)
        
        if extract:
            return extract_content(response)
        return response
    except Exception as e:
        # エラーはそのまま上位に伝播させる
        raise


# セッション管理ヘルパー関数

def initialize_session_history(session_key, sub_key=None):
    """
    セッション履歴を初期化するヘルパー関数
    
    Args:
        session_key: セッションのキー
        sub_key: サブキー（オプション）
    """
    if session_key not in session:
        session[session_key] = {} if sub_key else []
    
    if sub_key and sub_key not in session[session_key]:
        session[session_key][sub_key] = []
    
    session.modified = True

def add_to_session_history(session_key, entry, sub_key=None):
    """
    セッション履歴にエントリを追加するヘルパー関数
    
    Args:
        session_key: セッションのキー
        entry: 追加するエントリ（辞書）
        sub_key: サブキー（オプション）
    """
    # セッションが初期化されていることを確認
    initialize_session_history(session_key, sub_key)
    
    # エントリがなければタイムスタンプを追加
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now().isoformat()
    
    # 履歴に追加
    if sub_key:
        session[session_key][sub_key].append(entry)
    else:
        session[session_key].append(entry)
    
    session.modified = True

def clear_session_history(session_key, sub_key=None):
    """
    セッション履歴をクリアするヘルパー関数
    
    Args:
        session_key: クリアするセッションのキー
        sub_key: クリアするサブキー（オプション）
    """
    if session_key in session:
        if sub_key:
            if sub_key in session[session_key]:
                session[session_key][sub_key] = []
        else:
            session[session_key] = {} if isinstance(session[session_key], dict) else []
    
    session.modified = True

# セッション開始時間を保存するヘルパー関数を追加
def set_session_start_time(session_key, sub_key=None):
    """
    セッションの開始時間を記録するヘルパー関数
    
    Args:
        session_key: セッションのキー
        sub_key: サブキー（オプション）
    """
    # セッション設定キーを構築
    settings_key = f"{session_key}_settings"
    
    # セッション設定が存在しない場合は初期化
    if settings_key not in session:
        session[settings_key] = {} if sub_key else {"start_time": datetime.now().isoformat()}
    
    # サブキーがある場合
    if sub_key:
        if sub_key not in session[settings_key]:
            session[settings_key][sub_key] = {}
        session[settings_key][sub_key]["start_time"] = datetime.now().isoformat()
    else:
        session[settings_key]["start_time"] = datetime.now().isoformat()
    
    session.modified = True

# チャットエンドポイントを更新して共通関数を使用

def process_chat_message_legacy(message: str, model_name: str = None) -> str:
    """
    既存のチャット処理ロジック（A/Bテスト用）
    """
    if not model_name:
        model_name = DEFAULT_MODEL
    
    # chat_settingsの取得
    chat_settings = session.get("chat_settings", {})
    system_prompt = chat_settings.get("system_prompt", "")
    
    if not system_prompt:
        raise ValidationError("チャットセッションが初期化されていません")
    
    # 会話履歴の取得と更新
    initialize_session_history("chat_history")
    
    # メッセージリストの作成
    messages = []
    messages.append(SystemMessage(content=system_prompt))
    
    # 履歴からメッセージを構築
    add_messages_from_history(messages, session["chat_history"])
    
    # 新しいメッセージを追加
    messages.append(HumanMessage(content=message))
    
    # 応答を生成
    ai_message = create_model_and_get_response(model_name, messages)
    
    # 会話履歴の更新
    add_to_session_history("chat_history", {
        "human": message,
        "ai": ai_message
    })
    
    return ai_message

@app.route("/api/chat", methods=["POST"])
# @CSRFToken.require_csrf  # TODO: CSRF保護を後で有効化
def handle_chat() -> Any:
    """
    チャットメッセージの処理
    """
    data = request.get_json()
    if data is None:
        raise ValidationError("無効なJSONデータです")

    # 入力値のサニタイズ
    message = SecurityUtils.sanitize_input(data.get("message", ""))
    if not message:
        raise ValidationError("メッセージが空です", field="message")
        
    model_name = data.get("model", DEFAULT_MODEL)
    
    # モデル名の検証
    if not SecurityUtils.validate_model_name(model_name):
        raise ValidationError("無効なモデル名です", field="model")

    # chat_settingsの取得
    chat_settings = session.get("chat_settings", {})
    system_prompt = chat_settings.get("system_prompt", "")

    if not system_prompt:
        raise ValidationError("チャットセッションが初期化されていません")

    # 会話履歴の取得と更新（共通関数使用）
    initialize_session_history("chat_history")

    # メッセージリストの作成（型を明示的に指定）
    messages: List[BaseMessage] = []
    messages.append(SystemMessage(content=system_prompt))

    # 共通関数を使用して履歴からメッセージを構築
    add_messages_from_history(messages, session["chat_history"])

    # 新しいメッセージを追加
    messages.append(HumanMessage(content=message))

    # 既存のロジックを使用
    try:
        ai_message = process_chat_message_legacy(message, model_name)
        # レスポンスをエスケープして返す
        return jsonify({"response": SecurityUtils.escape_html(ai_message)})
    except Exception as e:
        raise e

@app.route("/api/clear_history", methods=["POST"])
def clear_history():
    """
    会話履歴をクリアするAPI
    """
    try:
        if request.json is None:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        mode = request.json.get("mode", "scenario")  # デフォルトはシナリオモード
        
        if mode == "chat":
            # 雑談モードの履歴クリア（共通関数使用）
            clear_session_history("chat_history")
            if "chat_settings" in session:
                session.pop("chat_settings", None)
                session.modified = True
        elif mode == "watch":
            # 観戦モードの履歴クリア（共通関数使用）
            clear_session_history("watch_history")
            if "watch_settings" in session:
                session.pop("watch_settings", None)
                session.modified = True
        else:
            # シナリオモードの履歴クリア
            selected_model = request.json.get("model", "llama2")
            scenario_id = request.json.get("scenario_id")
            
            if scenario_id:
                # 特定のシナリオ履歴をクリア（共通関数使用）
                clear_session_history("scenario_history", scenario_id)
            else:
                # 古い履歴形式との互換性維持
                if "conversation_history" in session and selected_model in session["conversation_history"]:
                    session["conversation_history"][selected_model] = []
                    session.modified = True

        return jsonify({
            "status": "success", 
            "message": "会話履歴がクリアされました"
        })

    except Exception as e:
        print(f"Error in clear_history: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"履歴のクリアに失敗しました: {str(e)}"
        }), 500

@app.route("/api/scenario_chat", methods=["POST"])
# @CSRFToken.require_csrf  # TODO: CSRF保護を後で有効化
def scenario_chat():
    """
    ロールプレイモード専用のチャットAPI
    """
    try:
        data = request.json
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        # 入力値のサニタイズ
        user_message = SecurityUtils.sanitize_input(data.get("message", ""))
        scenario_id = data.get("scenario_id", "")
        selected_model = data.get("model", DEFAULT_MODEL)
        
        # 入力検証
        if not SecurityUtils.validate_scenario_id(scenario_id):
            return jsonify({"error": "無効なシナリオIDです"}), 400
        if not SecurityUtils.validate_model_name(selected_model):
            return jsonify({"error": "無効なモデル名です"}), 400
        
        print(f"Received request: message={user_message}, scenario_id={scenario_id}, model={selected_model}")
        
        # シナリオロードエラー時の対応
        if not scenarios:
            return jsonify({"error": "シナリオデータが利用できません。管理者にお問い合わせください。"}), 503
        
        if not scenario_id or scenario_id not in scenarios:
            print(f"❌ シナリオID検証失敗: '{scenario_id}', 利用可能: {list(scenarios.keys())[:5]}")
            return jsonify({"error": "無効なシナリオIDです"}), 400

        scenario_data = scenarios[scenario_id]
        
        # リバースロール（上司役）の場合の処理
        is_reverse_role = scenario_data.get('role_type') == 'reverse'
        
        # セッション初期化（共通関数使用）
        initialize_session_history("scenario_history", scenario_id)
        
        # 初回メッセージの場合はセッション開始時間を記録
        if len(session["scenario_history"].get(scenario_id, [])) == 0:
            set_session_start_time("scenario", scenario_id)

        # システムプロンプトを構築
        if is_reverse_role:
            # リバースロール用のシステムプロンプト
            system_prompt = scenario_data.get("system_prompt", "")
        else:
            # 従来のシステムプロンプト
            # 安全な .get() を使用してネストされた辞書にアクセス
            character_setting = scenario_data.get("character_setting", {})
            personality = character_setting.get("personality", "未設定")
            speaking_style = character_setting.get("speaking_style", "未設定")
            situation = character_setting.get("situation", "未設定")
            initial_approach = character_setting.get("initial_approach", "未設定")

            system_prompt = f"""
# ロールプレイの基本設定
あなたは{scenario_data.get("role_info", "AI,不明").split("、")[0].replace("AIは", "")}として振る舞います。

## キャラクター詳細
- 性格: {personality}
- 話し方: {speaking_style}
- 現在の状況: {situation}

## 演技の指針
1. 一貫性：設定された役柄を終始一貫して演じ続けること
2. 自然さ：指定された話し方を守りながら、不自然にならないよう注意
3. 感情表現：
   - 表情や態度も含めて表現（例：「困ったように眉をひそめながら」）
   - 感情の変化を適度に表現
4. 反応の適切さ：
   - 相手の発言内容に対する適切な理解と反応
   - 文脈に沿った返答
5. 会話の自然な展開：
   - 一方的な会話を避ける
   - 適度な質問や確認を含める
   - 相手の反応を見ながら会話を進める

## 会話の制約
1. 返答の長さ：1回の発言は3行程度まで
2. 話題の一貫性：急な話題転換を避ける
3. 職場らしさ：敬語と略語を適切に使い分ける

## 現在の文脈
{scenario_data.get("description", "説明なし")} 

## 特記事項
- ユーザーの成長を促す反応を心がける
- 極端な否定は避け、建設的な対話を維持
- 必要に応じて適度な困難さを提示
"""

        # デフォルトのレスポンス
        response = ""
        
        try:
            # 会話履歴の構築
            messages: List[BaseMessage] = []
            messages.append(SystemMessage(content=system_prompt))
            
            # 共通関数を使用して履歴からメッセージを構築
            add_messages_from_history(messages, session["scenario_history"][scenario_id])

            # 新しいメッセージの処理
            if len(session["scenario_history"][scenario_id]) == 0:
                # 初回メッセージの場合
                if is_reverse_role:
                    # リバースロール：初回は状況説明のみを返す
                    if not user_message:
                        initial_context = scenario_data.get("initial_context", "")
                        initial_message = f"【状況】\n{initial_context}\n\n（部下があなたの指示を待っています。上司として最初の声かけをしてください）"
                        # セッションに履歴を保存
                        add_to_session_history("scenario_history", {
                            "human": "[シナリオ開始]",
                            "ai": initial_message
                        }, scenario_id)
                        return jsonify({"response": SecurityUtils.escape_html(initial_message)})
                    else:
                        # ユーザーの最初の発言に対する応答
                        messages.append(HumanMessage(content=user_message))
                else:
                    # 従来のロール：AIから話しかける
                    initial_approach = scenario_data.get("character_setting", {}).get("initial_approach", "自然に")
                    prompt = f"""
最初の声掛けとして、{initial_approach}という設定で
話しかけてください。感情や表情も自然に含めて表現してください。
"""
                    messages.append(HumanMessage(content=prompt))
            else:
                # 通常の会話の場合
                messages.append(HumanMessage(content=user_message))

            # 共通関数を使用して応答を生成
            response = create_model_and_get_response(selected_model, messages)
            
        except Exception as e:
            # LLMエラーを処理
            app_error = handle_llm_specific_error(e, "Gemini")
            print(f"Error in chat: {app_error.message}")
            response = f"申し訳ありません。{app_error.message}"

        # セッションに履歴を保存（共通関数使用）
        add_to_session_history("scenario_history", {
            "human": user_message if user_message else "[シナリオ開始]",
            "ai": response
        }, scenario_id)

        # レスポンスをエスケープして返す
        return jsonify({"response": SecurityUtils.escape_html(response)})

    except Exception as e:
        print(f"Conversation error: {str(e)}")
        # エラーメッセージを安全に返す
        error_msg = SecurityUtils.get_safe_error_message(e)
        return jsonify({"error": f"会話処理中にエラーが発生しました: {error_msg}"}), 500

@app.route("/api/scenario_clear", methods=["POST"])
def clear_scenario_history():
    """
    特定のシナリオの履歴をクリアする
    """
    try:
        data = request.json
        if not data or "scenario_id" not in data:
            return jsonify({"error": "シナリオIDが必要です"}), 400

        scenario_id = data["scenario_id"]
        if scenario_id not in scenarios:
            return jsonify({"error": "無効なシナリオIDです"}), 400

        # 履歴クリア（共通関数使用）
        clear_session_history("scenario_history", scenario_id)

        return jsonify({
            "status": "success",
            "message": "シナリオ履歴がクリアされました"
        })

    except Exception as e:
        print(f"Error clearing scenario history: {str(e)}")
        return jsonify({
            "error": f"履歴のクリアに失敗しました: {SecurityUtils.get_safe_error_message(e)}"
        }), 500

@app.route("/api/watch/start", methods=["POST"])
@secure_error_handler
# @CSRFToken.require_csrf  # TODO: CSRF保護を後で有効化
def start_watch():
    """会話観戦モードの開始"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        # 入力値のサニタイズと検証
        model_a = data.get("model_a")
        model_b = data.get("model_b")
        
        # モデル名の検証
        if not SecurityUtils.validate_model_name(model_a):
            return jsonify({"error": "無効なモデルA名です"}), 400
        if not SecurityUtils.validate_model_name(model_b):
            return jsonify({"error": "無効なモデルB名です"}), 400
            
        partner_type = SecurityUtils.sanitize_input(data.get("partner_type", ""))
        situation = SecurityUtils.sanitize_input(data.get("situation", ""))
        topic = SecurityUtils.sanitize_input(data.get("topic", ""))

        # セッションの初期化（共通関数使用）
        clear_session_history("watch_history")
        session["watch_settings"] = {
            "model_a": model_a,
            "model_b": model_b,
            "partner_type": partner_type,
            "situation": situation,
            "topic": topic,
            "current_speaker": "A",
            "start_time": datetime.now().isoformat()  # 開始時間を記録
        }
        session.modified = True

        try:
            # 観戦の初期メッセージを生成
            llm = initialize_llm(model_a)
            initial_message = generate_initial_message(
                llm, partner_type, situation, topic
            )
            
            # 履歴に保存
            session["watch_history"] = [{
                "speaker": "A", 
                "message": initial_message,
                "timestamp": datetime.now().isoformat()
            }]
            
            return jsonify({"message": f"太郎: {initial_message}"})

        except Exception as e:
            print(f"Error in watch initialization: {str(e)}")
            raise ExternalAPIError(
                service="LLM", 
                message="観戦の初期化に失敗しました"
            )

    except Exception as e:
        # 外側tryブロックのexceptハンドラ
        print(f"Error in start_watch: {str(e)}")
        return jsonify({
            "error": f"観戦モードの開始に失敗しました: {SecurityUtils.get_safe_error_message(e)}"
        }), 500

@app.route("/api/watch/next", methods=["POST"])
@secure_error_handler
# @CSRFToken.require_csrf  # TODO: CSRF保護を後で有効化
def next_watch_message() -> Any:
    """次の発言を生成"""
    try:
        if "watch_settings" not in session:
            return jsonify({"error": "観戦セッションが初期化されていません"}), 400

        settings = session["watch_settings"]
        history = session["watch_history"]

        # 次の話者を決定
        current_speaker = settings["current_speaker"]
        next_speaker = "B" if current_speaker == "A" else "A"
        model = settings["model_b"] if next_speaker == "B" else settings["model_a"]
        # 表示名を設定
        display_name = "花子" if next_speaker == "B" else "太郎"

        try:
            # 共通関数を使用して応答を生成
            try:
                # まずLLMを初期化
                llm = initialize_llm(model)
                # 次のメッセージを生成
                next_message = generate_next_message(llm, history)
            except Exception as e:
                # LLMエラーを処理
                app_error = handle_llm_specific_error(e, model)
                return jsonify({"error": app_error.message}), app_error.status_code
            
            # 履歴に保存
            history.append({
                "speaker": next_speaker,
                "message": next_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # 話者を更新
            settings["current_speaker"] = next_speaker
            session.modified = True

            return jsonify({"message": f"{display_name}: {next_message}"})

        except Exception as e:
            print(f"Error generating next message: {str(e)}")
            raise ExternalAPIError(
                service="LLM",
                message="メッセージの生成に失敗しました"
            )

    except Exception as e:
        # 外側tryブロックのexceptハンドラ
        print(f"Error in next_watch_message: {str(e)}")
        return jsonify({
            "error": f"次のメッセージ生成に失敗しました: {SecurityUtils.get_safe_error_message(e)}"
        }), 500

def generate_next_message(llm, history):
    """観戦モードの次のメッセージを生成"""
    # 会話履歴をフォーマット
    formatted_history = []
    for entry in history:
        # 話者AとBを太郎と花子に置き換え
        speaker_name = "太郎" if entry['speaker'] == "A" else "花子"
        formatted_history.append(f"{speaker_name}: {entry['message']}")
    
    system_prompt = """あなたは職場での自然な会話を行うAIです。
以下の点に注意して会話を続けてください：

1. 前の発言に適切に応答する
2. 職場での適切な距離感を保つ
3. 自然な会話の流れを維持する
4. 話題を適度に展開する

応答の制約：
- 感情や仕草は（）内に記述
- 発言は「」で囲む
- 1回の応答は3行程度まで
- 必ず日本語のみを使用する
- ローマ字や英語は使用しない
- 重要：話者名（太郎、花子など）を含めず、発言内容のみを返してください
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="以下の会話履歴に基づいて、次の発言をしてください：\n\n" + "\n".join(formatted_history))
    ]
    
    response = llm.invoke(messages)
    content = extract_content(response)
    
    # バックアップ機能：名前パターンを除去（太郎: や 花子: など）
    content = re.sub(r'^(太郎|花子):\s*', '', content.strip())
    
    return content

@app.route("/api/get_assist", methods=["POST"])
@with_error_handling
def get_assist() -> Any:
    """AIアシストの提案を取得するエンドポイント"""
    data = request.get_json()
    scenario_id = data.get("scenario_id")
    current_context = data.get("current_context", "")

    if not scenario_id:
        raise ValidationError("シナリオIDが必要です")

    # シナリオ情報を取得
    scenario = scenarios.get(scenario_id)
    if not scenario:
        raise NotFoundError("シナリオ", scenario_id)

    # AIアシストのプロンプトを作成
    assist_prompt = f"""
現在のシナリオ: {scenario.get('title', '無題のシナリオ')}
状況: {scenario.get('description', '説明なし')}
学習ポイント: {', '.join(scenario.get('learning_points', []))}

現在の会話:
{current_context}

上記の状況で、適切な返答のヒントを1-2文で簡潔に提案してください。
"""

    # 選択されているモデルを取得
    selected_model = session.get("selected_model", DEFAULT_MODEL)
    
    # 共通関数を使用して応答を生成
    suggestion = create_model_and_get_response(selected_model, assist_prompt)
    return jsonify({"suggestion": suggestion})

# もし消えてしまった場合に備えてextract_content関数の再追加
def extract_content(resp: Any) -> str:
    """様々な形式のレスポンスから内容を抽出"""
    if isinstance(resp, AIMessage):
        return str(resp.content)
    elif isinstance(resp, str):
        return resp
    elif isinstance(resp, list):
        if not resp:  # 空リストの場合
            return "応答が空でした。"
        # リストの最後のメッセージを処理
        last_msg = resp[-1]
        return extract_content(last_msg)  # 再帰的に処理
    elif isinstance(resp, dict):
        # 辞書の場合、contentキーを探す
        if "content" in resp:
            return str(resp["content"])
        # その他の既知のキーを確認
        for key in ["text", "message", "response"]:
            if key in resp:
                return str(resp[key])
    # 上記以外の場合は文字列に変換して返す
    try:
        return str(resp)
    except Exception:
        return "応答を文字列に変換できませんでした。"

# もし消えてしまった場合に備えてinitialize_llm関数の再追加
def initialize_llm(model_name: str):
    """モデル名に基づいて適切なLLMを初期化"""
    try:
        if model_name.startswith('gemini/'):
            return create_gemini_llm(model_name.replace('gemini/', ''))
        else:
            # gemini/プレフィックスがない場合もGeminiとして処理
            return create_gemini_llm(model_name)
    except Exception as e:
        print(f"Error in initialize_llm: {str(e)}")
        raise

# 欠けている関数を追加

# format_conversation_history関数の追加
def format_conversation_history(history):
    """会話履歴を読みやすい形式にフォーマット（ユーザーの発言のみ）"""
    formatted = []
    for entry in history:
        # ユーザーの発言のみを含める
        if entry.get("human"):
            formatted.append(f"ユーザー: {entry['human']}")
    return "\n".join(formatted)

def format_conversation_history_for_feedback(history):
    """フィードバック分析用に、AIとユーザー双方の会話履歴をフォーマットする"""
    formatted = []
    for entry in history:
        # 内部的な開始メッセージは分析に不要なため除外
        if entry.get("human") and entry["human"] not in ("[シナリオ開始]", "[雑談開始]"):
            formatted.append(f"ユーザー: {entry['human']}")
        if entry.get("ai"):
            # AIからの初期状況説明なども除外した方が分析精度が上がる可能性がある
            # が、一旦はすべてのAI発言を含める
            formatted.append(f"AI: {entry['ai']}")
    return "\n".join(formatted)

# get_partner_description関数の追加
def get_partner_description(partner_type: str) -> str:
    """相手の説明を取得"""
    descriptions = {
        "colleague": "同年代の同僚",
        "senior": "入社5年目程度の先輩社員",
        "junior": "入社2年目の後輩社員",
        "boss": "40代の課長",
        "client": "取引先の担当者（30代後半）"
    }
    return descriptions.get(partner_type, "同僚")

# get_situation_description関数の追加
def get_situation_description(situation: str) -> str:
    """状況の説明を取得"""
    descriptions = {
        "lunch": "ランチ休憩中のカフェテリアで",
        "break": "午後の休憩時間、休憩スペースで",
        "morning": "朝、オフィスに到着して席に着く前",
        "evening": "終業後、退社準備をしている時間",
        "party": "部署の懇親会で"
    }
    return descriptions.get(situation, "オフィスで")

# get_topic_description関数の追加
def get_topic_description(topic: str) -> str:
    """話題の説明を取得"""
    descriptions = {
        "general": "天気や週末の予定など、一般的な話題",
        "hobby": "趣味や休日の過ごし方について",
        "news": "最近のニュースや時事問題について",
        "food": "ランチや食事、おすすめのお店について",
        "work": "仕事に関する一般的な内容（機密情報は避ける）"
    }
    return descriptions.get(topic, "一般的な話題")

# モデル情報取得のヘルパー関数を追加
def get_all_available_models():
    """
    すべての利用可能なモデルを取得し、カテゴリ別に整理する
    
    Returns:
        dict: カテゴリ別モデルのマップと、全モデルリスト
    """
    try:
        # Geminiモデル取得
        gemini_models = get_available_gemini_models()
        
        # 文字列リストから辞書リストに変換
        model_dicts = []
        for model_id in gemini_models:
            model_dicts.append({
                "id": model_id,
                "name": model_id.split('/')[-1],  # gemini/xxx -> xxx
                "provider": "gemini"
            })
        
        return {
            "models": model_dicts,
            "categories": {
                "gemini": model_dicts
            }
        }
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        # 基本的なモデルリストでフォールバック
        basic_models = [
            {"id": "gemini/gemini-1.5-pro", "name": "gemini-1.5-pro", "provider": "gemini"},
            {"id": "gemini/gemini-1.5-flash", "name": "gemini-1.5-flash", "provider": "gemini"}
        ]
        return {
            "models": basic_models,
            "categories": {
                "gemini": basic_models
            }
        }

# 削除されたルートと関数を復元

@app.route('/favicon.ico')
def favicon():
    """ファビコンを返す（存在する場合）"""
    try:
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )
    except:
        # favicon.icoが存在しない場合は204 No Contentを返す
        return '', 204

@app.route("/api/feature_flags", methods=["GET"])
def get_feature_flags_api():
    """
    現在の機能フラグ設定を返すAPIエンドポイント
    フロントエンドが機能の有効/無効を判断するために使用
    """
    try:
        flags = get_feature_flags()
        return jsonify(flags.to_dict())
    except Exception as e:
        print(f"Error getting feature flags: {str(e)}")
        return jsonify({"error": "Failed to get feature flags"}), 500

@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """
    CSRFトークンを取得するエンドポイント
    クライアントがCSRFトークンを取得するために使用
    """
    try:
        from utils.security import CSRFToken
        
        # セッションにCSRFトークンを生成または既存のものを取得
        csrf_token = CSRFToken.get_or_create(session)
        
        return jsonify({
            'csrf_token': csrf_token,
            'expires_in': 3600  # 1時間有効
        })
    except Exception as e:
        # CSRFTokenが存在しない場合のフォールバック
        import secrets
        csrf_token = session.get('csrf_token')
        if not csrf_token:
            csrf_token = secrets.token_hex(16)
            session['csrf_token'] = csrf_token
            session.modified = True
        
        return jsonify({
            'csrf_token': csrf_token,
            'expires_in': 3600
        })

@app.route("/api/models", methods=["GET"])
@with_error_handling
def api_models():
    """
    利用可能なGeminiモデル一覧を返す
    """
    # モデル選択機能が無効化されている場合の処理
    if not is_model_selection_enabled():
        config = get_cached_config()
        return jsonify({
            "models": [{"name": config.DEFAULT_MODEL, "display_name": "Default Model"}],
            "feature_disabled": True,
            "message": "モデル選択機能は現在無効化されています。"
        })
    
    # 共通関数を使用してモデル情報を取得
    model_info = get_all_available_models()
    return jsonify(model_info)


@app.route("/api/feature_flags", methods=["GET"])
@with_error_handling
def api_feature_flags():
    """
    機能フラグの状態を返すAPI
    フロントエンドで機能の有効/無効を判定するために使用
    """
    try:
        flags = FeatureFlags.get_all_flags()
        return jsonify(flags)
    except Exception as e:
        return jsonify({
            "error": "Failed to get feature flags",
            "message": str(e)
        }), 500

# シナリオ一覧を表示するページ
@app.route("/scenarios")
def list_scenarios():
    """シナリオ一覧ページ"""
    # 共通関数を使用してモデル情報を取得
    model_info = get_all_available_models()
    available_models = model_info["models"]
    
    return render_template(
        "scenarios_list.html",
        scenarios=scenarios,
        models=available_models
    )

# シナリオを選択してロールプレイ画面へ
@app.route("/scenario/<scenario_id>")
def show_scenario(scenario_id):
    """シナリオページの表示"""
    if scenario_id not in scenarios:
        return "シナリオが見つかりません", 404

    # シナリオ履歴の初期化（共通関数使用）
    initialize_session_history("scenario_history", scenario_id)

    # シナリオIDに基づいてカテゴリを判定し、戻り先URLを決定
    if is_harassment_scenario(scenario_id):
        back_url = url_for('list_harassment_scenarios')
    else:
        back_url = url_for('list_regular_scenarios')

    # フィーチャーフラグを取得（エラーハンドリング付き）
    try:
        feature_flags = get_feature_flags()
        # 正しいプロパティ名を使用
        enable_tts = feature_flags.tts_enabled
        enable_learning_history = feature_flags.learning_history_enabled
    except (AttributeError, Exception) as e:
        # エラー時はデフォルト値を使用
        print(f"Warning: Failed to get feature flags: {e}")
        enable_tts = False
        enable_learning_history = False
    
    return render_template(
        "scenario.html",
        scenario_id=scenario_id,
        scenario_title=scenarios[scenario_id].get("title", "無題のシナリオ"),
        scenario_desc=scenarios[scenario_id].get("description", "説明がありません。"),
        scenario=scenarios[scenario_id],
        default_model=DEFAULT_MODEL,
        back_url=back_url,  # テンプレートに戻り先URLを渡す
        enable_tts=enable_tts,
        enable_learning_history=enable_learning_history
    )

# 新規: カテゴリ分けされたシナリオ一覧を取得するAPIエンドポイント
@app.route("/api/categorized_scenarios")
@with_error_handling
def get_categorized_scenarios_api():
    """カテゴリ分けされたシナリオ一覧をJSON形式で返す"""
    scenario_summary = get_scenario_category_summary()
    return jsonify(scenario_summary)

# 新規: 通常のコミュニケーションシナリオ一覧ページ
@app.route("/scenarios/regular")
@with_error_handling
def list_regular_scenarios():
    """通常のコミュニケーションシナリオ一覧ページ"""
    regular_scenarios, _ = get_categorized_scenarios()
    
    # 共通関数を使用してモデル情報を取得
    model_info = get_all_available_models()
    available_models = model_info["models"]
    
    return render_template(
        "scenarios/regular_list.html",
        scenarios=regular_scenarios,
        models=available_models,
        category="regular_communication"
    )

# 新規: ハラスメント防止シナリオ一覧ページ
@app.route("/scenarios/harassment")
@with_error_handling
def list_harassment_scenarios():
    """ハラスメント防止シナリオ一覧ページ（同意チェック付き）"""
    # セッションで同意状態を確認
    harassment_consent = session.get('harassment_consent', False)
    
    if not harassment_consent:
        # 同意画面にリダイレクト
        return render_template(
            "scenarios/harassment_consent.html",
            next_url="/scenarios/harassment"
        )
    
    _, harassment_scenarios = get_categorized_scenarios()
    
    # 共通関数を使用してモデル情報を取得
    model_info = get_all_available_models()
    available_models = model_info["models"]
    
    return render_template(
        "scenarios/harassment_list.html",
        scenarios=harassment_scenarios,
        models=available_models,
        category="harassment_prevention"
    )

# 新規: ハラスメント防止研修同意処理
@app.route("/harassment/consent", methods=["GET", "POST"])
def harassment_consent():
    """ハラスメント防止研修の同意画面・処理"""
    if request.method == "GET":
        return render_template("scenarios/harassment_consent.html")
    
    elif request.method == "POST":
        data = request.get_json()
        consent = data.get('consent', False)
        
        if consent:
            # セッションに同意状態を保存
            session['harassment_consent'] = True
            session['harassment_consent_timestamp'] = datetime.now().isoformat()
            session.modified = True
            
            return jsonify({
                "success": True,
                "redirect_url": "/scenarios/harassment"
            })
        else:
            return jsonify({
                "success": False,
                "message": "ハラスメント防止研修にアクセスするには同意が必要です。"
            })

# 新規: シナリオのカテゴリ判定API
@app.route("/api/scenario/<scenario_id>/category")
@with_error_handling
def get_scenario_category(scenario_id):
    """指定シナリオのカテゴリを返す"""
    if scenario_id not in scenarios:
        raise NotFoundError("シナリオ", scenario_id)
    
    is_harassment = is_harassment_scenario(scenario_id)
    category = "harassment_prevention" if is_harassment else "regular_communication"
    
    return jsonify({
        "scenario_id": scenario_id,
        "category": category,
        "requires_consent": is_harassment
    })

# モデル試行パターンを統一するためのヘルパー関数
def try_multiple_models_for_prompt(prompt: str, preferred_model: Optional[str] = None) -> Tuple[str, str, Optional[str]]:
    """
    Geminiモデルを使用してプロンプトに対する応答を取得するヘルパー関数
    
    Args:
        prompt: LLMに与えるプロンプト
        preferred_model: 優先使用するモデル名（オプション）
        
    Returns:
        (応答内容, 使用したモデル名, エラーメッセージ)のタプル。
        モデルが失敗した場合はエラーメッセージを返す。
    """
    content = None
    used_model = None
    error_msg = None
    
    try:
        # 🚨 CRITICAL FIX: ユーザーが選択したモデルを優先使用
        gemini_models = get_available_gemini_models()
        
        if preferred_model:
            # ユーザーが指定したモデルを優先
            # モデル名の正規化: gemini-1.5-flash -> gemini/gemini-1.5-flash
            if not preferred_model.startswith('gemini/'):
                normalized_model = f"gemini/{preferred_model}"
            else:
                normalized_model = preferred_model
                
            if normalized_model in gemini_models:
                model_name = normalized_model
                print(f"Using user-selected model for feedback: {model_name}")
            else:
                # 指定されたモデルが利用不可の場合、Flashモデルを優先
                flash_models = [m for m in gemini_models if 'flash' in m.lower()]
                if flash_models:
                    model_name = flash_models[0]
                    print(f"User model unavailable, falling back to Flash: {model_name}")
                else:
                    model_name = gemini_models[0] if gemini_models else None
                    print(f"Using fallback model: {model_name}")
        elif gemini_models:
            # モデルが指定されていない場合はFlashモデルを優先（コスト16倍削減）
            flash_models = [m for m in gemini_models if 'flash' in m.lower()]
            if flash_models:
                model_name = flash_models[0]
                print(f"Using cost-effective Flash model: {model_name}")
            else:
                model_name = gemini_models[0]
                print(f"No Flash model available, using: {model_name}")
        else:
            model_name = None
            
        print(f"Available models: {gemini_models}")
        
        if not model_name:
            error_msg = "No Gemini models available"
            print(error_msg)
            return None, None, error_msg
            
        # 🚨 CRITICAL FIX: 文字列をHumanMessageに変換してレート制限エラーを回避
        from langchain.schema import HumanMessage
        messages = [HumanMessage(content=prompt)]
        content_result = create_model_and_get_response(model_name, messages)
        
        # 確実に文字列になるように変換
        content = str(content_result) if content_result is not None else ""
        used_model = model_name
        print(f"Successfully generated content using {used_model}")
        return content, used_model, None
    except ResourceExhausted as e:
        print(f"Gemini API rate limit exceeded: {str(e)}")
        error_msg = "RATE_LIMIT_EXCEEDED"  # レート制限用の特別なマーカー
    except Exception as gemini_error:
        # 詳細なエラーログを出力
        print(f"=" * 60)
        print(f"Gemini model error in try_multiple_models_for_prompt:")
        print(f"Error type: {type(gemini_error).__name__}")
        print(f"Error message: {str(gemini_error)}")
        print(f"Model attempted: {model_name if 'model_name' in locals() else 'Unknown'}")
        print(f"Prompt length: {len(prompt)} characters")
        print(f"Prompt preview: {prompt[:200]}...")
        print(f"=" * 60)
        
        error_msg = str(gemini_error)
        # レート制限エラーの文字列パターンをチェック
        if any(keyword in str(gemini_error).lower() for keyword in ["rate limit", "quota", "レート制限", "429"]):
            error_msg = "RATE_LIMIT_EXCEEDED"
    
    # Geminiが失敗した場合
    return "", "", error_msg or "Gemini model error occurred"

# ========== 会話履歴処理のヘルパー関数 ==========
def add_messages_from_history(messages: List[BaseMessage], history, max_entries=5):
    """
    会話履歴からメッセージリストを構築するヘルパー関数
    
    Args:
        messages: 追加先のメッセージリスト
        history: 会話履歴（辞書のリスト）
        max_entries: 取得する最大エントリ数
    """
    # 直近の会話履歴を追加（トークン数削減のため最新n件のみ）
    recent_history = history[-max_entries:] if history else []
    
    for entry in recent_history:
        if entry.get("human"):
            messages.append(HumanMessage(content=entry["human"]))
        if entry.get("ai"):
            messages.append(AIMessage(content=entry["ai"]))
    
    return messages

# シナリオフィードバック関数を更新
@app.route("/api/scenario_feedback", methods=["POST"])
# @CSRFToken.require_csrf  # TODO: CSRF保護を後で有効化
def get_scenario_feedback():
    """シナリオの会話履歴に基づくフィードバックを生成"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        scenario_id = data.get("scenario_id")
        selected_model = data.get("model")  # ユーザーが選択したモデルを取得
        if not scenario_id or scenario_id not in scenarios:
            return jsonify({"error": "無効なシナリオIDです"}), 400

        # 会話履歴を取得
        if "scenario_history" not in session or scenario_id not in session["scenario_history"]:
            return jsonify({"error": "会話履歴が見つかりません"}), 404

        history = session["scenario_history"][scenario_id]
        scenario_data = scenarios.get(scenario_id, {})
        
        # リバースロール（上司役）かどうかチェック
        is_reverse_role = scenario_data.get('role_type') == 'reverse'

        # 安全にユーザーの役割を取得するヘルパー関数
        def get_user_role(scenario_data):
            if is_reverse_role:
                return scenario_data.get("user_role", "上司")
            else:
                role_info_str = scenario_data.get("role_info", "")
                if not isinstance(role_info_str, str):
                    return "不明"
                parts = role_info_str.split("、")
                return parts[1] if len(parts) > 1 else "不明"

        # 🚀 5AI協調設計: パワハラ防止シナリオ用強化プロンプト
        # AI-PAIRED: Claude 4 (深度設計) + Gemini 2.5 (簡潔性) + Qwen3-Coder (構造化) + Codex (問題解決) + Cursor (統合)
        # PATTERN: ストロング・スタイル（フィードバック品質重視）
        if is_reverse_role:
            # リバースロール（上司役）用詳細評価プロンプト（修正版）
            feedback_prompt = f"""【パワハラ防止評価】上司役コミュニケーション分析

シナリオ：{scenario_data.get("title", "上司対応練習")}
会話履歴：
{format_conversation_history_for_feedback(history)}

※最重要指示: ユーザーの発言・行動のみを評価してください。AIの行動は評価対象ではありません。
評価対象：「あなた」（ユーザー）の発言・選択・タイミング・配慮のみ
例: ✅「あなたの指示が明確でした」 ❌「AIは理解しようと努力した」

評価基準（ユーザーのみ対象）：
AIの行動・対応・努力・理解度は一切評価しないこと。
🎯 基本スコア（/100点）：権力バランス配慮度
📈 コミュニケーション質：
• 良い点（具体例2点）：「あなたの○○という発言が適切だった」の形式で明示
• 改善点（課題2点）：「あなたが○○を避けるとより良い」の形式で特定
🛠️ 即実行可能アドバイス：
• 明日から使える改善策（1つ）
• 適切な上司言動例（1つ）

※簡潔で実践的な指摘をお願いします。"""
        else:
            # 通常シナリオ用強化フィードバックプロンプト（修正版）
            feedback_prompt = f"""【職場コミュニケーション評価】スキル向上フィードバック

# 指示: 必ずユーザーの視点に立ち、ユーザーが直接行動に移せるように、具体的でポジティブなフィードバックを生成してください。

シナリオ分析：{scenario_data.get("title", "コミュニケーション練習")}
ユーザー役割：{get_user_role(scenario_data)}
会話履歴：
{format_conversation_history_for_feedback(history)}

※最重要指示: ユーザーの発言・行動のみを評価してください。AIの行動は評価対象ではありません。
評価対象：「あなた」（ユーザー）の発言・選択・タイミング・配慮のみ
例: ✅「あなたの説明が分かりやすかった」 ❌「AIは丁寧に対応した」

🔍 ユーザーコミュニケーション分析:
AIの行動・対応・努力・理解度は一切評価しないこと。
📊 総合スコア（/100点）：コミュニケーション効果度
✅ 優秀ポイント（2つ）：「あなたが○○したことが良かった」の形式で評価
⚠️ 成長機会（2つ）：「あなたがもっと○○できると良い」の形式で提案
💡 実践アクション：「明日からあなたが○○すると良い」の形式

※建設的で行動指向なフィードバックを提供してください。"""

        try:
            # デバッグログ追加 - 5AI修正により詳細な追跡を追加
            print(f"[FEEDBACK DEBUG] Starting scenario feedback generation")
            print(f"[FEEDBACK DEBUG] Scenario ID: {scenario_id}")
            print(f"[FEEDBACK DEBUG] User selected model: {selected_model}")
            print(f"[FEEDBACK DEBUG] Prompt length: {len(feedback_prompt)} characters")
            
            # 新しいヘルパー関数を使用してモデルを試行（ユーザー選択モデルを渡す）
            feedback_content, used_model, error_msg = try_multiple_models_for_prompt(feedback_prompt, selected_model)
            
            print(f"[FEEDBACK DEBUG] Result - Content: {bool(feedback_content)}, Model: {used_model}, Error: {error_msg}")
            
            # BUG-01 FIX: 空文字列も有効な応答として扱う
            if error_msg is None:
                # フィードバックレスポンスを作成
                response_data = {
                    "feedback": feedback_content,
                    "scenario": scenario_data.get("title", "無題のシナリオ"),
                    "model_used": used_model,
                }
                
                # 強み分析を追加
                response_data = update_feedback_with_strength_analysis(
                    response_data, "scenario", scenario_id
                )
                
                return jsonify(response_data)
            else:
                # すべてのモデルが失敗した場合
                # レート制限エラーの場合は429を返す
                if error_msg == "RATE_LIMIT_EXCEEDED":
                    return jsonify({
                        "error": "現在、アクセスが集中しているため、フィードバックを生成できませんでした。しばらくしてからもう一度お試しください。",
                        "attempted_models": "Gemini",
                        "retry_after": 60  # 60秒後に再試行を推奨
                    }), 429
                else:
                    # セキュリティ対策: エラー詳細を隠蔽
                    safe_message = SecurityUtils.get_safe_error_message(Exception(error_msg))
                    return jsonify({
                        "error": f"フィードバックの生成に失敗しました: {safe_message}",
                        "attempted_models": "Gemini"
                    }), 503  # Service Unavailable

        except Exception as e:
            print(f"Feedback generation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": f"フィードバックの生成中にエラーが発生しました: {str(e)}"
            }), 500
    
    except Exception as e:
        print(f"Scenario feedback error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"フィードバック処理中にエラーが発生しました: {str(e)}"
        }), 500


# 雑談フィードバック関数も更新
@app.route("/api/chat_feedback", methods=["POST"])
# @CSRFToken.require_csrf  # TODO: CSRF保護を後で有効化
def get_chat_feedback():
    """雑談練習のフィードバックを生成（ユーザーの発言に焦点を当てる）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400
        
        selected_model = data.get("model")  # ユーザーが選択したモデルを取得

        # 会話履歴の取得
        if "chat_history" not in session:
            return jsonify({"error": "会話履歴が見つかりません"}), 404

        # フィードバック用ログ出力
        print("Chat history:", session["chat_history"])
        print("Formatted history:", format_conversation_history(session["chat_history"]))

        # 🚀 5AI協調設計: 雑談スキル用強化フィードバックプロンプト
        # AI-PAIRED: 5AI議論による合意形成（progressive disclosure + 構造化評価）
        # PATTERN: ピンポンプログラミング（実装⇄評価サイクル）
        feedback_prompt = f"""【雑談スキル評価】職場コミュニケーション向上支援

# 指示: 必ずユーザーの視点に立ち、ユーザーが明日から使えるような、実践的で勇気づけられるアドバイスを生成してください。

コンテキスト分析：
👥 対話相手：{get_partner_description(data.get("partner_type"))}
🏢 状況設定：{get_situation_description(data.get("situation"))}
💬 会話履歴：
{format_conversation_history_for_feedback(session["chat_history"])}

※最重要指示: ユーザーの発言・行動のみを評価してください。AIの行動は評価対象ではありません。
評価対象：「あなた」（ユーザー）の発言・選択・タイミング・配慮のみ
例: ✅「あなたの話題選びが適切でした」 ❌「AIは話を合わせようとした」

🎯 ユーザースキル評価システム：
AIの行動・対応・努力・理解度は一切評価しないこと。
📈 雑談効果スコア（/100点）：あなたの関係構築スキル
🌟 コミュニケーション強み（2点）：
• 「あなたの○○が自然だった」「あなたの共感表現が良かった」の形式で評価
❗ 成長ポイント（2点）：
• 「あなたがもっと○○に配慮すると良い」「あなたの話題選択を○○すると良い」の形式
💪 即実践アクション（1つ）：「明日の雑談であなたが○○を試してみる」形式

評価視点：あなたの相手理解力・感情配慮・関係構築能力・場面適応性のみ評価
※職場での良好な人間関係構築に役立つフィードバックを提供"""

        # 新しいヘルパー関数を使用してモデルを試行（ユーザー選択モデルを渡す）
        feedback_content, used_model, error_msg = try_multiple_models_for_prompt(feedback_prompt, selected_model)
        
        # BUG-01 FIX: 空文字列も有効な応答として扱う
        if error_msg is None:
            # フィードバックレスポンスを作成
            response_data = {
                "feedback": feedback_content,
                "model_used": used_model,
                "status": "success"
            }
            
            # 強み分析を追加
            response_data = update_feedback_with_strength_analysis(
                response_data, "chat"
            )
            
            return jsonify(response_data)
        else:
            # すべてのモデルが失敗した場合
            # レート制限エラーの場合は429を返す
            if error_msg == "RATE_LIMIT_EXCEEDED":
                return jsonify({
                    "error": "現在、アクセスが集中しているため、フィードバックを生成できませんでした。しばらくしてからもう一度お試しください。",
                    "attempted_models": "Gemini",
                    "retry_after": 60,
                    "status": "error"
                }), 429
            else:
                # セキュリティ対策: エラー詳細を隠蔽
                safe_message = SecurityUtils.get_safe_error_message(Exception(error_msg))
                return jsonify({
                    "error": f"フィードバックの生成に失敗しました: {safe_message}",
                    "attempted_models": "Gemini",
                    "status": "error"
                }), 503

    except Exception as e:
        print(f"Error in chat_feedback: {str(e)}")
        import traceback
        traceback.print_exc()  # スタックトレースを出力
        return jsonify({
            "error": f"フィードバックの生成中にエラーが発生しました: {str(e)}",
            "status": "error"
        }), 500

def generate_initial_message(llm, partner_type, situation, topic):
    """観戦モードの最初のメッセージを生成"""
    system_prompt = f"""あなたは職場での自然な会話を行うAIです。
以下の点に注意して会話を始めてください：

設定：
- あなたは太郎という名前の社員です
- 相手: 花子という名前の{get_partner_description(partner_type)}
- 状況: {get_situation_description(situation)}
- 話題: {get_topic_description(topic)}

会話の注意点：
1. 設定された相手や状況に応じた適切な話し方をする
2. 自然な会話の流れを作る
3. 相手が話しやすい雰囲気を作る
4. 職場での適切な距離感を保つ

応答の制約：
- 感情や仕草は（）内に記述
- 発言は「」で囲む
- 1回の応答は3行程度まで
- 必ず日本語のみを使用する
- ローマ字や英語は使用しない
- 相手の名前は「花子さん」と呼ぶ

最初の声掛けをしてください。
"""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="会話を始めてください。")
    ]
    response = llm.invoke(messages)
    return extract_content(response)

# 観戦モードのページを表示するルートを追加
@app.route("/watch")
def watch_mode():
    """観戦モードページ"""
    # 観戦モードはモデル情報が不要なため、シンプルにテンプレートを返す
    return render_template("watch.html", feature_flags=feature_flags.to_dict())

# 学習履歴を表示するルートを追加
@app.route("/journal")
@require_feature('learning_history')
def view_journal():
    """学習履歴ページ"""
    # 履歴データを取得
    scenario_history = {}
    
    # セッションから各シナリオの履歴を取得
    if "scenario_history" in session:
        for scenario_id, history in session["scenario_history"].items():
            if scenario_id in scenarios and history:
                scenario_info = scenarios.get(scenario_id, {})
                scenario_history[scenario_id] = {
                    "title": scenario_info.get("title", "不明なシナリオ"),
                    "last_session": history[-1].get("timestamp") if history else None,
                    "sessions_count": len(history), # 1往復を1とカウント
                    "feedback": session.get("scenario_feedback", {}).get(scenario_id)
                }
    
    # 雑談履歴の取得
    chat_history = []
    if "chat_history" in session:
        chat_history = session["chat_history"]
    
    # 最終アクティビティの日時を計算
    last_activity = None
    
    # シナリオ履歴から最新の日時を確認
    for scenario_data in scenario_history.values():
        if scenario_data.get("last_session"):
            if not last_activity or scenario_data["last_session"] > last_activity:
                last_activity = scenario_data["last_session"]
    
    # チャット履歴からも確認
    if chat_history and len(chat_history) > 0:
        chat_last = chat_history[-1].get("timestamp")
        if chat_last:
            if not last_activity or chat_last > last_activity:
                last_activity = chat_last
    
    # 実際の練習時間を計算
    total_minutes = 0
    
    # シナリオの練習時間計算
    if "scenario_settings" in session:
        scenario_settings = session["scenario_settings"]
        for scenario_id, settings in scenario_settings.items():
            if scenario_id in session.get("scenario_history", {}) and session["scenario_history"][scenario_id]:
                # 開始時間と最後のメッセージの時間から計算
                start_time = datetime.fromisoformat(settings.get("start_time", datetime.now().isoformat()))
                last_msg_time = datetime.fromisoformat(session["scenario_history"][scenario_id][-1].get("timestamp", datetime.now().isoformat()))
                
                # 差分を分単位で計算
                time_diff = (last_msg_time - start_time).total_seconds() / 60
                total_minutes += time_diff
    
    # 雑談モードの練習時間計算
    if "chat_settings" in session and "chat_history" in session and session["chat_history"]:
        chat_settings = session["chat_settings"]
        start_time = datetime.fromisoformat(chat_settings.get("start_time", datetime.now().isoformat()))
        last_msg_time = datetime.fromisoformat(session["chat_history"][-1].get("timestamp", datetime.now().isoformat()))
        
        # 差分を分単位で計算
        time_diff = (last_msg_time - start_time).total_seconds() / 60
        total_minutes += time_diff
    
    # 観戦モードの練習時間計算
    if "watch_settings" in session and "watch_history" in session and session["watch_history"]:
        watch_settings = session["watch_settings"]
        start_time = datetime.fromisoformat(watch_settings.get("start_time", datetime.now().isoformat()))
        last_msg_time = datetime.fromisoformat(session["watch_history"][-1].get("timestamp", datetime.now().isoformat()))
        
        # 差分を分単位で計算
        time_diff = (last_msg_time - start_time).total_seconds() / 60
        total_minutes += time_diff
    
    # 時間と分に変換（小数点以下を四捨五入）
    total_minutes = round(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    # 練習時間の文字列を構築
    if hours > 0:
        total_practice_time = f"{hours}時間{minutes}分"
    else:
        total_practice_time = f"{minutes}分"
    
    # もし練習時間が0の場合
    if total_minutes == 0:
        total_practice_time = "まだ記録がありません"
    
    return render_template(
        "journal.html",
        scenario_history=scenario_history,
        chat_history=chat_history,
        last_activity=last_activity,
        total_practice_time=total_practice_time
    )

# 雑談練習開始用のエンドポイントを追加
@app.route("/api/start_chat", methods=["POST"])
@secure_error_handler
def start_chat() -> Any:
    """
    雑談練習を開始するAPI
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400
            
        model_name = data.get("model", DEFAULT_MODEL)
        partner_type = data.get("partner_type", "colleague")
        situation = data.get("situation", "break")
        topic = data.get("topic", "general")
        
        # セッションの初期化と設定の保存
        clear_session_history("chat_history")
        session["chat_settings"] = {
            "model": model_name,
            "partner_type": partner_type,
            "situation": situation,
            "topic": topic,
            "start_time": datetime.now().isoformat(),  # 開始時間を記録
            "system_prompt": f"""あなたは職場での雑談練習をサポートするAIアシスタントです。
# 設定
- 相手: {get_partner_description(partner_type)}
- 状況: {get_situation_description(situation)}
- 話題: {get_topic_description(topic)}

# 会話の方針
1. 指定された立場の人物として自然に振る舞ってください
2. 相手が話しやすいように、適度に質問を投げかけてください
3. 会話の流れを維持するよう努めてください
4. 仕事に関する質問が来ても、機密情報などには言及せず一般的な回答をしてください

# 応答の制約
- 一回の返答は3行程度に収めてください
- 雑談らしい自然な対話を心がけてください
- 敬語と略語のバランスを相手との関係性に合わせて調整してください
- 感情表現を（）内に適度に含めてください"""
        }
        session.modified = True
        
        # 初回メッセージの生成
        first_prompt = f"""
相手: {get_partner_description(partner_type)}
状況: {get_situation_description(situation)}
話題: {get_topic_description(topic)}

上記の設定で、あなたから雑談を始めてください。
最初の声かけとして、状況に応じた自然な挨拶や話題提供をしてください。
"""
        
        try:
            # 共通関数を使用して応答を生成
            response = create_model_and_get_response(model_name, first_prompt)
            
            # 履歴に保存
            add_to_session_history("chat_history", {
                "human": "[雑談開始]",
                "ai": response
            })
            
            return jsonify({"response": response})
            
        except Exception as e:
            # LLMエラーを処理
            app_error = handle_llm_specific_error(e, "Gemini")
            # レート制限エラーの場合は429を返す
            if isinstance(app_error, RateLimitError):
                return jsonify({"error": app_error.message, "retry_after": 60}), 429
            else:
                # 履歴に保存
                add_to_session_history("chat_history", {
                    "human": "[雑談開始]",
                    "ai": f"申し訳ありません。{app_error.message}"
                })
                
                return jsonify({"error": app_error.message}), app_error.status_code
                
    except Exception as e:
        # 外側tryブロックのexceptハンドラ
        print(f"Error in start_chat: {str(e)}")
        return jsonify({
            "error": f"雑談開始に失敗しました: {SecurityUtils.get_safe_error_message(e)}"
        }), 500

@app.route("/api/conversation_history", methods=["POST"])
@with_error_handling
def get_conversation_history():
    """
    会話履歴を取得するAPI
    """
    data = request.get_json()
    history_type = data.get("type")
    
    if history_type == "scenario":
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            raise ValidationError("シナリオIDが必要です")
            
        # 指定されたシナリオの履歴を取得
        if "scenario_history" not in session or scenario_id not in session["scenario_history"]:
            return jsonify({"history": []})
            
        return jsonify({"history": session["scenario_history"][scenario_id]})
        
    elif history_type == "chat":
        # 雑談履歴を取得
        if "chat_history" not in session:
            return jsonify({"history": []})
            
        return jsonify({"history": session["chat_history"]})
        
    elif history_type == "watch":
        # 観戦履歴を取得
        if "watch_history" not in session:
            return jsonify({"history": []})
            
        # 観戦履歴は形式が異なるので変換
        watch_history = []
        for entry in session["watch_history"]:
            watch_history.append({
                "timestamp": entry.get("timestamp"),
                "human" if entry["speaker"] == "A" else "ai": entry["message"]
            })
            
        return jsonify({"history": watch_history})
        
    else:
        raise ValidationError("不明な履歴タイプです")

@app.route("/api/tts", methods=["POST", "HEAD"])
@require_feature('tts')
@with_error_handling
def text_to_speech():
    """
    テキストを音声に変換するAPI
    フィーチャフラグ制御により、無効化されている場合は403エラーが返される
    
    HEADリクエスト: フロントエンドでの軽量状態チェック用
    POSTリクエスト: 実際のTTS生成
    """
    # HEADリクエストの場合は軽量レスポンス
    if request.method == "HEAD":
        return "", 200
    
    # POSTリクエストの場合は詳細なエラー情報を返す（現在は機能停止中）
    return jsonify({
        "error": "TTS機能は現在停止中です",
        "message": "高額請求が発生したため、TTS機能を停止しています。",
        "details": {
            "cost": "250,000円 ($1,667)",
            "characters": "16,675,000文字の音声生成",
            "requests": "約166,750回のリクエスト"
        },
        "alternative": "ブラウザ内蔵のWeb Speech APIをご利用ください",
        "fallback_available": True
    }), 503  # Service Temporarily Unavailable
    
    # 以下は無効化されたコード
    """
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
        
        text = data.get("text", "")
        if not text:
            return jsonify({"error": "テキストが必要です"}), 400
        
        # 音声設定（クライアントから指定された音声を使用）
        voice_name = data.get("voice", "kore")  # デフォルトは日本語女性音声（小文字）
        voice_style = data.get("style", None)  # 音声スタイル（オプション）
        emotion = data.get("emotion", None)  # 感情（オプション）
        
        # 感情による音声の自動変更は行わない（シナリオごとに固定音声を使用）
        # if emotion and not data.get("voice"):
        #     voice_name = get_voice_for_emotion(emotion)
        
        try:
            # Gemini TTS APIを使用
            from google import genai
            from google.genai import types
            import base64
            import wave
            import io
            
            # COMPLIANCE FIX: 規約準拠APIキーマネージャーから取得
            current_api_key = get_compliant_google_api_key()
            
            # Geminiクライアントの初期化
            client = genai.Client(api_key=current_api_key)
            
            # プロンプトの構築（スタイルのみ適用、感情は声の表現で）
            prompt = text
            if voice_style:
                prompt = f"{voice_style}: {text}"
            
            # 感情はプロンプトに含めるが、音声は変更しない
            # これにより同じ声優が異なる感情を表現できる
            if emotion and not voice_style:
                emotion_prompts = {
                    "happy": "Say cheerfully",
                    "sad": "Say sadly", 
                    "angry": "Say angrily",
                    "excited": "Say excitedly",
                    "calm": "Say calmly",
                    "tired": "Say tiredly",
                    "worried": "Say worriedly",
                    "confident": "Say confidently",
                    "friendly": "Say in a friendly manner",
                    "professional": "Say professionally",
                    "whisper": "Whisper",
                    "spooky": "Say mysteriously"
                }
                if emotion in emotion_prompts:
                    prompt = f"{emotion_prompts[emotion]}: {text}"
            
            # 音声合成リクエストの作成
            response = client.models.generate_content(
                model="models/gemini-2.5-flash-preview-tts",  # 正しいモデル名
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name.lower(),  # 小文字に変換
                            )
                        )
                    ),
                )
            )
            
            # デバッグ情報を追加
            print(f"TTS Response type: {type(response)}")
            print(f"Has parts: {hasattr(response, 'parts')}")
            print(f"Has candidates: {hasattr(response, 'candidates') and len(response.candidates) if hasattr(response, 'candidates') else 0}")
            
            # 音声データを取得（参考プロジェクトのロジックを使用）
            audio_data = None
            if hasattr(response, 'parts') and response.parts:
                part = response.parts[0]
                print(f"Using response.parts[0], type: {type(part)}")
                if hasattr(part, 'inline_data'):
                    audio_data = part.inline_data.data
                    print(f"Got inline_data.data, size: {len(audio_data) if audio_data else 0}")
            elif response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                print(f"Using candidate[0], type: {type(candidate)}")
                if hasattr(candidate, 'content') and candidate.content and hasattr(candidate.content, 'parts'):
                    part = candidate.content.parts[0]
                    print(f"Got candidate.content.parts[0], type: {type(part)}")
                    if hasattr(part, 'inline_data'):
                        audio_data = part.inline_data.data
                        print(f"Got inline_data.data from candidate, size: {len(audio_data) if audio_data else 0}")
                else:
                    raise ValueError("音声データが返されませんでした")
            else:
                raise ValueError("レスポンスに音声データが含まれていません")
            
            if not audio_data:
                raise ValueError("音声データが空です")
            
            # Base64デコード（必要な場合）
            # 音声データはすでにバイナリ形式なので、そのまま使用
            if isinstance(audio_data, bytes):
                audio_bytes = audio_data
                print(f"Using binary audio data, size: {len(audio_bytes)} bytes")
            elif isinstance(audio_data, str):
                # 文字列の場合はBase64デコード
                try:
                    audio_bytes = base64.b64decode(audio_data)
                    print(f"Base64 decoded successfully, size: {len(audio_bytes)} bytes")
                except Exception as e:
                    print(f"Base64 decode error: {e}")
                    raise ValueError("音声データのデコードに失敗しました")
            else:
                raise ValueError(f"予期しない音声データタイプ: {type(audio_data)}")
            
            # WAVファイルをメモリ上で作成
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wf:
                wf.setnchannels(1)  # モノラル
                wf.setsampwidth(2)  # 16ビット
                wf.setframerate(24000)  # 24kHz
                wf.writeframes(audio_bytes)
            
            # WAVデータを取得
            wav_io.seek(0)
            wav_data = wav_io.read()
            print(f"WAV data created, size: {len(wav_data)} bytes")
            
            # Base64エンコードして返す
            audio_content = base64.b64encode(wav_data).decode('utf-8')
            print(f"Base64 encoded for response, length: {len(audio_content)}")
            
            # COMPLIANCE FIX: 規約準拠API使用記録
            record_compliant_api_usage()
            
            return jsonify({
                "audio": audio_content,
                "format": "wav",
                "voice": voice_name,
                "provider": "gemini"
            })
            
        except Exception as tts_error:
            print(f"TTS error: {str(tts_error)}")
            
            # COMPLIANCE FIX: 規約準拠エラーハンドリング
            handle_compliant_api_error(tts_error)
            
            # エラーの場合はフォールバックとしてWeb Speech APIの使用を提案
            return jsonify({
                "error": "音声合成に失敗しました",
                "details": str(tts_error),
                "fallback": "Web Speech API"
            }), 500
    """        
    # except Exception as e:
    #     print(f"Error in text_to_speech: {str(e)}")
    #     return jsonify({"error": str(e)}), 500

def get_voice_for_emotion(emotion: str) -> str:
    """感情に最適な音声を選択する"""
    emotion_voice_map = {
        "happy": "autonoe",  # 明るい女性音声
        "excited": "fenrir",  # 興奮しやすい男性音声
        "sad": "vindemiatrix",  # 優しい女性音声
        "tired": "enceladus",  # 息づかいのある男性音声
        "angry": "algenib",  # 砂利声の男性音声
        "worried": "achernar",  # ソフトな男性音声
        "calm": "schedar",  # 均等な中性音声
        "confident": "alnilam",  # 確実な男性音声
        "professional": "orus",  # 会社的な男性音声
        "friendly": "achird",  # フレンドリーな男性音声
        "whisper": "enceladus",  # 息づかいのある音声
        "spooky": "umbriel"  # 気楽な中性音声（逆説的に不気味さを演出）
    }
    return emotion_voice_map.get(emotion, "kore")

# 画像キャッシュ（シンプルなメモリキャッシュ）
image_cache = {}
MAX_CACHE_SIZE = 50  # 最大50個までキャッシュ

@app.route("/api/generate_character_image", methods=["POST"])
@secure_error_handler
def generate_character_image():
    """
    AIキャラクターの画像を生成するAPI
    """
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # 必須パラメータの確認
        scenario_id = data.get("scenario_id")
        emotion = data.get("emotion", "neutral")
        text = data.get("text", "")  # AIの応答テキスト（感情検出用）
        
        if not scenario_id:
            return jsonify({"error": "シナリオIDが必要です"}), 400
        
        # シナリオ情報の取得
        if scenario_id not in scenarios:
            return jsonify({"error": "無効なシナリオID"}), 400
        
        scenario = scenarios[scenario_id]
        character_setting = scenario.get("character_setting", {})
        
        # キャラクター情報の解析
        personality = character_setting.get("personality", "")
        
        # 年齢・性別・役職の推定
        age_range = "40s"  # デフォルト
        gender = "male"    # デフォルト
        position = "manager"  # デフォルト
        
        # テキストから情報を抽出
        if "女性" in personality or "female" in personality.lower():
            gender = "female"
        elif "男性" in personality or "male" in personality.lower():
            gender = "male"
        
        if "20代" in personality or "新人" in personality:
            age_range = "20s"
        elif "30代" in personality:
            age_range = "30s"
        elif "40代" in personality:
            age_range = "40s"
        elif "50代" in personality:
            age_range = "50s"
        
        if "部長" in personality:
            position = "department manager"
        elif "課長" in personality:
            position = "section manager"
        elif "先輩" in personality:
            position = "senior colleague"
        elif "同僚" in personality:
            position = "colleague"
        elif "後輩" in personality or "新人" in personality:
            position = "junior colleague"
        
        # 感情から表情への変換（表情のみ変化、人物は同じ）
        emotion_expressions = {
            "happy": "with a warm, genuine smile and bright eyes",
            "sad": "with a concerned, sympathetic expression",
            "angry": "with a slightly frustrated but controlled expression",
            "excited": "with an enthusiastic, energetic expression",
            "worried": "with a worried, concerned look",
            "tired": "looking slightly fatigued but professional",
            "calm": "with a calm, composed expression",
            "confident": "with a confident, assured expression",
            "professional": "with a professional, neutral expression",
            "friendly": "with a friendly, approachable expression",
            "neutral": "with a neutral, attentive expression"
        }
        
        expression = emotion_expressions.get(emotion, emotion_expressions["neutral"])
        
        # 画像生成プロンプトの構築（同一人物を保証するため詳細な特徴を固定）
        gender_text = "woman" if gender == "female" else "man"
        
        # シナリオごとの固定的な外見特徴（キャラクターの一貫性を保つ）
        # 各シナリオには固有の人物を割り当て
        scenario_appearances = {
            # 男性上司系
            "scenario1": "short black hair with slight gray at temples, clean-shaven, rectangular glasses, serious demeanor",
            "scenario3": "graying hair neatly styled, clean-shaven, thin-rimmed glasses, authoritative look",
            "scenario5": "dark hair with professional cut, clean-shaven, no glasses, confident bearing",
            "scenario9": "salt-and-pepper hair, clean-shaven, round glasses, thoughtful expression",
            "scenario11": "silver hair, clean-shaven, no glasses, distinguished appearance",
            "scenario13": "short black hair, clean-shaven, modern glasses, tech-savvy look",
            "scenario16": "well-groomed dark hair, clean-shaven, designer glasses, strategic thinker",
            "scenario22": "athletic build, short hair, clean-shaven, energetic presence",
            "scenario29": "experienced look, graying temples, clean-shaven, warm smile",
            
            # 女性上司・先輩系
            "scenario7": "shoulder-length black hair, professional style, light makeup, leadership aura",
            "scenario15": "bob-cut hair, elegant makeup, pearl earrings, managerial presence",
            "scenario17": "sophisticated short hair, refined makeup, executive appearance",
            "scenario19": "long hair in low ponytail, gentle makeup, mentoring demeanor",
            "scenario26": "stylish medium-length hair, polished makeup, PR professional look",
            
            # 同僚系（デフォルト外見）
            "default_male": "short black hair, clean-shaven, casual professional look",
            "default_female": "medium-length black hair, natural makeup, approachable appearance"
        }
        
        # シナリオに基づいて外見を決定
        if scenario_id in scenario_appearances:
            appearance = scenario_appearances[scenario_id]
        else:
            # デフォルトの外見を使用
            default_key = f"default_{gender}"
            appearance = scenario_appearances.get(default_key, "professional appearance")
        
        # より強力な同一人物指定
        # シナリオごとに固有のシード値を使用
        character_seed = f"character_{scenario_id}_{gender}_{age_range}"
        
        prompt = (f"IMPORTANT: Generate the EXACT SAME person in every image. "
                 f"Character ID: {character_seed}. "
                 f"This is a professional Japanese {gender_text} in their {age_range}, "
                 f"with EXACTLY these features: {appearance}. "
                 f"They must have the SAME face structure, SAME hairstyle, SAME facial features in every image. "
                 f"Only the expression changes to show {expression}. "
                 f"Dressed in appropriate business attire for a {position}, "
                 f"in a modern Japanese office environment, "
                 f"photorealistic portrait style, high quality, "
                 f"professional lighting. "
                 f"CRITICAL: Maintain exact character consistency - same person, only expression differs.")
        
        # 状況に応じた背景の追加
        situation = character_setting.get("situation", "")
        if "会議" in situation:
            prompt += ", meeting room background"
        elif "休憩" in situation or "ランチ" in situation:
            prompt += ", office break room or cafeteria background"
        elif "懇親会" in situation:
            prompt += ", casual office party setting"
        
        # キャッシュキーの生成（シナリオIDと感情のみで構成）
        cache_key = f"{scenario_id}_{emotion}"
        
        # キャッシュチェック
        if cache_key in image_cache:
            print(f"画像キャッシュヒット: {cache_key}")
            cached_data = image_cache[cache_key]
            cached_data["cache_hit"] = True
            return jsonify(cached_data)
        
        try:
            # Gemini Image Generation APIを使用
            from google import genai
            from google.genai import types
            from PIL import Image as PILImage
            from io import BytesIO
            import base64
            
            # Geminiクライアントの初期化
            client = genai.Client(api_key=GOOGLE_API_KEY)
            
            print(f"画像生成開始: {cache_key}")
            
            # 画像生成リクエスト
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )
            
            # レスポンスから画像データを取得
            image_data = None
            generated_text = None
            
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'text') and part.text:
                        generated_text = part.text
                    elif hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
            
            if not image_data:
                raise ValueError("画像データが生成されませんでした")
            
            # 画像データの処理
            if isinstance(image_data, str):
                # すでにBase64の場合
                image_base64 = image_data
            else:
                # バイナリデータの場合はBase64エンコード
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # レスポンスの返却
            response_data = {
                "image": image_base64,
                "format": "png",
                "prompt": prompt,
                "emotion": emotion,
                "character_info": {
                    "age": age_range,
                    "gender": gender,
                    "position": position
                }
            }
            
            if generated_text:
                response_data["description"] = generated_text
            
            # キャッシュに保存（サイズ制限あり）
            if len(image_cache) >= MAX_CACHE_SIZE:
                # 最も古いエントリを削除
                oldest_key = next(iter(image_cache))
                del image_cache[oldest_key]
                print(f"キャッシュサイズ制限により削除: {oldest_key}")
            
            image_cache[cache_key] = response_data.copy()
            print(f"画像をキャッシュに保存: {cache_key}")
            
            return jsonify(response_data)
            
        except Exception as e:
            print(f"Image generation error: {str(e)}")
            raise ExternalAPIError(
                service="Image Generator",
                message="画像生成に失敗しました"
            )
            
    except Exception as e:
        # 外側tryブロックのexceptハンドラ
        print(f"Error in generate_character_image: {str(e)}")
        return jsonify({
            "error": f"画像生成に失敗しました: {SecurityUtils.get_safe_error_message(e)}"
        }), 500

@app.route("/api/tts/voices", methods=["GET"])
def get_available_voices():
    """
    EMERGENCY SHUTDOWN: TTS機能は高額請求により停止中
    """
    return jsonify({
        "error": "TTS音声機能は高額請求により緊急停止中",
        "message": "Gemini TTSで25万円の請求が発生したため、全TTS機能を停止しました",
        "alternative": "ブラウザ内蔵のWeb Speech APIを使用してください"
    }), 503
    
    # 以下は無効化されたコード
    """
    try:
        # Gemini TTSの利用可能な音声（全30種類）
        voices = [
            # 主要な音声（日本語向け推奨）
            {"id": "kore", "name": "Kore - 会社的", "gender": "female", "provider": "gemini", "style": "professional"},
            {"id": "aoede", "name": "Aoede - 軽快", "gender": "female", "provider": "gemini", "style": "breezy"},
            {"id": "callirrhoe", "name": "Callirrhoe - おおらか", "gender": "female", "provider": "gemini", "style": "easygoing"},
            {"id": "leda", "name": "Leda - 若々しい", "gender": "female", "provider": "gemini", "style": "youthful"},
            {"id": "algieba", "name": "Algieba - スムーズ", "gender": "female", "provider": "gemini", "style": "smooth"},
            {"id": "autonoe", "name": "Autonoe - 明るい", "gender": "female", "provider": "gemini", "style": "bright"},
            {"id": "despina", "name": "Despina - スムーズ", "gender": "female", "provider": "gemini", "style": "smooth"},
            {"id": "erinome", "name": "Erinome - クリア", "gender": "female", "provider": "gemini", "style": "clear"},
            {"id": "laomedeia", "name": "Laomedeia - アップビート", "gender": "female", "provider": "gemini", "style": "upbeat"},
            {"id": "pulcherrima", "name": "Pulcherrima - 前向き", "gender": "female", "provider": "gemini", "style": "forward"},
            {"id": "vindemiatrix", "name": "Vindemiatrix - 優しい", "gender": "female", "provider": "gemini", "style": "gentle"},
            
            # 男性音声
            {"id": "enceladus", "name": "Enceladus - 息づかい", "gender": "male", "provider": "gemini", "style": "breathy"},
            {"id": "charon", "name": "Charon - 情報提供的", "gender": "male", "provider": "gemini", "style": "informative"},
            {"id": "fenrir", "name": "Fenrir - 興奮しやすい", "gender": "male", "provider": "gemini", "style": "excitable"},
            {"id": "orus", "name": "Orus - 会社的", "gender": "male", "provider": "gemini", "style": "corporate"},
            {"id": "iapetus", "name": "Iapetus - クリア", "gender": "male", "provider": "gemini", "style": "clear"},
            {"id": "algenib", "name": "Algenib - 砂利声", "gender": "male", "provider": "gemini", "style": "gravelly"},
            {"id": "rasalgethi", "name": "Rasalgethi - 情報豊富", "gender": "male", "provider": "gemini", "style": "informative"},
            {"id": "achernar", "name": "Achernar - ソフト", "gender": "male", "provider": "gemini", "style": "soft"},
            {"id": "alnilam", "name": "Alnilam - 確実", "gender": "male", "provider": "gemini", "style": "assured"},
            {"id": "gacrux", "name": "Gacrux - 成熟", "gender": "male", "provider": "gemini", "style": "mature"},
            {"id": "achird", "name": "Achird - フレンドリー", "gender": "male", "provider": "gemini", "style": "friendly"},
            {"id": "zubenelgenubi", "name": "Zubenelgenubi - カジュアル", "gender": "male", "provider": "gemini", "style": "casual"},
            {"id": "sadachbia", "name": "Sadachbia - 活発", "gender": "male", "provider": "gemini", "style": "lively"},
            {"id": "sadaltager", "name": "Sadaltager - 知識豊富", "gender": "male", "provider": "gemini", "style": "knowledgeable"},
            {"id": "sulafat", "name": "Sulafat - 温かい", "gender": "male", "provider": "gemini", "style": "warm"},
            
            # 中性音声
            {"id": "puck", "name": "Puck - アップビート", "gender": "neutral", "provider": "gemini", "style": "upbeat"},
            {"id": "zephyr", "name": "Zephyr - 明るい", "gender": "neutral", "provider": "gemini", "style": "bright"},
            {"id": "umbriel", "name": "Umbriel - 気楽", "gender": "neutral", "provider": "gemini", "style": "easygoing"},
            {"id": "schedar", "name": "Schedar - 均等", "gender": "neutral", "provider": "gemini", "style": "even"}
        ]
        
        # Web Speech API（フォールバック）
        voices.append({
            "id": "web-speech", 
            "name": "ブラウザ音声合成（フォールバック）", 
            "gender": "various", 
            "provider": "browser"
        })
        
        return jsonify({"voices": voices})
    """    
    # except Exception as e:
    #     print(f"Error in get_available_voices: {str(e)}")
    #     return jsonify({"error": str(e)}), 500

@app.route("/api/tts/styles", methods=["GET"])
def get_available_styles():
    """
    EMERGENCY SHUTDOWN: TTS機能は高額請求により停止中
    """
    return jsonify({
        "error": "TTSスタイル機能は高額請求により緊急停止中",
        "message": "Gemini TTSで25万円の請求が発生したため、全TTS機能を停止しました",
        "alternative": "ブラウザ内蔵のWeb Speech APIを使用してください"
    }), 503
    
    # 以下は無効化されたコード（高額請求のため）
    # try:
    #     styles = {
    #         "emotions": [
    #             {"id": "happy", "name": "楽しい・嬉しい", "description": "明るく元気な感じ"},
    #             {"id": "sad", "name": "悲しい・寂しい", "description": "優しく穏やかな感じ"},
    #             {"id": "angry", "name": "怒り・不満", "description": "力強く断定的な感じ"},
    #             {"id": "excited", "name": "興奮・ワクワク", "description": "活発でエネルギッシュ"},
    #             {"id": "worried", "name": "心配・不安", "description": "控えめで慎重な感じ"},
    #             {"id": "tired", "name": "疲れ・眠い", "description": "ゆっくりと息遣いのある感じ"},
    #             {"id": "calm", "name": "落ち着き・安心", "description": "穏やかで安定した感じ"},
    #             {"id": "confident", "name": "自信・確信", "description": "はっきりと明確な感じ"},
    #             {"id": "professional", "name": "ビジネス・丁寧", "description": "フォーマルで礼儀正しい"},
    #             {"id": "friendly", "name": "親しみ・気さく", "description": "温かく親しみやすい"},
    #             {"id": "whisper", "name": "ささやき", "description": "静かで密やかな感じ"},
    #             {"id": "spooky", "name": "不気味・怖い", "description": "神秘的で薄気味悪い"}
    #         ],
    #         "custom_styles": [
    #             {"example": "in a storytelling manner", "description": "物語を語るような口調で"},
    #             {"example": "like a news anchor", "description": "ニュースキャスターのように"},
    #             {"example": "as if giving a presentation", "description": "プレゼンテーションをするように"},
    #             {"example": "in a comforting way", "description": "慰めるような優しい口調で"},
    #             {"example": "with dramatic emphasis", "description": "ドラマチックに強調して"}
    #         ]
    #     }
    #     
    #     return jsonify(styles)
    #     
    # except Exception as e:
    #     print(f"Error in get_available_styles: {str(e)}")
    #     return jsonify({"error": str(e)}), 500


# ========== 強み分析機能 ==========
@app.route("/strength_analysis")
def strength_analysis_page():
    """強み分析ページを表示"""
    # 強み分析機能が無効化されている場合
    if not is_strength_analysis_enabled():
        return render_template("feature_disabled.html", 
                             feature_name="強み分析",
                             message="強み分析機能は現在無効化されています。")
    
    return render_template("strength_analysis.html")


@app.route("/api/strength_analysis", methods=["POST"])
@secure_error_handler
def analyze_strengths():
    """会話履歴から強みを分析"""
    # 強み分析機能が無効化されている場合
    if not is_strength_analysis_enabled():
        return jsonify({
            "error": "Feature disabled",
            "message": "強み分析機能は現在無効化されています。"
        }), 403
    
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
            
        session_type = data.get("type", "chat")  # chat or scenario
        scenario_id = data.get("scenario_id")
        
        # 会話履歴を取得
        if session_type == "chat":
            history = session.get("chat_history", [])
        elif session_type == "scenario":
            if not scenario_id:
                return jsonify({"error": "シナリオIDが必要です"}), 400
            elif scenario_id == "all":
                # 全シナリオの履歴を結合
                scenario_histories = session.get("scenario_history", {})
                history = []
                for scenario_id, scenario_history in scenario_histories.items():
                    history.extend(scenario_history)
            else:
                history = session.get("scenario_history", {}).get(scenario_id, [])
        else:
            return jsonify({"error": f"不明なセッションタイプ: {session_type}"}), 400
        
        if not history:
            return jsonify({
                "scores": {key: 50 for key in ["empathy", "clarity", "active_listening", 
                          "adaptability", "positivity", "professionalism"]},
                "messages": ["まだ練習履歴がありません。会話を始めてみましょう！"],
                "history": []
            })
        
        # 会話履歴をフォーマット
        formatted_history = format_conversation_history(history)
        
        # 強み分析を実行（シンプルバージョン）
        scores = analyze_user_strengths(formatted_history)
        
        # 使用モデル名（今はシンプル分析なので固定）
        used_model = "simple_analyzer"
        
        # セッションに保存される強み履歴を更新
        if "strength_history" not in session:
            session["strength_history"] = {}
        
        if session_type not in session["strength_history"]:
            session["strength_history"][session_type] = []
        
        # 新しい分析結果を追加
        session["strength_history"][session_type].append({
            "timestamp": datetime.now().isoformat(),
            "scores": scores,
            "practice_count": len(session["strength_history"][session_type]) + 1
        })
        
        # 最大20件まで保持
        if len(session["strength_history"][session_type]) > 20:
            session["strength_history"][session_type] = session["strength_history"][session_type][-20:]
        
        session.modified = True
        
        # 励ましメッセージを生成
        messages = generate_encouragement_messages(
            scores,
            session["strength_history"][session_type][:-1]  # 現在の結果を除く
        )
        
        # パーソナライズされたメッセージを追加（1つ目のメッセージがある場合）
        if messages and len(messages) < 3:
            top_strength = get_top_strengths(scores, 1)[0]
            additional_messages = [
                f"{top_strength['name']}の才能が光っています！この強みを活かしてさらに成長しましょう。",
                f"素晴らしい{top_strength['name']}ですね！次回はさらに磨きをかけていきましょう。",
                f"{top_strength['name']}が{top_strength['score']}点！あなたの強みを自信にして前進しましょう。"
            ]
            import random
            messages.append(random.choice(additional_messages))
        
        return jsonify({
            "scores": scores,
            "messages": messages,
            "history": session["strength_history"][session_type],
            "model_used": used_model
        })
        
    except Exception as e:
        # 外側tryブロックのexceptハンドラ
        print(f"Error in analyze_strengths: {str(e)}")
        return jsonify({
            "error": f"強み分析に失敗しました: {SecurityUtils.get_safe_error_message(e)}"
        }), 500


def update_feedback_with_strength_analysis(feedback_response, session_type, scenario_id=None):
    """
    既存のフィードバックレスポンスに強み分析を追加するヘルパー関数
    """
    try:
        # 会話履歴を取得
        if session_type == "chat":
            history = session.get("chat_history", [])
        else:
            history = session.get("scenario_history", {}).get(scenario_id, [])
        
        if history:
            # 強み分析を実行（シンプルバージョン）
            formatted_history = format_conversation_history(history)
            scores = analyze_user_strengths(formatted_history)
            
            # トップ3の強みを取得
            top_strengths = get_top_strengths(scores, 3)
            
            # フィードバックレスポンスに追加
            feedback_response["strength_analysis"] = {
                "scores": scores,
                "top_strengths": top_strengths
            }
    except Exception as e:
        print(f"Error adding strength analysis to feedback: {str(e)}")
    
    return feedback_response


# ========== APIキー管理 ==========
@app.route("/api/key_status", methods=["GET"])
@secure_error_handler
def get_api_key_status():
    """APIキーの使用状況を取得"""
    # COMPLIANCE FIX: 規約準拠APIマネージャーを使用
    manager = get_compliant_api_manager()
    status = manager.get_status()
    return jsonify(status)


# ========== セッション管理・監視 ==========
@app.route("/api/session/health", methods=["GET"])
@secure_error_handler
def session_health_check():
    """セッションストアの健全性チェック"""
    try:
        if redis_session_manager:
            health = redis_session_manager.health_check()
            connection_info = redis_session_manager.get_connection_info()
            
            return jsonify({
                "status": "healthy" if health['connected'] else "degraded",
                "session_store": "redis" if health['connected'] else "fallback",
                "details": {
                    "redis_connected": health['connected'],
                    "fallback_active": health['fallback_active'],
                    "connection_info": connection_info,
                    "error": health.get('error')
                }
            })
        else:
            return jsonify({
                "status": "healthy",
                "session_store": "filesystem",
                "details": {
                    "redis_connected": False,
                    "fallback_active": False,
                    "session_dir": app.config.get("SESSION_FILE_DIR", "./flask_session")
                }
            })
            
    except Exception as e:
        # 外側tryブロックのexceptハンドラ
        print(f"Error in session_health_check: {str(e)}")
        return jsonify({
            "error": f"セッションヘルスチェックに失敗しました: {SecurityUtils.get_safe_error_message(e)}"
        }), 500


@app.route("/api/session/info", methods=["GET"])
@secure_error_handler
def session_info():
    """現在のセッション情報を取得"""
    try:
        session_data = {
            "session_id": session.get('_id', 'N/A'),
            "session_keys": list(session.keys()),
            "session_type": app.config.get("SESSION_TYPE", "unknown"),
            "permanent": session.permanent,
            "has_chat_history": 'chat_history' in session,
            "has_scenario_history": 'scenario_chat_history' in session,
            "current_scenario": session.get('current_scenario_id'),
            "model_choice": session.get('model_choice', 'N/A')
        }
        
        # セッションサイズの概算
        import sys
        session_size = sys.getsizeof(str(dict(session)))
        session_data["estimated_size_bytes"] = session_size
        
        return jsonify(session_data)
        
    except Exception as e:
        # 外側tryブロックのexceptハンドラ
        print(f"Error in get_session_info: {str(e)}")
        return jsonify({
            "error": f"セッション情報取得に失敗しました: {SecurityUtils.get_safe_error_message(e)}"
        }), 500


@app.route("/api/session/clear", methods=["POST"])
# @CSRFToken.require_csrf  # TODO: CSRF保護を後で有効化
def clear_session_data():
    """セッションデータのクリア"""
    try:
        data = request.json or {}
        clear_type = data.get("type", "all")
        
        if clear_type == "all":
            session.clear()
            message = "全セッションデータをクリアしました"
        elif clear_type == "chat":
            session.pop('chat_history', None)
            message = "チャット履歴をクリアしました"
        elif clear_type == "scenario":
            session.pop('scenario_chat_history', None)
            session.pop('current_scenario_id', None)
            message = "シナリオ履歴をクリアしました"
        elif clear_type == "watch":
            session.pop('watch_history', None)
            message = "観戦履歴をクリアしました"
        else:
            return jsonify({"error": "無効なクリアタイプです"}), 400
        
        return jsonify({
            "status": "success",
            "message": message,
            "cleared_type": clear_type
        })
        
    except Exception as e:
        return jsonify({
            "error": f"セッションクリアエラー: {str(e)}"
        }), 500


# ========== メイン起動 ==========
# ============= CSRFミドルウェアの設定 =============
# 保護が必要なエンドポイントのリスト
CSRF_PROTECTED_ENDPOINTS = [
    '/api/clear_history',
    '/api/chat',
    '/api/scenario_chat',
    '/api/watch/start',
    '/api/watch/next',
    '/api/scenario_feedback',
    '/api/chat_feedback',
    '/api/start_chat',
    '/api/start_scenario',
    '/api/start_watch'
]

@app.before_request
def csrf_middleware():
    """CSRFミドルウェア - 保護されたエンドポイントでCSRF検証を行う"""
    # POSTリクエストかつ保護対象のエンドポイントの場合
    if request.method == 'POST' and request.path in CSRF_PROTECTED_ENDPOINTS:
        try:
            from utils.security import CSRFToken
            
            # トークンの取得（ヘッダーまたはフォームから）
            token = request.headers.get('X-CSRF-Token') or \
                   request.headers.get('X-CSRFToken') or \
                   request.form.get('csrf_token')
            
            # トークンの検証
            if not CSRFToken.validate(token, session):
                # ロギング
                import logging
                logging.getLogger('utils.security').warning(f"CSRF token validation failed for {request.path}")
                
                return jsonify({
                    'error': 'CSRF token validation failed',
                    'code': 'CSRF_TOKEN_INVALID' if token else 'CSRF_TOKEN_MISSING'
                }), 403
        except ImportError:
            # CSRFTokenクラスが存在しない場合はスキップ
            pass

# ============= A/Bテスト用Blueprint登録 =============
try:
    from routes.ab_test_routes import ab_test_bp
    app.register_blueprint(ab_test_bp)
    print("✅ A/Bテストエンドポイントを登録しました (/api/v2/*)")
except ImportError as e:
    print(f"⚠️ A/Bテストエンドポイントは利用できません: {e}")

if __name__ == "__main__":
    # 設定に基づいてサーバーを起動
    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        use_reloader=config.HOT_RELOAD
    )
