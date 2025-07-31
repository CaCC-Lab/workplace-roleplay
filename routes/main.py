"""
メインルートのBlueprintモジュール
"""
from flask import Blueprint, render_template, session, g, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from scenarios import load_scenarios
from services.llm_service import LLMService
from services.analytics_service import AnalyticsService
from services.journal_service import JournalService


main_bp = Blueprint('main', __name__)

# サービスのインスタンス
llm_service = LLMService()
analytics_service = AnalyticsService()
journal_service = JournalService()

# シナリオデータの読み込み
SCENARIOS = load_scenarios()


@main_bp.before_request
def load_logged_in_user():
    """各リクエスト前にログインユーザーを読み込む"""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        from models import User
        g.user = User.query.get(user_id)


@main_bp.route("/")
def index():
    """ホームページ"""
    return render_template("index.html", user=current_user)


@main_bp.route("/chat")
def chat():
    """雑談練習ページ"""
    return render_template("chat.html")


@main_bp.route("/scenarios")
def list_scenarios():
    """シナリオ一覧ページ"""
    # カテゴリごとにシナリオを整理
    categorized_scenarios = {}
    for scenario_id, scenario in SCENARIOS.items():
        category = scenario.get("category", "その他")
        if category not in categorized_scenarios:
            categorized_scenarios[category] = []
        
        scenario_info = {
            "id": scenario_id,
            "title": scenario["title"],
            "difficulty": scenario.get("difficulty", "中級"),
            "description": scenario.get("description", ""),
            "tags": scenario.get("tags", [])
        }
        categorized_scenarios[category].append(scenario_info)
    
    # カテゴリ内でタイトル順にソート
    for category in categorized_scenarios:
        categorized_scenarios[category].sort(key=lambda x: x["title"])
    
    return render_template(
        "scenarios.html",
        categorized_scenarios=categorized_scenarios
    )


@main_bp.route("/scenario/<scenario_id>")
def show_scenario(scenario_id):
    """個別シナリオページ"""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return render_template("errors/404.html"), 404
    
    # 進捗情報を取得
    progress = None
    if current_user.is_authenticated:
        progress = analytics_service.get_scenario_progress(
            current_user.id, scenario_id
        )
    
    return render_template(
        "scenario.html",
        scenario=scenario,
        scenario_id=scenario_id,
        progress=progress
    )


@main_bp.route("/watch")
def watch_mode():
    """観戦モードページ"""
    return render_template("watch.html")


@main_bp.route("/journal")
@login_required
def view_journal():
    """学習履歴ページ"""
    # ユーザーの学習履歴を取得
    user_history = journal_service.get_user_history(current_user.id)
    
    # 統計情報を計算
    stats = journal_service.calculate_user_stats(user_history)
    
    # 最近の活動を取得
    recent_activities = journal_service.get_recent_activities(
        current_user.id, limit=10
    )
    
    return render_template(
        "journal.html",
        history=user_history,
        stats=stats,
        recent_activities=recent_activities
    )


@main_bp.route("/analytics")
@login_required
def analytics_dashboard():
    """分析ダッシュボードページ"""
    # ユーザーの分析データを取得
    user_analytics = analytics_service.get_user_analytics(current_user.id)
    
    # 進捗サマリーを取得
    progress_summary = analytics_service.get_progress_summary(current_user.id)
    
    # スキル評価を取得
    skill_assessment = analytics_service.get_skill_assessment(current_user.id)
    
    return render_template(
        "analytics.html",
        analytics=user_analytics,
        progress_summary=progress_summary,
        skill_assessment=skill_assessment
    )


@main_bp.route("/breathing")
def breathing_guide():
    """呼吸法ガイドページ"""
    return render_template("breathing.html")


@main_bp.route("/ambient")
def ambient_sounds():
    """環境音ページ"""
    return render_template("ambient.html")


@main_bp.route("/growth")
@login_required
def growth_tracker():
    """成長トラッカーページ"""
    # ユーザーの成長データを取得
    growth_data = analytics_service.get_growth_data(current_user.id)
    
    # マイルストーンを取得
    milestones = analytics_service.get_milestones(current_user.id)
    
    # 推奨事項を取得
    recommendations = analytics_service.get_recommendations(current_user.id)
    
    return render_template(
        "growth.html",
        growth_data=growth_data,
        milestones=milestones,
        recommendations=recommendations
    )


@main_bp.route("/strength_analysis")
def strength_analysis_page():
    """強み分析ページ"""
    return render_template("strength_analysis.html")


# API関連のエンドポイント

@main_bp.route("/api/models", methods=["GET"])
def api_models():
    """利用可能なモデルのリストを返すAPI"""
    try:
        models = llm_service.get_all_available_models()
        selected_model = session.get("selected_model", "gemini-1.5-flash")
        
        return jsonify({
            "models": models,
            "selected": selected_model
        })
    except Exception as e:
        return jsonify({
            "error": f"モデルリストの取得に失敗しました: {str(e)}",
            "models": [],
            "selected": "gemini-1.5-flash"
        }), 500


@main_bp.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """CSRFトークンを取得するAPI"""
    from utils.security import CSRFToken
    return jsonify({"csrf_token": CSRFToken.generate()})


@main_bp.route("/api/session/health", methods=["GET"])
def session_health_check():
    """セッションの健全性をチェックするAPI"""
    try:
        session_type = session.get("_session_type", "unknown")
        session_id = session.get("session_id", "unknown")
        
        # セッションの統計情報
        chat_history_count = len(session.get("chat_history", []))
        scenario_count = len(session.get("scenario_histories", {}))
        watch_history_count = len(session.get("watch_history", []))
        
        health_info = {
            "status": "healthy",
            "session_type": session_type,
            "session_id": session_id,
            "statistics": {
                "chat_messages": chat_history_count,
                "scenario_sessions": scenario_count,
                "watch_messages": watch_history_count
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(health_info)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@main_bp.route("/api/session/info", methods=["GET"])
def session_info():
    """セッション情報を取得するAPI"""
    try:
        info = {
            "session_id": session.get("session_id", "unknown"),
            "user_id": session.get("user_id"),
            "selected_model": session.get("selected_model", "gemini-1.5-flash"),
            "chat_settings": session.get("chat_settings", {}),
            "watch_settings": session.get("watch_settings", {}),
            "created_at": session.get("created_at", datetime.now().isoformat())
        }
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({"error": f"セッション情報の取得に失敗しました: {str(e)}"}), 500