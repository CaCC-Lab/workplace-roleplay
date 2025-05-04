from flask import Flask, render_template, request, jsonify, session, stream_with_context
from flask_session import Session
import requests
import os
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from pydantic import SecretStr  # 追加
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import time

# LangChain関連
from langchain_openai import ChatOpenAI  # OpenAI用
from langchain_community.llms.ollama import Ollama  # Ollama用
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from openai import OpenAI as OpenAIClient
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

# 既存のimport文の下に追加
from scenarios import load_scenarios

"""
要件:
1. ローカルLLM (Ollama) とクラウドLLM (OpenAI) を切り替えられる
2. ユーザごとに会話メモリを保持
3. モデル一覧を取得できる (ollamaが動いている前提)
4. Flaskを使ったプロトタイプ（Jinja2テンプレート）
"""

app = Flask(__name__)
# 環境変数からシークレットキーを取得、設定されていない場合はデフォルト値を使用
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_secret_key_here")  # セッション管理用のキー
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ========== 設定値・初期化 ==========
# Ollamaがローカルで起動しているURL
OLLAMA_API_URL = "http://localhost:11434"

# OpenAI APIキー (環境変数から取得)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Gemini APIキー (環境変数から取得)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Warning: GOOGLE_API_KEY is not set")

# LLMの温度やその他パラメータは必要に応じて調整
DEFAULT_TEMPERATURE = 0.7

# デフォルトモデルの設定
DEFAULT_MODEL = "gemini/gemini-2.5-flash-preview-04-17"  # 最新のモデルに更新

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
            raise ValueError("GOOGLE_API_KEY is not set")
            
        # APIキーの形式を検証
        if not GOOGLE_API_KEY.startswith("AI"):
            raise ValueError("Invalid Google API key format. Key should start with 'AI'")
        
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
            raise ValueError("Failed to get response from Gemini API")
            
        print("Gemini model initialized successfully")
        return llm
        
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
                print(f"Fallback also failed: {str(fallback_error)}")
                raise
        
        print(f"Error creating Gemini model: {error_msg}")
        raise

def get_available_openai_models():
    """
    OpenAI APIから利用可能なモデル一覧を取得
    エラー時は基本モデルのリストを返す
    """
    try:
        client = OpenAIClient(api_key=OPENAI_API_KEY)
        models = client.models.list()
        
        chat_models = []
        for model in models:
            if model.id.startswith(("gpt-4", "gpt-3.5")):
                chat_models.append(f"openai/{model.id}")
        
        return sorted(chat_models)  # Geminiモデルは別途追加するため、ここでは追加しない
    except Exception as e:
        print(f"OpenAI models fetch error: {e}")
        return [
            "openai/gpt-4o-mini",
            "openai/gpt-4",
            "openai/gpt-4-turbo-preview",
            "openai/gpt-3.5-turbo"
        ]  # Geminiモデルは別途追加するため、ここでは追加しない

# ========== モデル取得 (ローカル) ==========
def get_available_local_models():
    """
    Ollamaサーバから利用可能なモデル一覧を取得
    失敗した場合はデフォルトの"llama2"のみ返す
    """
    try:
        response = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=3)
        models_info = response.json()
        model_names = [m["name"] for m in models_info.get("models", [])]
        return model_names if model_names else ["llama2"]
    except Exception as e:
        print(f"Ollama models fetch error: {e}")
        return ["llama2"]

# ========== LLM生成ユーティリティ ==========
def create_ollama_llm(model_name: str):
    """
    LangChainのOllama LLMインスタンス生成（新しいクライアントを使用）
    """
    return Ollama(
        model=model_name,
        temperature=DEFAULT_TEMPERATURE,
    )

def create_openai_llm(model_name: str = "gpt-3.5-turbo") -> ChatOpenAI:
    """
    LangChainのOpenAI Chat modelインスタンス生成（更新版）
    """
    # モデル名からopenai/プレフィックスを削除
    if model_name.startswith("openai/"):
        model_name = model_name.replace("openai/", "")
    
    # APIキーをSecretStr型に変換
    api_key = SecretStr(OPENAI_API_KEY) if OPENAI_API_KEY else None
        
    return ChatOpenAI(
        temperature=DEFAULT_TEMPERATURE,
        api_key=api_key,  # SecretStr型で渡す
        model=model_name,
    )

# ========== シナリオ（職場のあなた再現シートを想定したデータ） ==========
# 実際にはデータベースや外部ファイルなどで管理するのがおすすめ
scenarios = load_scenarios()

# ========== Flaskルート ==========
@app.route("/")
def index():
    """トップページ"""
    # 共通関数を使用してモデル情報を取得
    model_info = get_all_available_models()
    available_models = model_info["models"]
    
    return render_template("index.html", models=available_models)

@app.route("/chat")
def chat():
    """
    自由会話ページ
    """
    # モデル一覧の取得を削除
    return render_template("chat.html")

# 新しいユーティリティ関数を追加
def handle_llm_error(error: Exception, fallback_function=None, fallback_args=None, error_prefix="エラーが発生しました"):
    """
    LLM関連のエラーを共通処理するユーティリティ関数
    
    Args:
        error: 発生した例外
        fallback_function: フォールバック時に実行する関数
        fallback_args: フォールバック関数に渡す引数の辞書
        error_prefix: エラーメッセージの接頭辞
        
    Returns:
        (エラーメッセージ, ステータスコード, フォールバック結果, fallback_model)のタプル
    """
    error_str = str(error)
    print(f"LLM error: {error_str}")
    
    # クォータ制限エラーの検出（OpenAIなど）
    if "insufficient_quota" in error_str or "429" in error_str:
        try:
            print("APIクォータ制限を検出。ローカルモデルにフォールバックします。")
            local_models = get_available_local_models()
            
            if local_models and fallback_function:
                fallback_model = local_models[0]  # 最初のローカルモデルを使用
                print(f"Using fallback model: {fallback_model}")
                
                if fallback_args is None:
                    fallback_args = {}
                
                # フォールバック関数に'fallback_model'引数を追加
                fallback_args['fallback_model'] = fallback_model
                
                # フォールバック関数を実行
                result = fallback_function(**fallback_args)
                return None, None, result, fallback_model
            else:
                return "APIクォータ制限に達し、利用可能なローカルモデルもありません。後でもう一度お試しください。", 429, None, None
                
        except Exception as fallback_error:
            print(f"Fallback model error: {str(fallback_error)}")
            return f"すべてのモデルでエラーが発生しました: {str(fallback_error)}", 500, None, None
    else:
        # その他のエラー
        return f"{error_prefix}: {error_str}", 500, None, None

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

def fallback_with_local_model(messages_or_prompt, fallback_model, extract=True):
    """
    ローカルモデルを使用してフォールバック処理を行う
    
    Args:
        messages_or_prompt: メッセージリストまたはプロンプト文字列
        fallback_model: 使用するフォールバックモデル名
        extract: 応答からコンテンツを抽出するかどうか
        
    Returns:
        フォールバックレスポンス
    """
    llm = create_ollama_llm(fallback_model)
    response = llm.invoke(messages_or_prompt)
    
    if extract:
        return extract_content(response)
    return response

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

# チャットエンドポイントを更新して共通関数を使用

@app.route("/api/chat", methods=["POST"])
def handle_chat():
    """
    チャットメッセージの処理
    """
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        message = data.get("message", "")
        model_name = data.get("model", DEFAULT_MODEL)

        # chat_settingsの取得
        chat_settings = session.get("chat_settings", {})
        system_prompt = chat_settings.get("system_prompt", "")

        if not system_prompt:
            return jsonify({"error": "チャットセッションが初期化されていません"}), 400

        try:
            # 会話履歴の取得と更新（共通関数使用）
            initialize_session_history("chat_history")

            # メッセージリストの作成（型を明示的に指定）
            messages: List[BaseMessage] = []
            messages.append(SystemMessage(content=system_prompt))

            # 共通関数を使用して履歴からメッセージを構築
            add_messages_from_history(messages, session["chat_history"])

            # 新しいメッセージを追加
            messages.append(HumanMessage(content=message))

            # 共通関数を使用して応答を生成
            try:
                ai_message = create_model_and_get_response(model_name, messages)
            except Exception as e:
                # エラーハンドリング共通関数を使用
                error_msg, status_code, fallback_result, fallback_model = handle_llm_error(
                    e,
                    fallback_with_local_model,
                    {"messages_or_prompt": messages}
                )
                
                if fallback_result:
                    ai_message = fallback_result
                else:
                    return jsonify({"error": error_msg}), status_code

            # 会話履歴の更新（共通関数使用）
            add_to_session_history("chat_history", {
                "human": message,
                "ai": ai_message
            })

            return jsonify({"response": ai_message})

        except Exception as e:
            print(f"Error in chat: {str(e)}")
            return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500

    except Exception as e:
        print(f"Error in handle_chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
def scenario_chat():
    """
    ロールプレイモード専用のチャットAPI
    """
    try:
        data = request.json
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        user_message = data.get("message", "")
        scenario_id = data.get("scenario_id", "")
        selected_model = data.get("model", DEFAULT_MODEL)
        
        print(f"Received request: message={user_message}, scenario_id={scenario_id}, model={selected_model}")
        
        if not scenario_id or scenario_id not in scenarios:
            return jsonify({"error": "無効なシナリオIDです"}), 400

        scenario_data = scenarios[scenario_id]
        
        # セステムプロンプトを構築
        system_prompt = f"""\
# ロールプレイの基本設定
あなたは{scenario_data["role_info"].split("、")[0].replace("AIは", "")}として振る舞います。

## キャラクター詳細
- 性格: {scenario_data["character_setting"]["personality"]}
- 話し方: {scenario_data["character_setting"]["speaking_style"]}
- 現在の状況: {scenario_data["character_setting"]["situation"]}

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
{scenario_data["description"]}

## 特記事項
- ユーザーの成長を促す反応を心がける
- 極端な否定は避け、建設的な対話を維持
- 必要に応じて適度な困難さを提示
"""
        
        # セッション初期化（共通関数使用）
        initialize_session_history("scenario_history", scenario_id)

        try:
            # 会話履歴の構築
            messages: List[BaseMessage] = []
            messages.append(SystemMessage(content=system_prompt))
            
            # 共通関数を使用して履歴からメッセージを構築
            add_messages_from_history(messages, session["scenario_history"][scenario_id])

            # 新しいメッセージの処理
            if len(session["scenario_history"][scenario_id]) == 0:
                # 初回メッセージの場合
                prompt = f"""\
最初の声掛けとして、{scenario_data["character_setting"]["initial_approach"]}という設定で
話しかけてください。感情や表情も自然に含めて表現してください。
"""
                messages.append(HumanMessage(content=prompt))
            else:
                # 通常の会話の場合
                messages.append(HumanMessage(content=user_message))

            # 共通関数を使用して応答を生成
            try:
                response = create_model_and_get_response(selected_model, messages)
            except Exception as e:
                # エラーハンドリング共通関数を使用
                error_msg, status_code, fallback_result, fallback_model = handle_llm_error(
                    e,
                    fallback_with_local_model,
                    {"messages_or_prompt": messages}
                )
                
                if fallback_result:
                    response = fallback_result
                else:
                    response = f"申し訳ありません。{error_msg}"

            # セッションに履歴を保存（共通関数使用）
            add_to_session_history("scenario_history", {
                "human": user_message if user_message else "[シナリオ開始]",
                "ai": response
            }, scenario_id)

            return jsonify({"response": response})

        except Exception as e:
            print(f"Conversation error: {str(e)}")
            return jsonify({"error": f"会話処理中にエラーが発生しました: {str(e)}"}), 500

    except Exception as e:
        print(f"General error: {str(e)}")
        return jsonify({"error": f"予期せぬエラーが発生しました: {str(e)}"}), 500

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
            "error": f"履歴のクリアに失敗しました: {str(e)}"
        }), 500

@app.route("/api/watch/start", methods=["POST"])
def start_watch():
    """LLM観戦モードの開始"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        model_a = data.get("model_a")
        model_b = data.get("model_b")
        partner_type = data.get("partner_type")
        situation = data.get("situation")
        topic = data.get("topic")

        # セッションの初期化（共通関数使用）
        clear_session_history("watch_history")
        session["watch_settings"] = {
            "model_a": model_a,
            "model_b": model_b,
            "partner_type": partner_type,
            "situation": situation,
            "topic": topic,
            "current_speaker": "A"
        }
        session.modified = True

        try:
            # generate_initial_messageに必要なパラメータ
            initial_message_args = {
                "partner_type": partner_type,
                "situation": situation,
                "topic": topic
            }
            
            # 共通関数を使用して応答を生成
            try:
                # まずLLMを初期化
                llm = initialize_llm(model_a)
                # 初期メッセージを生成
                initial_message = generate_initial_message(llm, **initial_message_args)
            except Exception as e:
                # エラーハンドリング共通関数を使用
                error_msg, status_code, fallback_result, fallback_model = handle_llm_error(
                    e,
                    # フォールバック関数として、ローカルモデルでの初期メッセージ生成を指定
                    lambda fallback_model, **kwargs: generate_initial_message(
                        initialize_llm(fallback_model), **kwargs
                    ),
                    # 必要なパラメータを渡す
                    initial_message_args
                )
                
                if fallback_result:
                    initial_message = fallback_result
                    # フォールバックモデルを保存
                    session["watch_settings"]["model_a"] = fallback_model
                    session["watch_settings"]["model_b"] = fallback_model
                    session.modified = True
                    
                    # 正常応答でフォールバック通知付き
                    return jsonify({
                        "message": f"モデルA(代替): {initial_message}", 
                        "notice": "OpenAIのクォータ制限により、ローカルモデルを使用しています。"
                    })
                else:
                    return jsonify({"error": error_msg}), status_code
            
            # 履歴に保存（共通関数使用）
            add_to_session_history("watch_history", {
                "speaker": "A",
                "message": initial_message
            })

            return jsonify({"message": f"モデルA: {initial_message}"})

        except Exception as e:
            print(f"Error in watch initialization: {str(e)}")
            return jsonify({"error": f"観戦の初期化に失敗しました: {str(e)}"}), 500

    except Exception as e:
        print(f"Error in start_watch: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/watch/next", methods=["POST"])
def next_watch_message():
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

        try:
            # 共通関数を使用して応答を生成
            try:
                # まずLLMを初期化
                llm = initialize_llm(model)
                # 次のメッセージを生成
                next_message = generate_next_message(llm, history)
            except Exception as e:
                # エラーハンドリング共通関数を使用
                error_msg, status_code, fallback_result, fallback_model = handle_llm_error(
                    e,
                    # フォールバック関数として、ローカルモデルでの次のメッセージ生成を指定
                    lambda fallback_model, **kwargs: generate_next_message(
                        initialize_llm(fallback_model), history
                    ),
                    {}  # 追加パラメータなし
                )
                
                if fallback_result:
                    next_message = fallback_result
                    # フォールバックモデルを保存（今後の会話用）
                    if next_speaker == "B":
                        settings["model_b"] = fallback_model
                    else:
                        settings["model_a"] = fallback_model
                    
                    # 正常応答でフォールバック通知付き
                    return jsonify({
                        "message": f"モデル{next_speaker}(代替): {next_message}", 
                        "notice": "OpenAIのクォータ制限により、ローカルモデルを使用しています。"
                    })
                else:
                    return jsonify({"error": error_msg}), status_code
            
            # 履歴に保存
            history.append({
                "speaker": next_speaker,
                "message": next_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # 話者を更新
            settings["current_speaker"] = next_speaker
            session.modified = True

            return jsonify({"message": f"モデル{next_speaker}: {next_message}"})

        except Exception as e:
            print(f"Error generating next message: {str(e)}")
            return jsonify({"error": f"メッセージの生成に失敗しました: {str(e)}"}), 500

    except Exception as e:
        print(f"Error in next_watch_message: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_next_message(llm, history):
    """観戦モードの次のメッセージを生成"""
    # 会話履歴をフォーマット
    formatted_history = []
    for entry in history:
        formatted_history.append(f"モデル{entry['speaker']}: {entry['message']}")
    
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
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="以下の会話履歴に基づいて、次の発言をしてください：\n\n" + "\n".join(formatted_history))
    ]
    
    response = llm.invoke(messages)
    return extract_content(response)

@app.route("/api/get_assist", methods=["POST"])
def get_assist():
    """AIアシストの提案を取得するエンドポイント"""
    try:
        data = request.get_json()
        scenario_id = data.get("scenario_id")
        current_context = data.get("current_context", "")

        if not scenario_id:
            return jsonify({"error": "シナリオIDが必要です"}), 400

        # シナリオ情報を取得
        scenario = scenarios.get(scenario_id)
        if not scenario:
            return jsonify({"error": "シナリオが見つかりません"}), 404

        # AIアシストのプロンプトを作成
        assist_prompt = f"""
現在のシナリオ: {scenario['title']}
状況: {scenario['description']}
学習ポイント: {', '.join(scenario['learning_points'])}

現在の会話:
{current_context}

上記の状況で、適切な返答のヒントを1-2文で簡潔に提案してください。
"""

        # 選択されているモデルを取得
        selected_model = session.get("selected_model", DEFAULT_MODEL)
        
        try:
            # 共通関数を使用して応答を生成
            suggestion = create_model_and_get_response(selected_model, assist_prompt)
            return jsonify({"suggestion": suggestion})
            
        except Exception as e:
            # エラーハンドリング共通関数を使用
            error_msg, status_code, fallback_result, fallback_model = handle_llm_error(
                e,
                fallback_with_local_model,
                {"messages_or_prompt": assist_prompt}
            )
            
            if fallback_result:
                return jsonify({
                    "suggestion": fallback_result, 
                    "fallback": True
                })
            else:
                return jsonify({"error": error_msg}), status_code

    except Exception as e:
        print(f"AIアシストエラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
        if model_name.startswith('openai/'):
            try:
                return create_openai_llm(model_name.replace('openai/', ''))
            except Exception as openai_error:
                # OpenAIのクォータ制限エラーをチェック
                error_str = str(openai_error)
                if "insufficient_quota" in error_str or "429" in error_str:
                    print(f"OpenAI quota limit reached: {error_str}")
                    print("Falling back to local model...")
                    # ローカルモデルにフォールバック
                    local_models = get_available_local_models()
                    if local_models:
                        fallback_model = local_models[0]
                        print(f"Using fallback model: {fallback_model}")
                        return create_ollama_llm(fallback_model)
                    else:
                        raise ValueError("OpenAIのクォータ制限に達し、利用可能なローカルモデルもありません")
                else:
                    # その他のエラーはそのまま再発生
                    raise
        elif model_name.startswith('gemini/'):
            return create_gemini_llm(model_name.replace('gemini/', ''))
        else:
            return create_ollama_llm(model_name)
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
        # ローカルモデル取得
        local_models = get_available_local_models()
        
        # OpenAIモデル取得
        openai_models = get_available_openai_models()
        
        # Geminiモデル取得
        gemini_models = get_available_gemini_models()
        
        # すべてのモデルを結合
        all_models = (
            openai_models +  # OpenAIモデル（"openai/"プレフィックス付き）
            gemini_models +  # Geminiモデル（"gemini/"プレフィックス付き）
            local_models     # ローカルモデル（プレフィックスなし）
        )
        
        return {
            "models": all_models,
            "categories": {
                "openai": openai_models,
                "gemini": gemini_models,
                "local": local_models
            }
        }
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        # 基本的なモデルリストでフォールバック
        basic_models = [
            "openai/gpt-4o-mini",
            "openai/gpt-3.5-turbo",
            "gemini/gemini-1.5-flash",
            "llama2"
        ]
        return {
            "models": basic_models,
            "categories": {
                "openai": ["openai/gpt-4o-mini", "openai/gpt-3.5-turbo"],
                "gemini": ["gemini/gemini-1.5-flash"],
                "local": ["llama2"]
            }
        }

# 削除されたルートと関数を復元

@app.route("/api/models", methods=["GET"])
def api_models():
    """
    利用可能なすべてのモデル一覧を返す
    - ローカルLLM (Ollama)
    - OpenAI
    - Google Gemini
    """
    try:
        # 共通関数を使用してモデル情報を取得
        model_info = get_all_available_models()
        return jsonify(model_info)
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
    
    return render_template(
        "scenario.html",
        scenario_id=scenario_id,
        scenario_title=scenarios[scenario_id]["title"],
        scenario_desc=scenarios[scenario_id]["description"],
        scenario=scenarios[scenario_id]
    )

# モデル試行パターンを統一するためのヘルパー関数
def try_multiple_models_for_prompt(prompt: str) -> Tuple[str, str, Optional[str]]:
    """
    複数のモデルを順に試行してプロンプトに対する応答を取得するヘルパー関数
    
    Args:
        prompt: LLMに与えるプロンプト
        
    Returns:
        (応答内容, 使用したモデル名, エラーメッセージ)のタプル。
        すべてのモデルが失敗した場合はエラーメッセージを返す。
    """
    content = None
    used_model = None
    error_msg = None
    
    # 1. まずGeminiを試行
    try:
        # 利用可能なGeminiモデルを確認
        gemini_models = get_available_gemini_models()
        if gemini_models:
            # 最初に見つかったGeminiモデルを使用
            model_name = gemini_models[0]
            print(f"Attempting to use Gemini model: {model_name}")
            content = create_model_and_get_response(model_name, prompt)
            used_model = model_name
            print(f"Successfully generated content using {used_model}")
            return content, used_model, None
        else:
            print("No Gemini models available")
    except Exception as gemini_error:
        print(f"Gemini model error: {str(gemini_error)}")
        error_msg = str(gemini_error)
    
    # 2. Geminiが失敗したらOpenAIを試行
    try:
        print("Falling back to OpenAI")
        model_name = "openai/gpt-3.5-turbo"
        content = create_model_and_get_response(model_name, prompt)
        used_model = model_name
        print(f"Successfully generated content using {used_model}")
        return content, used_model, None
    except Exception as openai_error:
        print(f"OpenAI model error: {str(openai_error)}")
        
        # クォータ制限エラーをチェック
        if "insufficient_quota" in str(openai_error) or "429" in str(openai_error):
            if not error_msg:
                error_msg = f"APIクォータ制限: {str(openai_error)}"
        else:
            if not error_msg:
                error_msg = f"OpenAI Error: {str(openai_error)}"
    
    # 3. OpenAIも失敗した場合、ローカルモデルを試行
    try:
        print("Falling back to local Ollama model")
        local_models = get_available_local_models()
        if local_models:
            model_name = local_models[0]  # ローカルモデル名の変数名を修正
            content = fallback_with_local_model(prompt, model_name)
            used_model = model_name
            print(f"Successfully generated content using local model {used_model}")
            return content, used_model, None
        else:
            print("No local models available")
            if not error_msg:
                error_msg = "No models available for inference"
    except Exception as local_error:
        print(f"Local model error: {str(local_error)}")
        if not error_msg:
            error_msg = f"Local model error: {str(local_error)}"
    
    # すべてのモデルが失敗した場合
    return None, None, error_msg or "Unknown error occurred with all models"

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
def get_scenario_feedback():
    """シナリオの会話履歴に基づくフィードバックを生成"""
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    scenario_id = data.get("scenario_id")
    if not scenario_id or scenario_id not in scenarios:
        return jsonify({"error": "無効なシナリオIDです"}), 400

    # 会話履歴を取得
    if "scenario_history" not in session or scenario_id not in session["scenario_history"]:
        return jsonify({"error": "会話履歴が見つかりません"}), 404

    history = session["scenario_history"][scenario_id]
    scenario_data = scenarios[scenario_id]

    # フィードバック生成用のプロンプト
    feedback_prompt = f"""\
# フィードバック生成の指示
あなたは職場コミュニケーションの専門家として、以下のロールプレイでのユーザーの対応を評価し、具体的で実践的なフィードバックを提供してください。

## シナリオ概要
{scenario_data["description"]}

## ユーザーの立場
{scenario_data["role_info"].split("、")[1]}

## 会話履歴の分析
{format_conversation_history(history)}

## 評価の観点
{', '.join(scenario_data["feedback_points"])}

## 学習目標
{', '.join(scenario_data["learning_points"])}

# フィードバック形式

## 1. 全体評価（100点満点）
- 点数と、その理由を簡潔に説明

## 2. 良かった点（具体例を含めて）
- コミュニケーションの効果的だった部分
- 特に評価できる対応や姿勢
- なぜそれが良かったのかの説明

## 3. 改善のヒント
- より効果的な表現方法の具体例
- 状況に応じた対応の選択肢
- 実際の言い回しの例示

## 4. 実践アドバイス
1. 明日から使える具体的なテクニック
2. 類似シーンでの応用ポイント
3. 次回のロールプレイでの注目ポイント

## 5. モチベーション向上のメッセージ
- 成長が見られた点への励まし
- 次のステップへの期待
"""

    try:
        # 新しいヘルパー関数を使用してモデルを試行
        feedback_content, used_model, error_msg = try_multiple_models_for_prompt(feedback_prompt)
        
        if feedback_content:
            return jsonify({
                "feedback": feedback_content,
                "scenario": scenario_data["title"],
                "model_used": used_model,
            })
        else:
            # すべてのモデルが失敗した場合
            return jsonify({
                "error": f"フィードバックの生成に失敗しました: {error_msg}",
                "attempted_models": "Gemini, OpenAI, Local"
            }), 500

    except Exception as e:
        print(f"Feedback generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"フィードバックの生成中にエラーが発生しました: {str(e)}"
        }), 500

# 雑談フィードバック関数も更新
@app.route("/api/chat_feedback", methods=["POST"])
def get_chat_feedback():
    """雑談練習のフィードバックを生成（ユーザーの発言に焦点を当てる）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        # 会話履歴の取得
        if "chat_history" not in session:
            return jsonify({"error": "会話履歴が見つかりません"}), 404

        # フィードバック用ログ出力
        print("Chat history:", session["chat_history"])
        print("Formatted history:", format_conversation_history(session["chat_history"]))

        # フィードバック生成用のプロンプト
        feedback_prompt = f"""# フィードバック生成の指示
あなたは雑談スキル向上のための専門コーチです。以下のユーザーの発言を分析し、具体的で実践的なフィードバックを提供してください。

## 会話の設定
- 相手: {get_partner_description(data.get("partner_type"))}
- 状況: {get_situation_description(data.get("situation"))}
- 話題: {get_topic_description(data.get("topic"))}

## ユーザーの発言履歴
{format_conversation_history(session["chat_history"])}

# フィードバック形式
## 1. 全体評価（100点満点）
- 雑談スキルの点数
- 評価理由（特に良かった点、改善点を簡潔に）

## 2. 発言の分析
- 適切な言葉遣いができている部分
- 相手との関係性に配慮できている表現
- 会話の流れを作れている箇所

## 3. 改善のヒント
- より自然な表現例
- 話題の広げ方の具体例
- 相手の興味を引き出す質問の仕方

## 4. 実践アドバイス
1. 即実践できる会話テクニック
2. 状況に応じた話題選びのコツ
3. 適切な距離感の保ち方

## 5. 今後のステップアップ
- 次回挑戦してほしい会話スキル
- 伸ばせそうな強みとその活かし方
"""

        # 新しいヘルパー関数を使用してモデルを試行
        feedback_content, used_model, error_msg = try_multiple_models_for_prompt(feedback_prompt)
        
        if feedback_content:
            return jsonify({
                "feedback": feedback_content,
                "model_used": used_model,
                "status": "success"
            })
        else:
            # すべてのモデルが失敗した場合
            return jsonify({
                "error": f"フィードバックの生成に失敗しました: {error_msg}",
                "attempted_models": "Gemini, OpenAI, Local",
                "status": "error"
            }), 500

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
- 相手: {get_partner_description(partner_type)}
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
    # 共通関数を使用してモデル情報を取得
    model_info = get_all_available_models()
    
    # カテゴリー別のモデル情報を準備
    models = {
        "openai": model_info["categories"]["openai"],
        "gemini": model_info["categories"]["gemini"],
        "local": model_info["categories"]["local"]
    }
    
    return render_template(
        "watch.html",
        models=models
    )

# 学習履歴を表示するルートを追加
@app.route("/journal")
def view_journal():
    """学習履歴ページ"""
    # 履歴データを取得
    scenario_history = {}
    
    # セッションから各シナリオの履歴を取得
    if "scenario_history" in session:
        for scenario_id, history in session["scenario_history"].items():
            if scenario_id in scenarios and history:
                scenario_history[scenario_id] = {
                    "title": scenarios[scenario_id]["title"],
                    "last_session": history[-1]["timestamp"] if history else None,
                    "sessions_count": len(history) // 2,  # 往復の会話数をカウント
                    "feedback": session.get("scenario_feedback", {}).get(scenario_id)
                }
    
    # 雑談履歴の取得
    chat_history = []
    if "chat_history" in session:
        chat_history = session["chat_history"]
    
    return render_template(
        "journal.html",
        scenario_history=scenario_history,
        chat_history=chat_history
    )

# 雑談練習開始用のエンドポイントを追加
@app.route("/api/start_chat", methods=["POST"])
def start_chat():
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
            # エラーハンドリング共通関数を使用
            error_msg, status_code, fallback_result, fallback_model = handle_llm_error(
                e,
                fallback_with_local_model,
                {"messages_or_prompt": first_prompt}
            )
            
            if fallback_result:
                # 履歴に保存
                add_to_session_history("chat_history", {
                    "human": "[雑談開始]",
                    "ai": fallback_result
                })
                
                # フォールバックモデルを保存
                session["chat_settings"]["model"] = fallback_model
                session.modified = True
                
                return jsonify({"response": fallback_result, "notice": "フォールバックモデルを使用しています"})
            else:
                return jsonify({"error": error_msg}), status_code
                
    except Exception as e:
        print(f"Error in start_chat: {str(e)}")
        return jsonify({"error": f"雑談の開始に失敗しました: {str(e)}"}), 500

# ========== メイン起動 ==========
if __name__ == "__main__":
    # デバッグモードで実行（本番環境では debug=False にしてください）
    app.run(debug=True, host="0.0.0.0", port=5000)
