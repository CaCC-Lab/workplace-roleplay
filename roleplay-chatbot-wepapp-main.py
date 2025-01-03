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

# ========== シナリオ（職場のあなた再現シートを想定したデータ） ==========
# 実際にはデータベースや外部ファイルなどで管理するのがおすすめ
scenarios = {
    "scenario1": {
        "title": "上司から急な仕事を頼まれた",
        "description": "既に他のタスクが立て込んでいる中、上司から急な依頼...",
        "role_info": "AIは上司役、あなたは新入社員",
        "character_setting": {
            "personality": "40代後半の男性課長。仕事はできるが部下の状況への配慮が少し足りない。基本的には良い上司だが、納期に追われると強引になることも。",
            "speaking_style": "「〜かな」「〜だけど」など、やや砕けた話し方。ただし指示を出すときは「〜してもらえる？」「〜お願いできる？」とやや丁寧に。",
            "situation": "重要クライアントからの急な要望で、今日中に資料を修正する必要がある。既に夕方5時を回っている。",
            "initial_approach": "「すまない、ちょっと急ぎの件で相談があるんだけど...」と、やや申し訳なさそうに声をかける"
        },
        "learning_points": [
            "タスクの優先順位付け",
            "上司への状況説明の仕方",
            "建設的な代替案の提示"
        ],
        "feedback_points": [
            "コミュニケーションの明確さ",
            "態度の適切さ",
            "問題解決力"
        ]
    },
    "scenario2": {
        "title": "同僚と作業分担でもめそう",
        "description": "同僚と一緒に取り組むプロジェクトで、分担が不公平になっている気がする。いつも自分だけ残業している状況。どう切り出す？",
        "role_info": "AIは同僚役、あなたは同僚A",
        "character_setting": {
            "personality": "20代後半の男性社員。仕事は普通にできるが、自分の都合を優先しがち。悪意はないが少し自己中心的。",
            "speaking_style": "フランクな話し方。「〜だよね」「〜じゃん」など、カジュアルな口調。",
            "situation": "共同プロジェクトで、自分の担当部分はさっさと済ませて帰ろうとしている。相手の負担には気付いていない様子。",
            "initial_approach": "「お、今日も残業？大変だね〜。僕はもう終わったから帰ろうと思ってたんだけど。」と、やや無神経に声をかける"
        },
        "learning_points": [
            "公平な作業分担の提案方法",
            "建設的な対話の進め方",
            "感情的にならない伝え方"
        ],
        "feedback_points": [
            "主張の明確さ",
            "感情のコントロール",
            "解決策の具体性"
        ]
    }
}

# ========== Flaskルート ==========
@app.route("/")
def index():
    """
    トップページ
    """
    return render_template("index.html")

@app.route("/chat")
def chat():
    """
    自由会話ページ
    """
    local_models = get_available_local_models()
    openai_models = [f"openai/{model}" for model in get_available_openai_models()]
    return render_template("chat.html", models=local_models + openai_models)

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
    # request.jsonがNoneの場合のチェック
    if request.json is None:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    selected_model = request.json.get("model", "llama2")
    
    if "conversation_history" in session and selected_model in session["conversation_history"]:
        session["conversation_history"][selected_model] = []
        session.modified = True
        return jsonify({"status": "success", "message": "会話履歴がクリアされました"})
    else:
        return jsonify({"status": "error", "message": "会話履歴が見つかりません"}), 404

# シナリオ一覧を表示するページ
@app.route("/scenarios")
def list_scenarios():
    """
    シナリオのタイトル一覧を表示
    """
    return render_template("scenarios_list.html", scenarios=scenarios)

# シナリオを選択してロールプレイ画面へ
@app.route("/scenario/<scenario_id>")
def show_scenario(scenario_id):
    """
    選択されたシナリオの概要を表示し、ロールプレイ画面 (scenario.html) をレンダリング
    """
    if scenario_id not in scenarios:
        return "シナリオが見つかりません。", 404

    scenario_data = scenarios[scenario_id]
    return render_template("scenario.html", 
                         scenario_id=scenario_id,
                         scenario_title=scenario_data["title"],
                         scenario_desc=scenario_data["description"],
                         scenario=scenario_data)

@app.route("/api/scenario_chat", methods=["POST"])
def scenario_chat():
    """
    ロールプレイモード専用のチャットAPI
    - シナリオごとに別メモリを管理し、AIに「上司役」「同僚役」などを演じさせる
    """
    data = request.json
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    user_message = data.get("message", "")
    scenario_id = data.get("scenario_id", "")
    
    if not scenario_id or scenario_id not in scenarios:
        return jsonify({"error": "無効なシナリオIDです"}), 400

    # シナリオ情報を取得
    scenario_data = scenarios[scenario_id]
    
    # プロンプトを構築
    system_prompt = f"""\
# ロールプレイ設定
あなたは{scenario_data["role_info"]}として振る舞ってください。

## キャラクター設定
- 性格: {scenario_data["character_setting"]["personality"]}
- 話し方: {scenario_data["character_setting"]["speaking_style"]}
- 状況: {scenario_data["character_setting"]["situation"]}

## 演技の注意点
1. 常に設定された役柄を演じ切ってください
2. 指定された話し方を一貫して使用してください
3. 感情や表情も適切に言葉で表現してください
4. 相手の発言に自然に反応してください
5. 職場での適切な距離感を保ちつつ、リアルな会話を心がけてください

## シナリオ背景
{scenario_data["description"]}
"""

    # シナリオ専用の会話履歴をセッションに保存
    # 例: session["scenario_history"][シナリオID] = [...]
    if "scenario_history" not in session:
        session["scenario_history"] = {}

    if scenario_id not in session["scenario_history"]:
        # シナリオごとに会話履歴のリストを持つ
        session["scenario_history"][scenario_id] = []

    scenario_history = session["scenario_history"][scenario_id]

    # LLMを生成 (ここではOllamaまたはOpenAIの既定モデルを仮利用)
    # 必要ならUIでモデルを切り替え可能にしてもOK
    # ここではデモなので "gpt-3.5-turbo" を固定例とします。
    llm_instance = create_openai_llm("gpt-3.5-turbo")
    # ※ ローカルLLMでやりたい場合は create_ollama_llm("llama2") 等に切り替え

    # ConversationBufferMemoryを再現
    memory = ConversationBufferMemory()

    # 過去のシナリオ会話を読み込み
    for entry in scenario_history:
        memory.save_context({"input": entry["human"]}, {"output": entry["ai"]})

    # ConversationChain構築
    chain = ConversationChain(
        llm=llm_instance,
        memory=memory,
        verbose=True
    )

    # ---- シナリオの前提をプロンプトに組み込む ----
    # 最初にシナリオが開始された時点で、AIに「ロール」を割り当てたい。
    # もし最初のユーザメッセージなら、シナリオ背景とロール情報をAIに伝える。
    if len(scenario_history) == 0:
        init_prompt = f"""\
{system_prompt}

最初の声掛けとして、以下の設定で話しかけてください：
{scenario_data["character_setting"]["initial_approach"]}
"""
        first_response = chain.predict(input=init_prompt)
        scenario_history.append({
            "human": "[シナリオ開始]",
            "ai": first_response
        })
        session.modified = True
        return jsonify({"response": first_response})

    # ---- 次のユーザメッセージに対するAIの応答を取得 ----
    response = chain.predict(input=user_message)

    # セッションに履歴を保存
    scenario_history.append({
        "human": user_message,
        "ai": response
    })
    session.modified = True

    return jsonify({"response": response})

@app.route("/api/scenario_clear", methods=["POST"])
def scenario_clear():
    """
    指定されたシナリオの会話履歴をクリア
    """
    # request.jsonがNoneの場合のチェック
    if request.json is None:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    data = request.json
    scenario_id = data.get("scenario_id", "")
    
    if not scenario_id:
        return jsonify({"status": "error", "message": "シナリオIDが指定されていません"}), 400

    if "scenario_history" in session and scenario_id in session["scenario_history"]:
        session["scenario_history"][scenario_id] = []
        session.modified = True
        return jsonify({"status": "success", "message": "シナリオの履歴をクリアしました。"})
    else:
        return jsonify({"status": "error", "message": "指定シナリオの履歴が見つかりません。"}), 404

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
あなたは職場コミュニケーションの専門家として、以下のロールプレイでのユーザーの対応について評価してください。

## シナリオ設定
{scenario_data["description"]}

## ユーザーの立場
{scenario_data["role_info"].split("、")[1]}  # "AIは上司役、あなたは新入社員" の後半部分を取得

## ユーザーの発言履歴
{format_conversation_history(history)}

## 評価の観点
{', '.join(scenario_data["feedback_points"])}

## 学習目標
{', '.join(scenario_data["learning_points"])}

以下の形式で、ユーザーの対応についてフィードバックを提供してください：

# 良かった点（強み）
- ユーザーの発言から見られた効果的なコミュニケーションポイント
- 特に評価できる対応や姿勢

# 改善のヒント
- より効果的なコミュニケーションのためのアドバイス
- 具体的な言い回しの提案

# 実践アドバイス
1. すぐに試せる具体的な練習方法
2. 類似シーンでの応用ポイント
3. 次回のロールプレイでの注目ポイント
"""

    # OpenAI APIでフィードバックを生成
    llm = create_openai_llm()
    feedback = llm.predict(feedback_prompt)

    return jsonify({
        "feedback": feedback,
        "scenario": scenario_data["title"]
    })

def format_conversation_history(history):
    """会話履歴を読みやすい形式にフォーマット"""
    formatted = []
    for entry in history:
        # シナリオ開始マーカーはスキップ
        if entry.get("human") == "[シナリオ開始]":
            continue
        # ユーザーの発言のみを含める
        if entry.get("human"):
            formatted.append(f"ユーザー: {entry['human']}")
    return "\n".join(formatted)

# ========== メイン起動 ==========
if __name__ == "__main__":
    # 本番運用時はgunicornなどを使う想定
    app.run(debug=True, host="0.0.0.0", port=5000)
