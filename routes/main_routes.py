"""
Main routes for the workplace-roleplay application.
Handles home page, health check, and basic pages.
"""

import os
from datetime import datetime
from typing import Any, Dict

from config.feature_flags import get_feature_flags
from flask import Blueprint, Flask, Response, current_app, render_template, send_from_directory

from config import get_cached_config
from errors import secure_error_handler

# Blueprint作成
main_bp = Blueprint("main", __name__)

# 設定の取得
config = get_cached_config()


def get_all_available_models() -> Dict[str, Any]:
    """
    すべての利用可能なモデルを取得し、カテゴリ別に整理する

    Returns:
        Dict[str, Any]: カテゴリ別モデルのマップと、全モデルリスト
    """
    try:
        import google.generativeai as genai

        # Gemini APIの設定を確認
        api_key = config.GOOGLE_API_KEY
        if not api_key:
            print("Warning: GOOGLE_API_KEY is not set")
            return _get_fallback_models()

        # 利用可能なモデルを取得
        genai.configure(api_key=api_key)
        models = genai.list_models()

        # Geminiモデルをフィルタリング
        gemini_models = []
        for model in models:
            if "gemini" in model.name.lower():
                model_short_name = model.name.split("/")[-1]
                model_name = f"gemini/{model_short_name}"
                gemini_models.append(model_name)

        # 文字列リストから辞書リストに変換
        model_dicts = []
        for model_id in gemini_models:
            model_dicts.append({"id": model_id, "name": model_id.split("/")[-1], "provider": "gemini"})

        return {"models": model_dicts, "categories": {"gemini": model_dicts}}
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        return _get_fallback_models()


def _get_fallback_models() -> Dict[str, Any]:
    """フォールバック用のモデルリストを返す"""
    basic_models = [
        {"id": "gemini/gemini-1.5-pro", "name": "gemini-1.5-pro", "provider": "gemini"},
        {
            "id": "gemini/gemini-1.5-flash",
            "name": "gemini-1.5-flash",
            "provider": "gemini",
        },
    ]
    return {"models": basic_models, "categories": {"gemini": basic_models}}


@main_bp.route("/health")
@secure_error_handler
def health_check() -> Response:
    """ヘルスチェックエンドポイント"""
    from flask import jsonify

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "checks": {"database": "N/A", "llm": "ready"},  # DBを使用していない
    }
    return jsonify(health_status), 200


@main_bp.route("/api/metrics")
@secure_error_handler
def get_performance_metrics() -> Response:
    """
    パフォーマンスメトリクスを取得
    ---
    tags:
      - health
    responses:
      200:
        description: パフォーマンスメトリクス
    """
    from flask import jsonify

    try:
        from utils.performance import (
            get_metrics,
            get_scenario_cache,
            get_prompt_cache,
            get_business_metrics,
        )

        # パフォーマンスメトリクス
        perf_metrics = get_metrics().get_metrics()

        # ビジネスメトリクス
        business_metrics = get_business_metrics().get_summary()

        # キャッシュ統計
        cache_stats = {
            "scenario_cache": get_scenario_cache().stats(),
            "prompt_cache": get_prompt_cache().stats(),
        }

        return (
            jsonify(
                {
                    "performance": perf_metrics,
                    "business": business_metrics,
                    "caches": cache_stats,
                }
            ),
            200,
        )
    except ImportError:
        return jsonify({"error": "Performance metrics not available"}), 503


@main_bp.route("/")
def index() -> str:
    """トップページ"""
    # 共通関数を使用してモデル情報を取得
    model_info = get_all_available_models()
    available_models = model_info["models"]

    # モデル選択機能の有効/無効を制御するフラグ
    enable_model_selection = os.getenv("ENABLE_MODEL_SELECTION", "true").lower() == "true"

    return render_template(
        "index.html",
        models=available_models,
        enable_model_selection=enable_model_selection,
    )


@main_bp.route("/chat")
def chat_page() -> str:
    """自由会話ページ"""
    feature_flags = get_feature_flags()
    return render_template(
        "chat.html",
        default_model=config.DEFAULT_MODEL,
        feature_flags=feature_flags.to_dict(),
    )


@main_bp.route("/favicon.ico")
def favicon() -> Response:
    """ファビコンを返す（存在する場合）"""
    try:
        return send_from_directory(
            os.path.join(current_app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )
    except Exception:
        # favicon.icoが存在しない場合は204 No Contentを返す
        return "", 204


# カスタムJinjaフィルターの登録関数
def register_template_filters(app: Flask) -> None:
    """テンプレートフィルターを登録"""

    @app.template_filter("datetime")
    def format_datetime(value: Any) -> str:
        """ISO形式の日時文字列をより読みやすい形式に変換"""
        if not value:
            return "なし"
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime("%Y年%m月%d日 %H:%M")
        except (ValueError, TypeError):
            return str(value)
