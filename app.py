"""
workplace-roleplay メインアプリケーション
職場コミュニケーション練習アプリ

リファクタリング後のエントリポイント
- Blueprint方式でルートを分離
- アプリケーションファクトリパターンを採用
"""

from typing import Optional
from datetime import datetime
from flask import Flask

# 設定モジュール
from config import get_cached_config

# コアモジュール
from core.extensions import init_extensions
from core.error_handlers import register_error_handlers
from core.middleware import register_middleware

# ルート登録
from routes import register_blueprints


def create_app(config=None) -> Flask:
    """
    アプリケーションファクトリ

    Args:
        config: 設定オブジェクト（オプション）

    Returns:
        Flask: 初期化されたFlaskアプリケーション
    """
    app = Flask(__name__)

    # 設定の読み込み
    if config is None:
        config = get_cached_config()

    # Flask設定の適用
    app.secret_key = config.SECRET_KEY
    app.config["DEBUG"] = config.DEBUG
    app.config["TESTING"] = config.TESTING
    app.config["WTF_CSRF_ENABLED"] = config.WTF_CSRF_ENABLED

    # セッション設定
    app.config["SESSION_TYPE"] = config.SESSION_TYPE
    app.config["SESSION_LIFETIME"] = config.SESSION_LIFETIME_MINUTES * 60

    # 拡張の初期化（セッション、Redis等）
    init_extensions(app, config)

    # エラーハンドラー登録
    register_error_handlers(app)

    # ミドルウェア登録（CSRF等）
    register_middleware(app)

    # Blueprint登録
    register_blueprints(app)

    # カスタムJinjaフィルターの登録
    _register_template_filters(app)

    # Gemini APIの初期化
    _initialize_gemini_api(config)

    return app


def _register_template_filters(app: Flask):
    """テンプレートフィルターを登録"""

    @app.template_filter("datetime")
    def format_datetime(value):
        """ISO形式の日時文字列をより読みやすい形式に変換"""
        if not value:
            return "なし"
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime("%Y年%m月%d日 %H:%M")
        except (ValueError, TypeError):
            return str(value)


def _initialize_gemini_api(config):
    """Gemini APIを初期化"""
    try:
        import google.generativeai as genai

        api_key = config.GOOGLE_API_KEY
        if api_key and not config.TESTING:
            genai.configure(api_key=api_key)
            print("✅ Gemini API初期化完了")
        elif config.TESTING:
            print("📝 テストモード: Gemini API初期化スキップ")
        else:
            print("⚠️ GOOGLE_API_KEYが設定されていません")
    except Exception as e:
        print(f"❌ Gemini API初期化エラー: {e}")


# ========== 後方互換性のための関数（ルートから参照される） ==========

# グローバル変数（既存コードとの互換性のため）
llm = None
scenarios = {}
feature_flags = None


def initialize_llm(model_name: str):
    """モデル名に基づいて適切なLLMを初期化"""
    from services.llm_service import LLMService

    service = LLMService()
    return service.initialize_llm(model_name)


def create_gemini_llm(model_name: str = "gemini-1.5-flash"):
    """LangChainのGemini Chat modelインスタンス生成"""
    from services.llm_service import LLMService

    service = LLMService()
    return service.create_gemini_llm(model_name)


def extract_content(resp):
    """様々な形式のレスポンスから内容を抽出"""
    from utils.helpers import extract_content as _extract_content

    return _extract_content(resp)


def create_model_and_get_response(model_name: str, messages_or_prompt, extract=True):
    """指定されたモデルでLLMを初期化し、応答を取得する共通関数"""
    try:
        llm = initialize_llm(model_name)
        response = llm.invoke(messages_or_prompt)

        if extract:
            return extract_content(response)
        return response
    except Exception:
        raise


def try_multiple_models_for_prompt(prompt: str, preferred_model: Optional[str] = None):
    """Geminiモデルを使用してプロンプトに対する応答を取得するヘルパー関数（サービス層経由）"""
    from services.feedback_service import get_feedback_service

    feedback_service = get_feedback_service()
    return feedback_service.try_multiple_models_for_prompt(prompt, preferred_model)


def update_feedback_with_strength_analysis(feedback_response, session_type, scenario_id=None):
    """既存のフィードバックレスポンスに強み分析を追加するヘルパー関数（サービス層経由）"""
    from services.strength_service import get_strength_service

    strength_service = get_strength_service()
    return strength_service.update_feedback_with_strength_analysis(feedback_response, session_type, scenario_id)


def get_available_gemini_models():
    """利用可能なGeminiモデルのリストを返す"""
    try:
        config = get_cached_config()
        import google.generativeai as genai

        if not config.GOOGLE_API_KEY:
            return []

        genai.configure(api_key=config.GOOGLE_API_KEY)
        models = genai.list_models()

        gemini_models = []
        for model in models:
            if "gemini" in model.name.lower():
                model_short_name = model.name.split("/")[-1]
                model_name = f"gemini/{model_short_name}"
                gemini_models.append(model_name)

        return gemini_models

    except Exception as e:
        print(f"Error fetching Gemini models: {str(e)}")
        return ["gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash"]


# シナリオのロード
def _load_scenarios():
    """シナリオをロード"""
    global scenarios
    try:
        from scenarios import load_scenarios

        scenarios = load_scenarios()
        print(f"✅ シナリオロード成功: {len(scenarios)}個")
    except Exception as e:
        print(f"❌ シナリオロードエラー: {e}")
        scenarios = {}


# 初期化時にシナリオをロード
_load_scenarios()


# ========== アプリケーションインスタンス ==========

# デフォルトのアプリケーションインスタンス（後方互換性のため）
app = create_app()


# ========== 後方互換性のためのルート別名登録 ==========
# テンプレートで `url_for('index')` などを使用している場合の互換性

# 重要：テンプレートの url_for() は Blueprint名付きに更新が必要
# 例: url_for('index') -> url_for('main.index')
# 以下はその間の移行期間用の互換性レイヤー

# 後方互換性用（実際の使用箇所は削除済み）

# Blueprintの関数を取得して別名でルートを登録
_main_index = app.view_functions.get("main.index")
_main_chat_page = app.view_functions.get("main.chat_page")
_scenario_list = app.view_functions.get("scenario.list_scenarios")
_scenario_show = app.view_functions.get("scenario.show_scenario")
_scenario_regular = app.view_functions.get("scenario.list_regular_scenarios")
_scenario_harassment = app.view_functions.get("scenario.list_harassment_scenarios")
_watch_mode = app.view_functions.get("watch.watch_mode")

# 別名エンドポイントを登録（既存のルールとは異なるエンドポイント名で）
if _main_index:
    app.view_functions["index"] = _main_index
if _main_chat_page:
    app.view_functions["chat"] = _main_chat_page
if _scenario_list:
    app.view_functions["list_scenarios"] = _scenario_list
if _scenario_show:
    app.view_functions["show_scenario"] = _scenario_show
if _scenario_regular:
    app.view_functions["list_regular_scenarios"] = _scenario_regular
if _scenario_harassment:
    app.view_functions["list_harassment_scenarios"] = _scenario_harassment
if _watch_mode:
    app.view_functions["watch_mode"] = _watch_mode

# 追加のview_functions参照
_journal_view = app.view_functions.get("journal.view_journal")
_strength_page = app.view_functions.get("strength.strength_analysis_page")
_scenario_chat = app.view_functions.get("scenario.scenario_chat")

if _journal_view:
    app.view_functions["view_journal"] = _journal_view
if _strength_page:
    app.view_functions["strength_analysis_page"] = _strength_page
if _scenario_chat:
    app.view_functions["scenario_chat"] = _scenario_chat

# url_mapにルールを追加（url_for互換性のため）
from werkzeug.routing import Rule

try:
    # 既存のルールに別名エンドポイントを追加
    app.url_map.add(Rule("/", endpoint="index", methods=["GET"]))
    app.url_map.add(Rule("/chat", endpoint="chat", methods=["GET"]))
    app.url_map.add(Rule("/scenarios", endpoint="list_scenarios", methods=["GET"]))
    app.url_map.add(Rule("/scenario/<scenario_id>", endpoint="show_scenario", methods=["GET"]))
    app.url_map.add(Rule("/scenarios/regular", endpoint="list_regular_scenarios", methods=["GET"]))
    app.url_map.add(Rule("/scenarios/harassment", endpoint="list_harassment_scenarios", methods=["GET"]))
    app.url_map.add(Rule("/watch", endpoint="watch_mode", methods=["GET"]))
    app.url_map.add(Rule("/journal", endpoint="view_journal", methods=["GET"]))
    app.url_map.add(Rule("/strength_analysis", endpoint="strength_analysis_page", methods=["GET"]))
    app.url_map.add(Rule("/api/scenario_chat", endpoint="scenario_chat", methods=["POST"]))
    print("✅ テンプレート互換性のためのルート別名を登録しました")
except Exception as e:
    print(f"⚠️ ルート別名登録の一部がスキップされました: {e}")


# ========== メイン起動 ==========

if __name__ == "__main__":
    config = get_cached_config()
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT, use_reloader=config.HOT_RELOAD)
