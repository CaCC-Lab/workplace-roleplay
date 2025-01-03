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
from typing import Optional, Dict
from datetime import datetime

# LangChain関連
from langchain_community.chat_models import ChatOpenAI
from langchain_community.llms.ollama import Ollama  # 修正：正しいインポートパス
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from openai import OpenAI as OpenAIClient  # OpenAIクライアントを追加
from langchain_core.runnables import RunnableWithMessageHistory  # 新しい会話チェーン

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

# デフォルトモデルの設定
DEFAULT_MODEL = "openai/gpt-4o-mini"

def get_available_openai_models():
    """
    OpenAI APIから利用可能なモデル一覧を取得
    エラー時は基本モデルのリストを返す
    """
    try:
        client = OpenAIClient(api_key=OPENAI_API_KEY)
        models = client.models.list()
        
        # ChatモデルとGPTモデルのみをフィルタリング
        chat_models = []
        for model in models:
            if model.id.startswith(("gpt-4", "gpt-3.5")):
                # モデル名の先頭に"openai/"を付加
                chat_models.append(f"openai/{model.id}")
        
        return sorted(chat_models)  # モデル名でソート
    except Exception as e:
        print(f"OpenAI models fetch error: {e}")
        # エラー時は基本的なモデルのリストを返す
        return [
            "openai/gpt-4",
            "openai/gpt-4-turbo-preview",
            "openai/gpt-3.5-turbo"
        ]

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
    """トップページ"""
    return render_template("index.html")

@app.route("/chat")
def chat():
    """
    自由会話ページ
    """
    # 利用可能なモデルを取得
    openai_models = get_available_openai_models()
    local_models = get_available_local_models()
    
    # OpenAIモデルとローカルモデルを結合
    available_models = openai_models + local_models
    
    return render_template(
        "chat.html",
        models=available_models
    )

@app.route("/api/chat", methods=["POST"])
def chat_message():
    """
    チャットAPIエンドポイント
    """
    try:
        data = request.json
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        user_message = data.get("message", "")
        selected_model = data.get("model", DEFAULT_MODEL)

        # モデルの選択と初期化
        if selected_model.startswith("openai/"):
            openai_model_name = selected_model.split("/")[1]
            llm_instance = create_openai_llm(model_name=openai_model_name)
        else:
            # Ollamaモデルの場合、存在確認
            if selected_model not in get_available_local_models():
                return jsonify({
                    "error": f"モデル '{selected_model}' が見つかりません。"
                           f"ollama pull {selected_model} を実行してください。"
                }), 404
            llm_instance = create_ollama_llm(selected_model)

        # 会話履歴の初期化
        if "chat_history" not in session:
            session["chat_history"] = []

        # メモリの初期化
        memory = ConversationBufferMemory()
        
        # 過去の会話履歴を読み込み
        for entry in session["chat_history"]:
            memory.save_context(
                {"input": entry["human"]},
                {"output": entry["ai"]}
            )

        # ConversationChain構築
        chain = ConversationChain(
            llm=llm_instance,
            memory=memory,
            verbose=True
        )

        # 応答を生成
        response = chain.predict(input=user_message)

        # セッションに履歴を保存
        session["chat_history"].append({
            "human": user_message,
            "ai": response,
            "timestamp": datetime.now().isoformat()
        })
        session.modified = True

        return jsonify({"response": response})

    except Exception as e:
        print(f"Error in chat: {str(e)}")
        return jsonify({"error": "チャット処理中にエラーが発生しました"}), 500

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
    """個別のシナリオページ"""
    if scenario_id not in scenarios:
        return "シナリオが見つかりません", 404
    
    # 利用可能なモデルを取得
    openai_models = get_available_openai_models()
    local_models = get_available_local_models()
    
    # OpenAIモデルとローカルモデルを結合
    available_models = openai_models + local_models
    
    return render_template(
        "scenario.html",
        scenario_id=scenario_id,
        scenario=scenarios[scenario_id],
        scenario_title=scenarios[scenario_id]["title"],
        scenario_desc=scenarios[scenario_id]["description"],
        models=available_models
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
        
        if not scenario_id or scenario_id not in scenarios:
            return jsonify({"error": "無効なシナリオIDです"}), 400

        # シナリオ情報を取得
        scenario_data = scenarios[scenario_id]
        
        # シナリオ専用の会話履歴をセッションに保存
        if "scenario_history" not in session:
            session["scenario_history"] = {}

        if scenario_id not in session["scenario_history"]:
            session["scenario_history"][scenario_id] = []

        # モデルの選択と初期化
        if selected_model.startswith("openai/"):
            openai_model_name = selected_model.split("/")[1]
            llm_instance = create_openai_llm(model_name=openai_model_name)
        else:
            # Ollamaモデルの場合、存在確認
            if selected_model not in get_available_local_models():
                return jsonify({
                    "error": f"モデル '{selected_model}' が見つかりません。"
                           f"ollama pull {selected_model} を実行してください。"
                }), 404
            llm_instance = create_ollama_llm(selected_model)

        # 会話履歴を使ってメモリを初期化
        memory = ConversationBufferMemory()
        
        # システムプロンプトを構築
        system_prompt = f"""\
# ロールプレイの設定
あなたは{scenario_data["role_info"].split("、")[0].replace("AIは", "")}です。

## キャラクター設定
性格: {scenario_data["character_setting"]["personality"]}
話し方: {scenario_data["character_setting"]["speaking_style"]}
状況: {scenario_data["character_setting"]["situation"]}

## 演技の注意点
1. 常に設定された役柄を一貫して演じ続けてください
2. 指定された話し方を厳密に守ってください
3. 感情や表情も自然に表現してください（例：「少し困ったような表情で」「申し訳なさそうに」など）
4. 相手の発言に対して適切な反応を示してください
5. 職場での適切な距離感を保ちつつ、リアルな会話を心がけてください
6. 一度に長すぎる発言は避け、自然な会話の長さを保ってください

## 現在の状況
{scenario_data["description"]}
"""
        
        # システムプロンプトを最初に追加
        if len(session["scenario_history"][scenario_id]) == 0:
            memory.save_context(
                {"input": "シナリオ設定"},
                {"output": system_prompt}
            )

        # 過去の会話履歴を読み込み
        for entry in session["scenario_history"][scenario_id]:
            memory.save_context(
                {"input": entry["human"]},
                {"output": entry["ai"]}
            )

        # ConversationChain構築
        chain = ConversationChain(
            llm=llm_instance,
            memory=memory,
            verbose=True
        )

        # 最初のメッセージの場合
        if len(session["scenario_history"][scenario_id]) == 0:
            init_prompt = f"""\
{memory.load_memory_variables({"input": "シナリオ設定"})["output"]}

あなたは{scenario_data["character_setting"]["initial_approach"]}という設定で
最初の声掛けをしてください。
感情や表情も自然に含めて表現してください。
"""
            first_response = chain.predict(input=init_prompt)
            session["scenario_history"][scenario_id].append({
                "human": "[シナリオ開始]",
                "ai": first_response,
                "timestamp": datetime.now().isoformat()
            })
            session.modified = True
            return jsonify({"response": first_response})

        # ユーザーの発言に対する応答を生成
        context_prompt = f"""\
前の会話を踏まえて、{scenario_data["role_info"].split("、")[0].replace("AIは", "")}として
以下のユーザーの発言に自然に応答してください：

{user_message}

## 注意点
- 感情や表情も含めて表現する
- 設定された話し方を守る
- 適切な長さで返答する
- 職場の上下関係や距離感を意識する
"""
        response = chain.predict(input=context_prompt)

        # セッションに履歴を保存
        session["scenario_history"][scenario_id].append({
            "human": user_message,
            "ai": response,
            "timestamp": datetime.now().isoformat()
        })
        session.modified = True

        return jsonify({"response": response})

    except Exception as e:
        print(f"Error in scenario_chat: {str(e)}")
        return jsonify({"error": "チャット処理中にエラーが発生しました"}), 500

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

# ========== メイン起動 ==========
if __name__ == "__main__":
    # 本番運用時はgunicornなどを使う想定
    app.run(debug=True, host="0.0.0.0", port=5000)
