"""
Strength analysis routes for the workplace-roleplay application.
Handles strength analysis API endpoints.
"""

import random
from datetime import datetime

from config.feature_flags import is_strength_analysis_enabled
from flask import Blueprint, jsonify, render_template, request, session

from errors import secure_error_handler

# 強み分析関連のインポート
from strength_analyzer import (
    analyze_user_strengths,
    generate_encouragement_messages,
    get_top_strengths,
)
from utils.helpers import format_conversation_history

# セキュリティ関連のインポート
try:
    from utils.security import SecurityUtils
except ImportError:

    class SecurityUtils:
        @staticmethod
        def get_safe_error_message(e):
            return str(e)


# Blueprint作成
strength_bp = Blueprint("strength", __name__)


@strength_bp.route("/strength_analysis")
def strength_analysis_page():
    """強み分析ページを表示"""
    if not is_strength_analysis_enabled():
        return render_template(
            "feature_disabled.html", feature_name="強み分析", message="強み分析機能は現在無効化されています。"
        )

    return render_template("strength_analysis.html")


@strength_bp.route("/api/strength_analysis", methods=["POST"])
@secure_error_handler
def analyze_strengths():
    """会話履歴から強みを分析"""
    if not is_strength_analysis_enabled():
        return (
            jsonify({"error": "Feature disabled", "message": "強み分析機能は現在無効化されています。"}),
            403,
        )

    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400

        session_type = data.get("type", "chat")
        scenario_id = data.get("scenario_id")

        # 会話履歴を取得
        if session_type == "chat":
            history = session.get("chat_history", [])
        elif session_type == "scenario":
            if not scenario_id:
                return jsonify({"error": "シナリオIDが必要です"}), 400
            elif scenario_id == "all":
                scenario_histories = session.get("scenario_history", {})
                history = []
                for sid, scenario_history in scenario_histories.items():
                    history.extend(scenario_history)
            else:
                history = session.get("scenario_history", {}).get(scenario_id, [])
        else:
            return jsonify({"error": f"不明なセッションタイプ: {session_type}"}), 400

        if not history:
            return jsonify(
                {
                    "scores": {
                        key: 50
                        for key in [
                            "empathy",
                            "clarity",
                            "active_listening",
                            "adaptability",
                            "positivity",
                            "professionalism",
                        ]
                    },
                    "messages": ["まだ練習履歴がありません。会話を始めてみましょう！"],
                    "history": [],
                }
            )

        # 会話履歴をフォーマット
        formatted_history = format_conversation_history(history)

        # 強み分析を実行
        scores = analyze_user_strengths(formatted_history)

        # セッションに保存される強み履歴を更新
        if "strength_history" not in session:
            session["strength_history"] = {}

        if session_type not in session["strength_history"]:
            session["strength_history"][session_type] = []

        # 新しい分析結果を追加
        session["strength_history"][session_type].append(
            {
                "timestamp": datetime.now().isoformat(),
                "scores": scores,
                "practice_count": len(session["strength_history"][session_type]) + 1,
            }
        )

        # 最大20件まで保持
        if len(session["strength_history"][session_type]) > 20:
            session["strength_history"][session_type] = session["strength_history"][
                session_type
            ][-20:]

        session.modified = True

        # 励ましメッセージを生成
        messages = generate_encouragement_messages(
            scores, session["strength_history"][session_type][:-1]
        )

        # パーソナライズされたメッセージを追加
        if messages and len(messages) < 3:
            top_strength = get_top_strengths(scores, 1)[0]
            additional_messages = [
                f"{top_strength['name']}の才能が光っています！この強みを活かしてさらに成長しましょう。",
                f"素晴らしい{top_strength['name']}ですね！次回はさらに磨きをかけていきましょう。",
                f"{top_strength['name']}が{top_strength['score']}点！あなたの強みを自信にして前進しましょう。",
            ]
            messages.append(random.choice(additional_messages))

        return jsonify(
            {
                "scores": scores,
                "messages": messages,
                "history": session["strength_history"][session_type],
                "model_used": "simple_analyzer",
            }
        )

    except Exception as e:
        print(f"Error in analyze_strengths: {str(e)}")
        return (
            jsonify(
                {"error": f"強み分析に失敗しました: {SecurityUtils.get_safe_error_message(e)}"}
            ),
            500,
        )


def update_feedback_with_strength_analysis(
    feedback_response, session_type, scenario_id=None
):
    """
    既存のフィードバックレスポンスに強み分析を追加するヘルパー関数
    """
    try:
        # 会話履歴を取得
        if session_type == "chat":
            history = session.get("chat_history", [])
        else:
            history = session.get("scenario_history", {}).get(scenario_id, [])

        if history:
            # 強み分析を実行
            formatted_history = format_conversation_history(history)
            scores = analyze_user_strengths(formatted_history)

            # トップ3の強みを取得
            top_strengths = get_top_strengths(scores, 3)

            # フィードバックレスポンスに追加
            feedback_response["strength_analysis"] = {
                "scores": scores,
                "top_strengths": top_strengths,
            }
    except Exception as e:
        print(f"Error adding strength analysis to feedback: {str(e)}")

    return feedback_response
