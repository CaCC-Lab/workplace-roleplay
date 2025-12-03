"""
Watch mode routes for the workplace-roleplay application.
Handles AI conversation observation functionality.
"""

from datetime import datetime
from typing import Any

from config.feature_flags import get_feature_flags
from flask import Blueprint, jsonify, render_template, request, session

from config import get_cached_config
from errors import ExternalAPIError, secure_error_handler

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
        def get_safe_error_message(e):
            return str(e)


# サービス層のインポート
from services.watch_service import get_watch_service

from utils.helpers import (
    clear_session_history,
)

# Blueprint作成
watch_bp = Blueprint("watch", __name__)

# 設定の取得
config = get_cached_config()
DEFAULT_MODEL = config.DEFAULT_MODEL


# サービス層を使用するため、関数を削除（watch_serviceに移動済み）


@watch_bp.route("/watch")
def watch_mode():
    """観戦モードページ"""
    feature_flags = get_feature_flags()
    return render_template("watch.html", feature_flags=feature_flags.to_dict())


@watch_bp.route("/api/watch/start", methods=["POST"])
@secure_error_handler
def start_watch():
    """会話観戦モードの開始"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        model_a = data.get("model_a")
        model_b = data.get("model_b")

        if not SecurityUtils.validate_model_name(model_a):
            return jsonify({"error": "無効なモデルA名です"}), 400
        if not SecurityUtils.validate_model_name(model_b):
            return jsonify({"error": "無効なモデルB名です"}), 400

        partner_type = SecurityUtils.sanitize_input(data.get("partner_type", ""))
        situation = SecurityUtils.sanitize_input(data.get("situation", ""))
        topic = SecurityUtils.sanitize_input(data.get("topic", ""))

        # セッションの初期化
        clear_session_history("watch_history")
        session["watch_settings"] = {
            "model_a": model_a,
            "model_b": model_b,
            "partner_type": partner_type,
            "situation": situation,
            "topic": topic,
            "current_speaker": "A",
            "start_time": datetime.now().isoformat(),
        }
        session.modified = True

        try:
            from app import initialize_llm

            watch_service = get_watch_service()
            llm = initialize_llm(model_a)
            initial_message = watch_service.generate_initial_message(llm, partner_type, situation, topic)

            session["watch_history"] = [
                {
                    "speaker": "A",
                    "message": initial_message,
                    "timestamp": datetime.now().isoformat(),
                }
            ]

            return jsonify({"message": f"太郎: {initial_message}"})

        except Exception as e:
            print(f"Error in watch initialization: {str(e)}")
            raise ExternalAPIError(service="LLM", message="観戦の初期化に失敗しました")

    except Exception as e:
        print(f"Error in start_watch: {str(e)}")
        return (
            jsonify({"error": f"観戦モードの開始に失敗しました: {SecurityUtils.get_safe_error_message(e)}"}),
            500,
        )


@watch_bp.route("/api/watch/next", methods=["POST"])
@secure_error_handler
def next_watch_message() -> Any:
    """次の発言を生成"""
    try:
        if "watch_settings" not in session:
            return jsonify({"error": "観戦セッションが初期化されていません"}), 400

        settings = session["watch_settings"]
        history = session["watch_history"]

        watch_service = get_watch_service()
        current_speaker = settings["current_speaker"]
        next_speaker = watch_service.switch_speaker(current_speaker)
        model = settings["model_b"] if next_speaker == "B" else settings["model_a"]
        display_name = watch_service.get_speaker_display_name(next_speaker)

        try:
            from app import initialize_llm
            from errors import handle_llm_specific_error

            try:
                llm = initialize_llm(model)
                next_message = watch_service.generate_next_message(llm, history)
            except Exception as e:
                app_error = handle_llm_specific_error(e, model)
                return jsonify({"error": app_error.message}), app_error.status_code

            history.append(
                {
                    "speaker": next_speaker,
                    "message": next_message,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            settings["current_speaker"] = next_speaker
            session.modified = True

            return jsonify({"message": f"{display_name}: {next_message}"})

        except Exception as e:
            print(f"Error generating next message: {str(e)}")
            raise ExternalAPIError(service="LLM", message="メッセージの生成に失敗しました")

    except Exception as e:
        print(f"Error in next_watch_message: {str(e)}")
        return (
            jsonify({"error": f"次のメッセージ生成に失敗しました: {SecurityUtils.get_safe_error_message(e)}"}),
            500,
        )
