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
from typing import Optional, Dict, List
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
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

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
    """
    return ChatOpenAI(
        temperature=DEFAULT_TEMPERATURE,
        api_key=OPENAI_API_KEY,
        max_tokens=1500,
        model=model_name,
    )

# ========== シナリオ（職場のあなた再現シートを想定したデータ） ==========
# 実際にはデータベースや外部ファイルなどで管理するのがおすすめ
scenarios = {
    "scenario1": {
        "title": "上司から曖昧な仕事を依頼された",
        "description": "上司から「この書類、今度の会議で配布するから参加者分準備をしておいて」とだけ依頼される場面です。",
        "difficulty": "初級",
        "tags": ["指示の確認", "コミュニケーション基礎", "報告・連絡・相談"],
        "role_info": "AIは上司役、あなたは新入社員",
        "character_setting": {
            "personality": "40代後半の男性課長。仕事はできるが部下の状況への配慮が少し足りない。基本的には良い上司だが、納期に追われると強引になることも。",
            "speaking_style": "「〜かな」「〜だけど」など、やや砕けた話し方。ただし指示を出すときは「〜してもらえる？」「〜お願いできる？」とやや丁寧に。",
            "situation": "重要な会議の準備で忙しく、部下への指示を手短に済ませたい状況。",
            "initial_approach": "（資料を手に持ちながら）「あ、ちょっといい？この書類、今度の会議で配布するから参加者分準備をしておいて」"
        },
        "learning_points": [
            "曖昧な指示を受けた際の確認の仕方",
            "上司への質問の適切な方法",
            "必要な情報の洗い出し方"
        ],
        "feedback_points": [
            "質問の的確さ",
            "コミュニケーションの明確さ",
            "確認事項の網羅性"
        ]
    },
    "scenario2": {
        "title": "締切が迫っている仕事を抱えているときに、上司から別の仕事を頼まれた",
        "description": "既存の締切間近の仕事がある中で、上司から「悪いけど大至急で見積書20社分作ってくれ！」と新しい仕事を依頼される場面です。",
        "difficulty": "中級",
        "tags": ["優先順位管理", "タスク調整", "状況説明"],
        "role_info": "AIは上司役、あなたは中堅社員",
        "character_setting": {
            "personality": "50代前半の女性部長。仕事は非常に出来るが、複数のプロジェクトを同時に進行させているため、部下の状況を把握しきれていないことも。",
            "speaking_style": "テキパキとした口調。「〜お願い」「〜してもらえる？」など、丁寧だが急いでいる様子が伝わる話し方。",
            "situation": "取引先からの急な要請で、新しい見積書の作成が必要になった。",
            "initial_approach": "（急ぎ足で近づいてきて）「悪いけど大至急で見積書20社分作ってくれる？今日中に必要なの！」"
        },
        "learning_points": [
            "現在の業務状況の適切な説明方法",
            "優先順位の確認と調整",
            "建設的な代替案の提示"
        ],
        "feedback_points": [
            "状況説明の明確さ",
            "解決策の提案力",
            "コミュニケーションの適切さ"
        ]
    },
    "scenario3": {
        "title": "先輩からの指示にミスがあった",
        "description": "先輩から「印刷をしてほしい書類と印刷部数の書かれたメモ」を渡され、印刷するように頼まれた。しかし、メモに間違えを見つけた。",
        "difficulty": "中級",
        "tags": ["指示の確認", "ミスの指摘", "コミュニケーション"],
        "role_info": "AIは先輩役、あなたは後輩社員",
        "character_setting": {
            "personality": "30代前半の女性社員。細かいことに気がつくが、時々ミスをすることもある。",
            "speaking_style": "丁寧だが、時々早口になる。",
            "situation": "急いでいるため、細かいミスに気づかずに指示を出してしまった。",
            "initial_approach": "「この書類、印刷しておいてくれる？メモに部数を書いておいたから。」"
        },
        "learning_points": [
            "ミスを見つけた際の指摘方法",
            "指示内容の確認方法",
            "適切なコミュニケーションの取り方"
        ],
        "feedback_points": [
            "ミスの指摘の仕方",
            "指示の確認の適切さ",
            "コミュニケーションの明確さ"
        ]
    },
    "scenario4": {
        "title": "自分は帰ろうと思ったのに、先輩がまだ仕事中だった",
        "description": "自分の仕事が終わり帰ろうとしたが、先輩がまだ仕事をしているのを見かけた場面です。",
        "difficulty": "初級",
        "tags": ["職場の雰囲気", "コミュニケーション", "気配り"],
        "role_info": "AIは先輩役、あなたは後輩社員",
        "character_setting": {
            "personality": "40代の男性社員。仕事熱心で、後輩の面倒見が良い。",
            "speaking_style": "落ち着いた口調で話す。",
            "situation": "まだ仕事が残っており、後輩が帰るのを見て少し驚いている。",
            "initial_approach": "「お疲れ様。もう帰るの？」"
        },
        "learning_points": [
            "職場での気配りの仕方",
            "先輩への声掛けの方法",
            "職場の雰囲気を読む力"
        ],
        "feedback_points": [
            "気配りの適切さ",
            "コミュニケーションの円滑さ",
            "職場の雰囲気を読む力"
        ]
    },
    "scenario5": {
        "title": "後輩のミスなのに自分が怒られた",
        "description": "単なる先輩であり、後輩の上司ではないのにも関わらず、一緒に作業をしていたというだけで後輩がミスしたことを上司に怒られた。",
        "difficulty": "上級",
        "tags": ["責任の所在", "コミュニケーション", "問題解決"],
        "role_info": "AIは上司役、あなたは先輩社員",
        "character_setting": {
            "personality": "50代の男性部長。厳しいが、公平な判断を心がけている。",
            "speaking_style": "厳格な口調で話す。",
            "situation": "後輩のミスについて、先輩としての責任を問うている。",
            "initial_approach": "「後輩がミスしたと聞いた。一緒に作業していた君が先輩としてしっかりフォローしないとダメだろう。」"
        },
        "learning_points": [
            "責任の所在を明確にする方法",
            "上司への報告の仕方",
            "問題解決のためのコミュニケーション"
        ],
        "feedback_points": [
            "責任の所在の明確さ",
            "報告の適切さ",
            "問題解決のためのコミュニケーション"
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
