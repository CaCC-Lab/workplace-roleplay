"""
Journal (learning history) routes for the workplace-roleplay application.
Handles learning history display.
"""

from datetime import datetime

from config.feature_flags import require_feature
from flask import Blueprint, render_template, session

from scenarios import load_scenarios

# Blueprint作成
journal_bp = Blueprint("journal", __name__)

# シナリオをロード
try:
    scenarios = load_scenarios()
except Exception as e:
    print(f"❌ シナリオロードエラー (journal_routes): {e}")
    scenarios = {}


@journal_bp.route("/journal")
@require_feature("learning_history")
def view_journal():
    """学習履歴ページ"""
    # 履歴データを取得
    scenario_history = {}

    # セッションから各シナリオの履歴を取得
    if "scenario_history" in session:
        for scenario_id, history in session["scenario_history"].items():
            if scenario_id in scenarios and history:
                scenario_info = scenarios.get(scenario_id, {})
                scenario_history[scenario_id] = {
                    "title": scenario_info.get("title", "不明なシナリオ"),
                    "last_session": history[-1].get("timestamp") if history else None,
                    "sessions_count": len(history),
                    "feedback": session.get("scenario_feedback", {}).get(scenario_id),
                }

    # 雑談履歴の取得
    chat_history = []
    if "chat_history" in session:
        chat_history = session["chat_history"]

    # 最終アクティビティの日時を計算
    last_activity = None

    # シナリオ履歴から最新の日時を確認
    for scenario_data in scenario_history.values():
        if scenario_data.get("last_session"):
            if not last_activity or scenario_data["last_session"] > last_activity:
                last_activity = scenario_data["last_session"]

    # チャット履歴からも確認
    if chat_history and len(chat_history) > 0:
        chat_last = chat_history[-1].get("timestamp")
        if chat_last:
            if not last_activity or chat_last > last_activity:
                last_activity = chat_last

    # 実際の練習時間を計算
    total_minutes = 0

    # シナリオの練習時間計算
    if "scenario_settings" in session:
        scenario_settings = session["scenario_settings"]
        for scenario_id, settings in scenario_settings.items():
            if scenario_id in session.get("scenario_history", {}) and session["scenario_history"][scenario_id]:
                start_time = datetime.fromisoformat(settings.get("start_time", datetime.now().isoformat()))
                last_msg_time = datetime.fromisoformat(
                    session["scenario_history"][scenario_id][-1].get("timestamp", datetime.now().isoformat())
                )
                time_diff = (last_msg_time - start_time).total_seconds() / 60
                total_minutes += time_diff

    # 雑談モードの練習時間計算
    if "chat_settings" in session and "chat_history" in session and session["chat_history"]:
        chat_settings = session["chat_settings"]
        start_time = datetime.fromisoformat(chat_settings.get("start_time", datetime.now().isoformat()))
        last_msg_time = datetime.fromisoformat(session["chat_history"][-1].get("timestamp", datetime.now().isoformat()))
        time_diff = (last_msg_time - start_time).total_seconds() / 60
        total_minutes += time_diff

    # 観戦モードの練習時間計算
    if "watch_settings" in session and "watch_history" in session and session["watch_history"]:
        watch_settings = session["watch_settings"]
        start_time = datetime.fromisoformat(watch_settings.get("start_time", datetime.now().isoformat()))
        last_msg_time = datetime.fromisoformat(
            session["watch_history"][-1].get("timestamp", datetime.now().isoformat())
        )
        time_diff = (last_msg_time - start_time).total_seconds() / 60
        total_minutes += time_diff

    # 時間と分に変換
    total_minutes = round(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    # 練習時間の文字列を構築
    if hours > 0:
        total_practice_time = f"{hours}時間{minutes}分"
    else:
        total_practice_time = f"{minutes}分"

    if total_minutes == 0:
        total_practice_time = "まだ記録がありません"

    return render_template(
        "journal.html",
        scenario_history=scenario_history,
        chat_history=chat_history,
        last_activity=last_activity,
        total_practice_time=total_practice_time,
    )
