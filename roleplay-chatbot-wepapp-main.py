"""
依存パッケージ:
- Flask
- Flask-Session
- requests
- langchain
- langchain-community
- google-generativeai>=0.3.0

インストール方法:
pip install -r requirements.txt
"""

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
app.secret_key = "your_secret_key_here"  # セッション管理用のキー(本番は安全に管理を)
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
DEFAULT_MODEL = "openai/gpt-4o-mini"

# Gemini APIの初期化
try:
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Gemini API initialization error: {e}")

def get_available_gemini_models():
    """
    利用可能なGeminiモデルのリストを返す
    """
    try:
        # Gemini APIの設定を確認
        if not GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY is not set")
            return []
            
        # 利用可能なモデルを取得
        models = genai.list_models()
        
        # Geminiモデルをフィルタリング
        gemini_models = []
        for model in models:
            if "gemini" in model.name.lower():
                # モデル名を整形（gemini/プレフィックスを追加）
                model_name = f"gemini/{model.name.split('/')[-1]}"
                gemini_models.append(model_name)
        
        print(f"Available Gemini models: {gemini_models}")
        return gemini_models
        
    except Exception as e:
        print(f"Error fetching Gemini models: {str(e)}")
        # エラー時はデフォルトのモデルリストを返す
        return [
            "gemini/gemini-pro",
            "gemini/gemini-pro-vision"
        ]

def create_gemini_llm(model_name: str = "gemini-pro"):
    """
    LangChainのGemini Chat modelインスタンス生成
    """
    try:
        # モデル名からgemini/プレフィックスを削除
        if model_name.startswith("gemini/"):
            model_name = model_name.replace("gemini/", "")
        
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
        print(f"Error creating Gemini model: {str(e)}")
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
        
        return sorted(chat_models) + get_available_gemini_models()  # Geminiモデルも追加
    except Exception as e:
        print(f"OpenAI models fetch error: {e}")
        return [
            "openai/gpt-4o-mini",
            "openai/gpt-4",
            "openai/gpt-4-turbo-preview",
            "openai/gpt-3.5-turbo"
        ] + get_available_gemini_models()  # Geminiモデルも追加

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
    # 利用可能なモデルを取得
    openai_models = get_available_openai_models()
    local_models = get_available_local_models()
    
    # OpenAIモデルとローカルモデルを結合
    available_models = openai_models + local_models
    
    return render_template("index.html", models=available_models)

@app.route("/chat")
def chat():
    """
    自由会話ページ
    """
    # モデル一覧の取得を削除
    return render_template("chat.html")

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
            # モデルの初期化
            if model_name.startswith('openai/'):
                llm = create_openai_llm(model_name)
            elif model_name.startswith('gemini/'):
                llm = create_gemini_llm(model_name)
            else:
                llm = create_ollama_llm(model_name)

            # 会話履歴の取得と更新
            if "chat_history" not in session:
                session["chat_history"] = []

            # メッセージリストの作成（型を明示的に指定）
            messages: List[BaseMessage] = []
            messages.append(SystemMessage(content=system_prompt))

            # 直近の会話履歴を追加（トークン数削減のため最新5件のみ）
            recent_history = session["chat_history"][-5:] if session["chat_history"] else []
            for entry in recent_history:
                if entry.get("human"):
                    messages.append(HumanMessage(content=entry["human"]))
                if entry.get("ai"):
                    messages.append(AIMessage(content=entry["ai"]))

            # 新しいメッセージを追加
            messages.append(HumanMessage(content=message))

            # 応答の生成
            response = llm.invoke(messages)
            ai_message = extract_content(response)

            # 会話履歴の更新
            session["chat_history"].append({
                "human": message,
                "ai": ai_message,
                "timestamp": datetime.now().isoformat()
            })
            session.modified = True

            return jsonify({"response": ai_message})

        except Exception as e:
            print(f"Error in chat: {str(e)}")
            return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500

    except Exception as e:
        print(f"Error in handle_chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/models", methods=["GET"])
def api_models():
    """
    利用可能なすべてのモデル一覧を返す
    - ローカルLLM (Ollama)
    - OpenAI
    - Google Gemini
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
        
        return jsonify({
            "models": all_models,
            "categories": {
                "openai": openai_models,
                "gemini": gemini_models,
                "local": local_models
            }
        })
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
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
            # 雑談モードの履歴クリア
            if "chat_history" in session:
                session["chat_history"] = []
                session.modified = True
            if "chat_settings" in session:
                session.pop("chat_settings", None)
                session.modified = True
        else:
            # シナリオモードの履歴クリア
            selected_model = request.json.get("model", "llama2")
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

# シナリオ一覧を表示するページ
@app.route("/scenarios")
def list_scenarios():
    """シナリオ一覧ページ"""
    # 利用可能なモデルを取得
    openai_models = get_available_openai_models()
    local_models = get_available_local_models()
    
    # OpenAIモデルとローカルモデルを結合
    available_models = openai_models + local_models
    
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
    
    # シナリオ履歴の初期化（履歴クリアは削除）
    if "scenario_history" not in session:
        session["scenario_history"] = {}
    
    return render_template(
        "scenario.html",
        scenario_id=scenario_id,
        scenario_title=scenarios[scenario_id]["title"],
        scenario_desc=scenarios[scenario_id]["description"],
        scenario=scenarios[scenario_id]
    )

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
        
        # セッション初期化
        if "scenario_history" not in session:
            session["scenario_history"] = {}
        
        if scenario_id not in session["scenario_history"]:
            session["scenario_history"][scenario_id] = []

        # モデルの初期化
        try:
            if selected_model.startswith('openai/'):
                openai_model_name = selected_model.split("/")[1]
                llm = create_openai_llm(model_name=openai_model_name)
            elif selected_model.startswith('gemini/'):
                openai_model_name = selected_model.split("/")[1]
                llm = create_gemini_llm(model_name=openai_model_name)
            else:
                available_models = get_available_local_models()
                if selected_model not in available_models:
                    return jsonify({
                        "error": f"モデル '{selected_model}' が見つかりません。"
                    }), 404
                llm = create_ollama_llm(selected_model)
        except Exception as e:
            print(f"Model initialization error: {str(e)}")
            return jsonify({"error": f"モデルの初期化に失敗しました: {str(e)}"}), 500

        try:
            # 会話履歴の構築
            messages: List[BaseMessage] = []
            messages.append(SystemMessage(content=system_prompt))
            
            # 過去の会話履歴を追加
            for entry in session["scenario_history"][scenario_id]:
                if entry["human"]:
                    messages.append(HumanMessage(content=entry["human"]))
                if entry["ai"]:
                    messages.append(AIMessage(content=entry["ai"]))

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

            # レスポンスの生成と処理
            try:
                ai_message = llm.invoke(messages)
                if isinstance(ai_message, AIMessage):
                    response = ai_message.content
                elif isinstance(ai_message, str):
                    response = ai_message  # 文字列の場合はそのまま使用
                else:
                    response = "不明な応答形式です。"
            except Exception as e:
                print(f"Response processing error: {str(e)}")
                response = "申し訳ありません。応答の処理中にエラーが発生しました。"

            # セッションに履歴を保存
            session["scenario_history"][scenario_id].append({
                "human": user_message if user_message else "[シナリオ開始]",
                "ai": response,
                "timestamp": datetime.now().isoformat()
            })
            session.modified = True

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

        # シナリオ履歴の初期化
        if "scenario_history" not in session:
            session["scenario_history"] = {}

        # このシナリオの履歴をクリア
        session["scenario_history"][scenario_id] = []
        session.modified = True

        return jsonify({
            "status": "success",
            "message": "シナリオ履歴がクリアされました"
        })

    except Exception as e:
        print(f"Error clearing scenario history: {str(e)}")
        return jsonify({
            "error": f"履歴のクリアに失敗しました: {str(e)}"
        }), 500

@app.route("/api/scenario_feedback", methods=["POST"])
def get_scenario_feedback():
    """シナリオの会話履歴に基づくフィードバックを生成"""
    data = request.json
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
        # フィードバック用のモデルを選択（Geminiを優先）
        try:
            llm = create_gemini_llm("gemini-pro")  # Geminiモデルを使用
            print("Using Gemini model for feedback")
        except Exception as gemini_error:
            print(f"Gemini model error: {str(gemini_error)}, falling back to OpenAI")
            llm = create_openai_llm("gpt-3.5-turbo")  # フォールバック

        # フィードバックの生成
        feedback = llm.invoke(feedback_prompt)
        
        # レスポンスの処理
        if isinstance(feedback, (str, AIMessage)):
            feedback_content = feedback.content if isinstance(feedback, AIMessage) else feedback
        else:
            raise ValueError("Unexpected feedback format")

        return jsonify({
            "feedback": feedback_content,
            "scenario": scenario_data["title"]
        })

    except Exception as e:
        print(f"Feedback generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"フィードバックの生成中にエラーが発生しました: {str(e)}"
        }), 500

def format_conversation_history(history):
    """会話履歴を読みやすい形式にフォーマット（ユーザーの発言のみ）"""
    formatted = []
    for entry in history:
        # ユーザーの発言のみを含める
        if entry.get("human"):
            formatted.append(f"ユーザー: {entry['human']}")
    return "\n".join(formatted)

@app.route("/journal")
def view_journal():
    """
    学習履歴を表示するページ
    """
    # セッションから会話履歴を取得
    scenario_history = session.get("scenario_history", {})
    
    # 履歴データを整形
    journal_entries = []
    for scenario_id, history in scenario_history.items():
        if scenario_id in scenarios:
            entry = {
                "scenario_title": scenarios[scenario_id]["title"],
                "scenario_id": scenario_id,
                "conversations": history,
                "last_practice": history[-1]["timestamp"] if history else None
            }
            journal_entries.append(entry)
    
    return render_template("journal.html", 
                         entries=journal_entries,
                         scenarios=scenarios)

@app.template_filter('datetime')
def format_datetime(value):
    """ISOフォーマットの日時文字列を読みやすい形式に変換"""
    if not value:
        return "未実施"
    dt = datetime.fromisoformat(value)
    return dt.strftime('%Y年%m月%d日 %H:%M')

# 新しいルートを追加
@app.route("/watch")
def watch_mode():
    """
    LLM同士の観戦モードページ
    """
    # 利用可能なモデルを取得
    openai_models = get_available_openai_models()
    local_models = get_available_local_models()
    available_models = openai_models + local_models
    
    return render_template(
        "watch.html", 
        models=available_models,
        scenarios=scenarios
    )

@app.route("/api/watch_conversation", methods=["POST"])
def watch_conversation():
    """従来のPOSTリクエスト用のエンドポイント（互換性のため残す）"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    return jsonify({"message": "Please use the streaming endpoint"}), 200

@app.route("/api/watch_conversation/stream")
def watch_conversation_stream():
    """2つのLLM間の会話を生成するAPI"""
    # クエリパラメータから値を取得
    scenario_id = request.args.get("scenario_id")
    max_turns = min(int(request.args.get("max_turns", 5)), 10)

    def generate():
        try:
            if not scenario_id:
                yield "data: " + json.dumps({"error": "必要なパラメータが不足しています"}) + "\n\n"
                return

            if scenario_id not in scenarios:
                yield "data: " + json.dumps({"error": "無効なシナリオIDです"}) + "\n\n"
                return

            current_model = session.get("selected_model", DEFAULT_MODEL)
            
            try:
                llm1 = initialize_llm(current_model)
                llm2 = initialize_llm(current_model)
            except Exception as e:
                yield "data: " + json.dumps({"error": f"LLMの初期化に失敗しました: {str(e)}"}) + "\n\n"
                return

            scenario_data = scenarios[scenario_id]
            system_prompt1 = create_system_prompt(scenario_data, "role1")
            system_prompt2 = create_system_prompt(scenario_data, "role2")
            conversation = []

            # 最初の発言を生成
            try:
                initial_message = generate_response(llm1, system_prompt1, [], scenario_data["character_setting"]["initial_approach"])
                if initial_message:
                    message = {
                        "speaker": "llm1",
                        "model": current_model,
                        "message": initial_message,
                        "timestamp": datetime.now().isoformat()
                    }
                    conversation.append(message)
                    yield "data: " + json.dumps({"type": "message", "data": message}) + "\n\n"
                    time.sleep(1)  # 自然な間を作る
            except Exception as e:
                yield "data: " + json.dumps({"error": f"初期メッセージの生成に失敗: {str(e)}"}) + "\n\n"
                return

            # 交互に会話を生成
            for turn in range(max_turns - 1):
                try:
                    # LLM2の応答
                    llm2_response = generate_response(llm2, system_prompt2, conversation, None)
                    if llm2_response:
                        message = {
                            "speaker": "llm2",
                            "model": current_model,
                            "message": llm2_response,
                            "timestamp": datetime.now().isoformat()
                        }
                        conversation.append(message)
                        yield "data: " + json.dumps({"type": "message", "data": message}) + "\n\n"
                        time.sleep(1)  # 自然な間を作る

                    # LLM1の応答
                    llm1_response = generate_response(llm1, system_prompt1, conversation, None)
                    if llm1_response:
                        message = {
                            "speaker": "llm1",
                            "model": current_model,
                            "message": llm1_response,
                            "timestamp": datetime.now().isoformat()
                        }
                        conversation.append(message)
                        yield "data: " + json.dumps({"type": "message", "data": message}) + "\n\n"
                        time.sleep(1)  # 自然な間を作る

                except Exception as e:
                    print(f"Error in conversation turn {turn}: {str(e)}")
                    break

            # 会話終了を通知
            yield "data: " + json.dumps({"type": "complete"}) + "\n\n"

        except Exception as e:
            print(f"Error in watch_conversation: {str(e)}")
            yield "data: " + json.dumps({"error": str(e)}) + "\n\n"

    return app.response_class(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

def initialize_llm(model_name: str):
    """モデル名に基づいて適切なLLMを初期化"""
    if model_name.startswith("openai/"):
        return create_openai_llm(model_name)
    elif model_name.startswith("gemini/"):
        return create_gemini_llm(model_name)
    else:
        return create_ollama_llm(model_name)

def create_system_prompt(scenario_data: Dict[str, Any], role: str) -> str:
    """役割に応じたシステムプロンプトを生成"""
    base_prompt = f"""\
# ロールプレイの基本設定
あなたは{'上司' if role == 'role1' else '部下'}として振る舞います。
以下の設定に従って、一貫した役割を演じてください。

## キャラクター詳細
- 性格: {scenario_data["character_setting"]["personality"]}
- 話し方: {scenario_data["character_setting"]["speaking_style"]}
- 現在の状況: {scenario_data["character_setting"]["situation"]}

## 演技の指針
1. 一貫性：設定された役柄を終始一貫して演じ続けること
2. 自然さ：指定された話し方を守りながら、不自然にならないよう注意
3. 感情表現：表情や態度も含めて表現すること
4. 会話の自然な展開を心がけること

## 重要な制約事項
1. 必ず1回の応答で完結した返答をすること
2. メタ的な説明や解説は行わないこと
3. システムエラーについて言及しないこと
4. 空の応答を返さないこと
5. 自分の発言を訂正したり、謝罪したりしないこと
6. 同じ応答を繰り返さないこと
7. 相手の発言内容に対して具体的に応答すること
8. 相手の発言を注意深く聞き、適切に応答すること

## {'部下' if role == 'role2' else '上司'}としての応答指針
{'''
1. 指示内容を具体的に復唱して確認する
2. 不明点があれば具体的に質問する
3. 実行可能な時間を明確に伝える
4. 必要な情報を漏れなく確認する
5. 理解したことを明確に伝える
6. 相手が情報を提供したら、その情報を活用して応答する
7. 相手がイライラしている場合は、落ち着いて対応する
8. 同じ質問を繰り返さない
''' if role == 'role2' else '''
1. 部下に対して明確な指示を出す
2. 質問には具体的に答える
3. 締め切りを明確に伝える
4. 必要な情報を提供する
5. 部下の理解度を確認する
'''}

## 応答例
上司:「この資料、コピーしておいて」
部下:（資料を確認しながら）「はい、承知いたしました。何部必要でしょうか？また、両面印刷でよろしいでしょうか？」
上司:「20部必要で、両面でお願い」
部下:（メモを取りながら）「承知いたしました。20部、両面印刷で準備いたします。締め切りはいつまでにしましょうか？」

## 現在の文脈
{scenario_data["description"]}

## 応答形式
- 感情や仕草は（）内に記述
- 台詞は「」で囲む
- 1回の応答は3行程度まで
"""
    return base_prompt

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

def generate_response(llm, system_prompt: str, conversation: List[Dict], initial_message: Optional[str] = None) -> str:
    """会話履歴を考慮してレスポンスを生成"""
    try:
        # メッセージリストの作成（1回だけ）
        messages: List[BaseMessage] = []
        messages.append(SystemMessage(content=system_prompt))
        
        # 直近2つの会話のみを使用（履歴を減らしてトークン数を削減）
        recent_conversations = conversation[-2:] if len(conversation) > 2 else conversation
        
        # 会話履歴を追加
        for entry in recent_conversations:
            content = entry["message"]
            if entry["speaker"] == "llm2":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        
        if initial_message:
            messages.append(HumanMessage(content=f"以下の言葉で会話を開始してください：{initial_message}"))
        
        # リトライ回数を2回に制限
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # リトライ間隔を設定（429エラー対策）
                if attempt > 0:
                    time.sleep(2)  # 2秒待機
                
                # LLMに応答を生成させる
                raw_response = llm.invoke(messages)
                content = extract_content(raw_response)
                
                # 応答の検証
                if content and len(content.strip()) > 0:
                    if ('（' in content and '）' in content) and ('「' in content and '」' in content):
                        return content
                
                # 無効な応答の場合、プロンプトを簡潔に強化
                if attempt < max_retries - 1:
                    messages[0] = SystemMessage(content=system_prompt + "\n\n重要: 感情表現（）と発言「」を含めてください。")
                    
            except Exception as retry_error:
                print(f"Retry error (attempt {attempt + 1}): {str(retry_error)}")
                if "429" in str(retry_error):
                    # クォータ制限に達した場合は長めに待機
                    time.sleep(5)
                continue
        
        # 最後の試行でも失敗した場合は、最小限のメッセージで1回だけ試行
        try:
            minimal_messages = [
                SystemMessage(content="あなたは会話の参加者です。感情表現（）と発言「」を含めて応答してください。"),
                HumanMessage(content="会話を続けてください。")
            ]
            return extract_content(llm.invoke(minimal_messages))
            
        except Exception as final_error:
            print(f"Final attempt error: {str(final_error)}")
            # 最後の手段として、基本的な応答を返す
            return "（考えながら）「申し訳ありません、少々お待ちください。」"
        
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return "（困惑した様子で）「少々お待ちください。」"

# 雑談練習用のヘルパー関数
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

@app.route("/api/start_chat", methods=["POST"])
def start_chat():
    """雑談練習の開始"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        partner_type = data.get("partner_type")
        situation = data.get("situation")
        topic = data.get("topic")
        selected_model = data.get("model")

        # システムプロンプトの構築
        system_prompt = f"""あなたは{get_partner_description(partner_type)}として振る舞います。
現在の状況: {get_situation_description(situation)}
話題: {get_topic_description(topic)}

以下の点に注意して会話を進めてください：
1. 指定された立場や状況に応じた適切な話し方を心がける
2. 相手の発言に興味を示し、話を広げる質問をする
3. 適度に自分の経験や意見も交える
4. 会話の自然な流れを維持する
5. 職場での適切な距離感を保つ
6. 必ず日本語のみで応答する（英語は使用しない）
7. 相手の発言の内容に合わせて自然に会話を展開する
8. 感情表現は日本語で行う（例：「（笑顔で）」「（驚いた様子で）」）

応答の制約：
- 感情や仕草は（）内に記述
- 発言は「」で囲む
- 1回の応答は3行程度まで
- 必ず日本語のみを使用する
- ローマ字や英語は使用しない
"""

        try:
            # モデルの初期化
            if selected_model.startswith('openai/'):
                llm = create_openai_llm(selected_model)
            elif selected_model.startswith('gemini/'):
                llm = create_gemini_llm(selected_model)
            else:
                llm = create_ollama_llm(selected_model)

            # 初期メッセージの生成
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content="雑談を始めてください。最初の声掛けをお願いします。")
            ]
            
            response = llm.invoke(messages)
            initial_message = extract_content(response)

            # セッションに会話設定を保存
            session["chat_settings"] = {
                "partner_type": partner_type,
                "situation": situation,
                "topic": topic,
                "system_prompt": system_prompt
            }

            return jsonify({"response": initial_message})

        except Exception as e:
            print(f"Error in chat initialization: {str(e)}")
            return jsonify({"error": f"チャットの初期化に失敗しました: {str(e)}"}), 500

    except Exception as e:
        print(f"Error in start_chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

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

        # フバッグ用ログ出力
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

        try:
            # フィードバック用のモデルを選択（Geminiを優先）
            llm = create_gemini_llm("gemini-pro")
            print("Using Gemini for feedback generation")
        except Exception as e:
            print(f"Gemini error: {str(e)}, falling back to OpenAI")
            llm = create_openai_llm("gpt-3.5-turbo")

        # フィードバック生成
        response = llm.invoke(feedback_prompt)
        feedback_content = extract_content(response)
        
        # デバッグ用ログ出力
        print("Generated feedback:", feedback_content)

        if not feedback_content:
            raise ValueError("フィードバックの生成に失敗しました")

        return jsonify({
            "feedback": feedback_content,
            "status": "success"
        })

    except Exception as e:
        print(f"Error in chat_feedback: {str(e)}")
        import traceback
        traceback.print_exc()  # スタックトレースを出力
        return jsonify({"error": str(e)}), 500

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

        # セッションの初期化
        session["watch_settings"] = {
            "model_a": model_a,
            "model_b": model_b,
            "partner_type": partner_type,
            "situation": situation,
            "topic": topic,
            "current_speaker": "A"
        }
        session["watch_history"] = []
        session.modified = True

        try:
            llm = create_llm(model_a)
            initial_message = generate_initial_message(
                llm, 
                partner_type,
                situation,
                topic
            )
            
            # 履歴に保存
            session["watch_history"].append({
                "speaker": "A",
                "message": initial_message,
                "timestamp": datetime.now().isoformat()
            })
            session.modified = True

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
            llm = create_llm(model)
            next_message = generate_next_message(llm, history)
            
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

def create_llm(model_name):
    """モデル名に基づいて適切なLLMインスタンスを作成"""
    if model_name.startswith('openai/'):
        return create_openai_llm(model_name.replace('openai/', ''))
    elif model_name.startswith('gemini/'):
        return create_gemini_llm(model_name.replace('gemini/', ''))
    else:
        return create_ollama_llm(model_name)

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

# ========== メイン起動 ==========
if __name__ == "__main__":
    # 本番運用時はgunicornなどを使う想定
    app.run(debug=True, host="0.0.0.0", port=5000)
