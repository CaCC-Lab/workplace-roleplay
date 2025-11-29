"""
Chat routes for the workplace-roleplay application.
Handles chat API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from config.feature_flags import get_feature_flags
from flask import Blueprint, Response, jsonify, request, session
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from config import get_cached_config
from errors import ValidationError, secure_error_handler, with_error_handling

# セキュリティ関連のインポート
try:
    from utils.security import SecurityUtils
except ImportError:

    class SecurityUtils:
        @staticmethod
        def sanitize_input(text):
            return text

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


# サービス層のインポート
from services.feedback_service import get_feedback_service

from utils.helpers import (
    add_messages_from_history,
    add_to_session_history,
    clear_session_history,
    extract_content,
    format_conversation_history_for_feedback,
    get_partner_description,
    get_situation_description,
    get_topic_description,
    initialize_session_history,
    set_session_start_time,
)

# Blueprint作成
chat_bp = Blueprint("chat", __name__)

# 設定の取得
config = get_cached_config()
DEFAULT_MODEL = config.DEFAULT_MODEL


def _get_llm_and_invoke(model_name: str, messages: List[BaseMessage]) -> str:
    """
    LLMを初期化して応答を取得するヘルパー関数
    """
    # app.pyの関数をインポート（循環参照を避けるためここでインポート）
    from app import extract_content as app_extract_content
    from app import initialize_llm

    llm = initialize_llm(model_name)
    response = llm.invoke(messages)
    return app_extract_content(response)


@chat_bp.route("/api/chat", methods=["POST"])
def handle_chat() -> Response:
    """チャットメッセージの処理"""
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

    # 会話履歴の取得と更新
    initialize_session_history("chat_history")

    # メッセージリストの作成
    messages: List[BaseMessage] = []
    messages.append(SystemMessage(content=system_prompt))

    # 履歴からメッセージを構築
    add_messages_from_history(messages, session["chat_history"])

    # 新しいメッセージを追加
    messages.append(HumanMessage(content=message))

    try:
        ai_message = _get_llm_and_invoke(model_name, messages)

        # 会話履歴の更新
        add_to_session_history("chat_history", {"human": message, "ai": ai_message})

        return jsonify({"response": SecurityUtils.escape_html(ai_message)})
    except Exception as e:
        raise e


@chat_bp.route("/api/start_chat", methods=["POST"])
@secure_error_handler
def start_chat() -> Response:
    """雑談練習を開始するAPI"""
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
            "start_time": datetime.now().isoformat(),
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
- 感情表現を（）内に適度に含めてください""",
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
            from app import create_model_and_get_response

            response = create_model_and_get_response(model_name, first_prompt)

            # 履歴に保存
            add_to_session_history("chat_history", {"human": "[雑談開始]", "ai": response})

            return jsonify({"response": response})

        except Exception as e:
            from errors import RateLimitError, handle_llm_specific_error

            app_error = handle_llm_specific_error(e, "Gemini")
            if isinstance(app_error, RateLimitError):
                return jsonify({"error": app_error.message, "retry_after": 60}), 429
            else:
                add_to_session_history(
                    "chat_history",
                    {"human": "[雑談開始]", "ai": f"申し訳ありません。{app_error.message}"},
                )
                return jsonify({"error": app_error.message}), app_error.status_code

    except Exception as e:
        print(f"Error in start_chat: {str(e)}")
        return (
            jsonify(
                {"error": f"雑談開始に失敗しました: {SecurityUtils.get_safe_error_message(e)}"}
            ),
            500,
        )


@chat_bp.route("/api/clear_history", methods=["POST"])
def clear_history() -> Response:
    """会話履歴をクリアするAPI"""
    try:
        if request.json is None:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        mode = request.json.get("mode", "scenario")

        if mode == "chat":
            clear_session_history("chat_history")
            if "chat_settings" in session:
                session.pop("chat_settings", None)
                session.modified = True
        elif mode == "watch":
            clear_session_history("watch_history")
            if "watch_settings" in session:
                session.pop("watch_settings", None)
                session.modified = True
        else:
            # シナリオモードの履歴クリア
            selected_model = request.json.get("model", "llama2")
            scenario_id = request.json.get("scenario_id")

            if scenario_id:
                clear_session_history("scenario_history", scenario_id)
            else:
                if (
                    "conversation_history" in session
                    and selected_model in session["conversation_history"]
                ):
                    session["conversation_history"][selected_model] = []
                    session.modified = True

        return jsonify({"status": "success", "message": "会話履歴がクリアされました"})

    except Exception as e:
        print(f"Error in clear_history: {str(e)}")
        return jsonify({"status": "error", "message": f"履歴のクリアに失敗しました: {str(e)}"}), 500


@chat_bp.route("/api/chat_feedback", methods=["POST"])
def get_chat_feedback() -> Response:
    """雑談練習のフィードバックを生成（ユーザーの発言に焦点を当てる）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        selected_model = data.get("model")

        # 会話履歴の取得
        if "chat_history" not in session:
            return jsonify({"error": "会話履歴が見つかりません"}), 404

        # フィードバックプロンプトを構築（サービス層を使用）
        feedback_service = get_feedback_service()
        feedback_prompt = feedback_service.build_chat_feedback_prompt(
            session["chat_history"],
            data.get("partner_type", "colleague"),
            data.get("situation", "break"),
        )

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
                "model_used": used_model,
                "status": "success",
            }

            # 強み分析を追加（サービス層を使用）
            from services.strength_service import get_strength_service

            strength_service = get_strength_service()
            response_data = strength_service.update_feedback_with_strength_analysis(
                response_data, "chat"
            )

            return jsonify(response_data)
        else:
            if error_msg == "RATE_LIMIT_EXCEEDED":
                return (
                    jsonify(
                        {
                            "error": "現在、アクセスが集中しているため、フィードバックを生成できませんでした。",
                            "attempted_models": "Gemini",
                            "retry_after": 60,
                            "status": "error",
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
                            "status": "error",
                        }
                    ),
                    503,
                )

    except Exception as e:
        print(f"Error in chat_feedback: {str(e)}")
        import traceback

        traceback.print_exc()
        return (
            jsonify({"error": f"フィードバックの生成中にエラーが発生しました: {str(e)}", "status": "error"}),
            500,
        )


@chat_bp.route("/api/conversation_history", methods=["POST"])
@with_error_handling
def get_conversation_history() -> Response:
    """会話履歴を取得するAPI"""
    data = request.get_json()
    history_type = data.get("type")

    if history_type == "scenario":
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            raise ValidationError("シナリオIDが必要です")

        if (
            "scenario_history" not in session
            or scenario_id not in session["scenario_history"]
        ):
            return jsonify({"history": []})

        return jsonify({"history": session["scenario_history"][scenario_id]})

    elif history_type == "chat":
        if "chat_history" not in session:
            return jsonify({"history": []})

        return jsonify({"history": session["chat_history"]})

    elif history_type == "watch":
        if "watch_history" not in session:
            return jsonify({"history": []})

        watch_history = []
        for entry in session["watch_history"]:
            watch_history.append(
                {
                    "timestamp": entry.get("timestamp"),
                    "human" if entry["speaker"] == "A" else "ai": entry["message"],
                }
            )

        return jsonify({"history": watch_history})

    else:
        raise ValidationError("不明な履歴タイプです")
