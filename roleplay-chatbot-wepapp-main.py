"""
依存パッケージ:
- Flask
- Flask-Session
- requests
- langchain
- langchain-community

インストール方法:
pip install -r requirements.txt
"""

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import requests
import os
from typing import Optional

# LangChain関連
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOpenAI
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from openai import OpenAI as OpenAIClient  # OpenAIクライアントを追加

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

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

# LLMの温度やその他パラメータは必要に応じて調整
DEFAULT_TEMPERATURE = 0.7

def get_available_openai_models():
    """
    OpenAI APIから利用可能なモデル一覧を取得
    エラー時は空リストを返す
    """
    try:
        client = OpenAIClient(api_key=OPENAI_API_KEY)
        models = client.models.list()
        # ChatモデルとGPTモデルのみをフィルタリング
        chat_models = [
            model.id for model in models 
            if model.id.startswith(("gpt-4", "gpt-3.5"))
        ]
        return sorted(chat_models)  # モデル名でソート
    except Exception as e:
        print(f"OpenAI models fetch error: {e}")
        return []

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
    LangChainのOllama LLMインスタンス生成
    """
    callbacks = [StreamingStdOutCallbackHandler()]
    return Ollama(
        model=model_name,
        callbacks=callbacks,
        temperature=DEFAULT_TEMPERATURE,
    )

def create_openai_llm(model_name: str = "gpt-3.5-turbo") -> ChatOpenAI:
    """
    LangChainのOpenAI Chat modelインスタンス生成
    
    Args:
        model_name (str): 使用するモデル名
    
    Returns:
        ChatOpenAI: OpenAIのチャットモデルインスタンス
    """
    return ChatOpenAI(
        temperature=DEFAULT_TEMPERATURE,
        api_key=OPENAI_API_KEY,
        max_tokens=512,
        model=model_name,
    )

# ========== Flaskルート ==========
@app.route("/")
def index():
    """
    トップページ
    - ローカルLLMモデル一覧取得
    - OpenAIモデル一覧を動的に取得
    - index.html を返す
    """
    local_models = get_available_local_models()
    openai_models = [f"openai/{model}" for model in get_available_openai_models()]
    return render_template("index.html", models=local_models + openai_models)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    チャットAPI
    """
    data = request.json
    if data is None:  # request.jsonがNoneの場合のチェック
        return jsonify({"error": "Invalid JSON"}), 400
        
    user_message = data.get("message", "")
    selected_model = data.get("model", "llama2")

    # OpenAIモデルかどうかをプレフィックスで判断
    if selected_model.startswith("openai/"):
        openai_model_name = selected_model.split("/")[1]  # プレフィックスを除去
        llm_instance = create_openai_llm(model_name=openai_model_name)
    else:
        llm_instance = create_ollama_llm(selected_model)

    # 会話履歴をセッションに保存
    if "conversation_history" not in session:
        session["conversation_history"] = {}
    
    if selected_model not in session["conversation_history"]:
        session["conversation_history"][selected_model] = []
    
    history = session["conversation_history"][selected_model]

    # 会話履歴を使って新しいメモリを作成
    memory = ConversationBufferMemory()
    for entry in history:
        memory.save_context({"input": entry["human"]}, {"output": entry["ai"]})

    chain = ConversationChain(
        llm=llm_instance,
        memory=memory,
        verbose=True
    )

    # 応答を生成
    response = chain.predict(input=user_message)

    # 会話履歴を更新
    history.append({
        "human": user_message,
        "ai": response
    })
    session.modified = True

    return jsonify({"response": response})

@app.route("/api/models", methods=["GET"])
def api_models():
    """
    ローカルLLM (ollama) のモデル一覧を返す
    + OpenAIモデル一覧も動的に取得して返す
    """
    local_models = get_available_local_models()
    openai_models = [f"openai/{model}" for model in get_available_openai_models()]
    all_models = local_models + openai_models
    return jsonify({"models": all_models})

@app.route("/api/clear_history", methods=["POST"])
def clear_history():
    """
    会話履歴をクリアするAPI
    """
    selected_model = request.json.get("model", "llama2")
    
    if "conversation_history" in session and selected_model in session["conversation_history"]:
        session["conversation_history"][selected_model] = []
        session.modified = True
        return jsonify({"status": "success", "message": "会話履歴がクリアされました"})
    else:
        return jsonify({"status": "error", "message": "会話履歴が見つかりません"}), 404

# ========== メイン起動 ==========
if __name__ == "__main__":
    # 本番運用時はgunicornなどを使う想定
    app.run(debug=True, host="0.0.0.0", port=5000)
