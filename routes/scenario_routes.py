"""
Scenario routes for the workplace-roleplay application.
Handles scenario-related API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from config.feature_flags import get_feature_flags
from flask import (
    Blueprint,
    Response,
    jsonify,
    render_template,
    request,
    session,
    url_for,
)
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

# サービス層のインポート
from services.scenario_service import get_scenario_service

from config import get_cached_config
from errors import (
    NotFoundError,
    ValidationError,
    secure_error_handler,
    with_error_handling,
)

# シナリオ関連のインポート
from scenarios import load_scenarios
from scenarios.category_manager import (
    get_categorized_scenarios as get_categorized_scenarios_func,
)
from scenarios.category_manager import (
    get_scenario_category_summary,
    is_harassment_scenario,
)

# セキュリティ関連のインポート
try:
    from utils.security import SecurityUtils
except ImportError:

    class SecurityUtils:
        @staticmethod
        def sanitize_input(text):
            return text

        @staticmethod
        def validate_scenario_id(scenario_id):
            return True

        @staticmethod
        def validate_model_name(model_name):
            return True

        @staticmethod
        def escape_html(content):
            import html

            return html.escape(str(content))

        @staticmethod
        def get_safe_error_message(e):
            return str(e)


from utils.helpers import (
    add_messages_from_history,
    add_to_session_history,
    clear_session_history,
    format_conversation_history_for_feedback,
    initialize_session_history,
    set_session_start_time,
)

# Blueprint作成
scenario_bp = Blueprint("scenario", __name__)

# 設定の取得
config = get_cached_config()
DEFAULT_MODEL = config.DEFAULT_MODEL

# シナリオサービスを取得
scenario_service = get_scenario_service()
scenarios = scenario_service.get_all_scenarios()


def _get_all_available_models() -> Dict[str, Any]:
    """利用可能なモデルリストを取得"""
    try:
        from routes.main_routes import get_all_available_models

        return get_all_available_models()
    except ImportError:
        return {
            "models": [
                {
                    "id": "gemini/gemini-1.5-pro",
                    "name": "gemini-1.5-pro",
                    "provider": "gemini",
                },
                {
                    "id": "gemini/gemini-1.5-flash",
                    "name": "gemini-1.5-flash",
                    "provider": "gemini",
                },
            ]
        }


def _get_categorized_scenarios_local() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """シナリオをカテゴリ別に分類する（サービス層を使用）"""
    return scenario_service.get_categorized_scenarios()


# ========== ページルート ==========


@scenario_bp.route("/scenarios")
def list_scenarios() -> str:
    """シナリオ一覧ページ"""
    model_info = _get_all_available_models()
    available_models = model_info["models"]

    return render_template(
        "scenarios_list.html", scenarios=scenarios, models=available_models
    )


@scenario_bp.route("/scenario/<scenario_id>")
def show_scenario(scenario_id: str) -> str:
    """シナリオページの表示"""
    scenario_data = scenario_service.get_scenario_by_id(scenario_id)
    if not scenario_data:
        return "シナリオが見つかりません", 404

    # シナリオ履歴の初期化
    initialize_session_history("scenario_history", scenario_id)

    # シナリオIDに基づいてカテゴリを判定し、戻り先URLを決定
    if scenario_service.is_harassment_scenario(scenario_id):
        back_url = url_for("scenario.list_harassment_scenarios")
    else:
        back_url = url_for("scenario.list_regular_scenarios")

    # フィーチャーフラグを取得
    try:
        feature_flags = get_feature_flags()
        enable_tts = feature_flags.tts_enabled
        enable_learning_history = feature_flags.learning_history_enabled
    except (AttributeError, Exception) as e:
        print(f"Warning: Failed to get feature flags: {e}")
        enable_tts = False
        enable_learning_history = False

    return render_template(
        "scenario.html",
        scenario_id=scenario_id,
        scenario_title=scenario_data.get("title", "無題のシナリオ"),
        scenario_desc=scenario_data.get("description", "説明がありません。"),
        scenario=scenario_data,
        default_model=DEFAULT_MODEL,
        back_url=back_url,
        enable_tts=enable_tts,
        enable_learning_history=enable_learning_history,
    )


@scenario_bp.route("/scenarios/regular")
@with_error_handling
def list_regular_scenarios():
    """通常のコミュニケーションシナリオ一覧ページ"""
    regular_scenarios, _ = _get_categorized_scenarios_local()

    model_info = _get_all_available_models()
    available_models = model_info["models"]

    return render_template(
        "scenarios/regular_list.html",
        scenarios=regular_scenarios,
        models=available_models,
        category="regular_communication",
    )


@scenario_bp.route("/scenarios/harassment")
@with_error_handling
def list_harassment_scenarios():
    """ハラスメント防止シナリオ一覧ページ（同意チェック付き）"""
    harassment_consent = session.get("harassment_consent", False)

    if not harassment_consent:
        return render_template(
            "scenarios/harassment_consent.html", next_url="/scenarios/harassment"
        )

    _, harassment_scenarios = _get_categorized_scenarios_local()

    model_info = _get_all_available_models()
    available_models = model_info["models"]

    return render_template(
        "scenarios/harassment_list.html",
        scenarios=harassment_scenarios,
        models=available_models,
        category="harassment_prevention",
    )


@scenario_bp.route("/harassment/consent", methods=["GET", "POST"])
def harassment_consent():
    """ハラスメント防止研修の同意画面・処理"""
    if request.method == "GET":
        return render_template("scenarios/harassment_consent.html")

    elif request.method == "POST":
        data = request.get_json()
        consent = data.get("consent", False)

        if consent:
            session["harassment_consent"] = True
            session["harassment_consent_timestamp"] = datetime.now().isoformat()
            session.modified = True

            return jsonify({"success": True, "redirect_url": "/scenarios/harassment"})
        else:
            return jsonify({"success": False, "message": "ハラスメント防止研修にアクセスするには同意が必要です。"})


# ========== APIルート ==========


@scenario_bp.route("/api/scenario_chat", methods=["POST"])
def scenario_chat() -> Response:
    """ロールプレイモード専用のチャットAPI"""
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

        # シナリオロードエラー時の対応
        if not scenarios:
            return jsonify({"error": "シナリオデータが利用できません。"}), 503

        scenario_data = scenario_service.get_scenario_by_id(scenario_id)
        if not scenario_data:
            return jsonify({"error": "無効なシナリオIDです"}), 400

        # リバースロール（上司役）の場合の処理
        is_reverse_role = scenario_data.get("role_type") == "reverse"

        # セッション初期化
        initialize_session_history("scenario_history", scenario_id)

        # 初回メッセージの場合はセッション開始時間を記録
        if len(session["scenario_history"].get(scenario_id, [])) == 0:
            set_session_start_time("scenario", scenario_id)

        # システムプロンプトを構築（サービス層を使用）
        system_prompt = scenario_service.build_system_prompt(
            scenario_data, is_reverse_role
        )

        response = ""

        try:
            from app import extract_content, initialize_llm
            from errors import handle_llm_specific_error

            messages: List[BaseMessage] = []
            messages.append(SystemMessage(content=system_prompt))
            add_messages_from_history(
                messages, session["scenario_history"][scenario_id]
            )

            if len(session["scenario_history"][scenario_id]) == 0:
                # 初期メッセージの取得（サービス層を使用）
                initial_message = scenario_service.get_initial_message(
                    scenario_data, is_reverse_role
                )

                if is_reverse_role:
                    if not user_message and initial_message:
                        add_to_session_history(
                            "scenario_history",
                            {"human": "[シナリオ開始]", "ai": initial_message},
                            scenario_id,
                        )
                        return jsonify(
                            {"response": SecurityUtils.escape_html(initial_message)}
                        )
                    else:
                        messages.append(HumanMessage(content=user_message))
                else:
                    if initial_message:
                        messages.append(HumanMessage(content=initial_message))
            else:
                messages.append(HumanMessage(content=user_message))

            llm = initialize_llm(selected_model)
            llm_response = llm.invoke(messages)
            response = extract_content(llm_response)

        except Exception as e:
            from errors import handle_llm_specific_error

            app_error = handle_llm_specific_error(e, "Gemini")
            print(f"Error in chat: {app_error.message}")
            response = f"申し訳ありません。{app_error.message}"

        # セッションに履歴を保存
        add_to_session_history(
            "scenario_history",
            {"human": user_message if user_message else "[シナリオ開始]", "ai": response},
            scenario_id,
        )

        return jsonify({"response": SecurityUtils.escape_html(response)})

    except Exception as e:
        print(f"Conversation error: {str(e)}")
        error_msg = SecurityUtils.get_safe_error_message(e)
        return jsonify({"error": f"会話処理中にエラーが発生しました: {error_msg}"}), 500


@scenario_bp.route("/api/scenario_clear", methods=["POST"])
def clear_scenario_history():
    """特定のシナリオの履歴をクリアする"""
    try:
        data = request.json
        if not data or "scenario_id" not in data:
            return jsonify({"error": "シナリオIDが必要です"}), 400

        scenario_id = data["scenario_id"]
        if not scenario_service.get_scenario_by_id(scenario_id):
            return jsonify({"error": "無効なシナリオIDです"}), 400

        clear_session_history("scenario_history", scenario_id)

        return jsonify({"status": "success", "message": "シナリオ履歴がクリアされました"})

    except Exception as e:
        print(f"Error clearing scenario history: {str(e)}")
        return (
            jsonify(
                {"error": f"履歴のクリアに失敗しました: {SecurityUtils.get_safe_error_message(e)}"}
            ),
            500,
        )


@scenario_bp.route("/api/scenario_feedback", methods=["POST"])
def get_scenario_feedback() -> Response:
    """シナリオの会話履歴に基づくフィードバックを生成"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        scenario_id = data.get("scenario_id")
        selected_model = data.get("model")

        scenario_data = scenario_service.get_scenario_by_id(scenario_id)
        if not scenario_data:
            return jsonify({"error": "無効なシナリオIDです"}), 400

        if (
            "scenario_history" not in session
            or scenario_id not in session["scenario_history"]
        ):
            return jsonify({"error": "会話履歴が見つかりません"}), 404

        history = session["scenario_history"][scenario_id]

        is_reverse_role = scenario_data.get("role_type") == "reverse"

        # フィードバックプロンプトを構築（サービス層を使用）
        from services.feedback_service import get_feedback_service

        feedback_service = get_feedback_service()

        feedback_prompt = feedback_service.build_scenario_feedback_prompt(
            history, scenario_data, is_reverse_role
        )

        try:
            (
                feedback_content,
                used_model,
                error_msg,
            ) = feedback_service.try_multiple_models_for_prompt(
                feedback_prompt, selected_model
            )

            if error_msg is None:
                response_data = {
                    "feedback": feedback_content,
                    "scenario": scenario_data.get("title", "無題のシナリオ"),
                    "model_used": used_model,
                }

                # 強み分析を追加（サービス層を使用）
                from services.strength_service import get_strength_service

                strength_service = get_strength_service()
                response_data = strength_service.update_feedback_with_strength_analysis(
                    response_data, "scenario", scenario_id
                )

                return jsonify(response_data)
            else:
                if error_msg == "RATE_LIMIT_EXCEEDED":
                    return (
                        jsonify(
                            {
                                "error": "アクセスが集中しています。しばらくしてからお試しください。",
                                "attempted_models": "Gemini",
                                "retry_after": 60,
                            }
                        ),
                        429,
                    )
                else:
                    safe_message = SecurityUtils.get_safe_error_message(
                        Exception(error_msg)
                    )
                    return (
                        jsonify(
                            {
                                "error": f"フィードバックの生成に失敗しました: {safe_message}",
                                "attempted_models": "Gemini",
                            }
                        ),
                        503,
                    )

        except Exception as e:
            print(f"Feedback generation error: {str(e)}")
            import traceback

            traceback.print_exc()
            return jsonify({"error": f"フィードバックの生成中にエラーが発生しました: {str(e)}"}), 500

    except Exception as e:
        print(f"Scenario feedback error: {str(e)}")
        return jsonify({"error": f"フィードバック処理中にエラーが発生しました: {str(e)}"}), 500


@scenario_bp.route("/api/categorized_scenarios")
@with_error_handling
def get_categorized_scenarios_api():
    """カテゴリ分けされたシナリオ一覧をJSON形式で返す"""
    scenario_summary = scenario_service.get_scenario_category_summary()
    return jsonify(scenario_summary)


@scenario_bp.route("/api/scenario/<scenario_id>/category")
@with_error_handling
def get_scenario_category(scenario_id):
    """指定シナリオのカテゴリを返す"""
    if not scenario_service.get_scenario_by_id(scenario_id):
        raise NotFoundError("シナリオ", scenario_id)

    is_harassment = scenario_service.is_harassment_scenario(scenario_id)
    category = "harassment_prevention" if is_harassment else "regular_communication"

    return jsonify(
        {
            "scenario_id": scenario_id,
            "category": category,
            "requires_consent": is_harassment,
        }
    )


@scenario_bp.route("/api/get_assist", methods=["POST"])
@with_error_handling
def get_assist() -> Any:
    """AIアシストの提案を取得するエンドポイント"""
    data = request.get_json()
    scenario_id = data.get("scenario_id")
    current_context = data.get("current_context", "")

    if not scenario_id:
        raise ValidationError("シナリオIDが必要です")

    scenario = scenario_service.get_scenario_by_id(scenario_id)
    if not scenario:
        raise NotFoundError("シナリオ", scenario_id)

    assist_prompt = f"""
現在のシナリオ: {scenario.get('title', '無題のシナリオ')}
状況: {scenario.get('description', '説明なし')}
学習ポイント: {', '.join(scenario.get('learning_points', []))}

現在の会話:
{current_context}

上記の状況で、適切な返答のヒントを1-2文で簡潔に提案してください。
"""

    selected_model = session.get("selected_model", DEFAULT_MODEL)

    from app import create_model_and_get_response

    suggestion = create_model_and_get_response(selected_model, assist_prompt)
    return jsonify({"suggestion": suggestion})
