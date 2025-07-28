"""APIモジュール"""
from flask import Blueprint


def create_api_blueprint() -> Blueprint:
    """APIブループリントを作成"""
    from . import chat, models, scenarios, recommendations, security
    
    # ブループリントの作成
    api_bp = Blueprint("api", __name__)
    
    # ルートの登録
    api_bp.add_url_rule(
        "/models",
        view_func=models.get_models,
        methods=["GET"]
    )
    
    api_bp.add_url_rule(
        "/chat",
        view_func=chat.chat,
        methods=["POST"]
    )
    
    api_bp.add_url_rule(
        "/scenarios/<scenario_id>/chat",
        view_func=scenarios.scenario_chat,
        methods=["POST"]
    )
    
    api_bp.add_url_rule(
        "/scenarios/<scenario_id>/feedback",
        view_func=scenarios.scenario_feedback,
        methods=["POST"]
    )
    
    api_bp.add_url_rule(
        "/recommended_scenarios",
        view_func=recommendations.get_recommended_scenarios,
        methods=["GET"]
    )
    
    api_bp.add_url_rule(
        "/csrf-token",
        view_func=security.get_csrf_token,
        methods=["GET"]
    )
    
    return api_bp


__all__ = ["create_api_blueprint"]