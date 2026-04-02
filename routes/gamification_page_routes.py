"""
ゲーミフィケーション・ダッシュボード画面
"""

from __future__ import annotations

from flask import Blueprint, render_template

from config.feature_flags import get_feature_flags

gamification_page_bp = Blueprint("gamification_page", __name__)


@gamification_page_bp.route("/gamification")
def gamification_dashboard():
    """学習ダッシュボード（XP・クエスト・分析・エクスポート）"""
    feature_flags = get_feature_flags()
    return render_template(
        "gamification.html",
        feature_flags=feature_flags.to_dict(),
    )
