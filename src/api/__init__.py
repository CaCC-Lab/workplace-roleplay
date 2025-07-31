"""APIモジュール"""
from flask import Blueprint


def create_api_blueprint() -> Blueprint:
    """APIブループリントを作成"""
    from . import chat, models, scenarios, recommendations, security, async_scenario, scenarios_list
    
    # ブループリントの作成
    api_bp = Blueprint("api", __name__)
    
    # 子ブループリントの登録
    api_bp.register_blueprint(async_scenario.bp)
    
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
    
    api_bp.add_url_rule(
        "/scenarios",
        view_func=scenarios_list.get_paginated_scenarios,
        methods=["GET"]
    )
    
    api_bp.add_url_rule(
        "/scenario-tags",
        view_func=scenarios_list.get_scenario_tags,
        methods=["GET"]
    )
    
    return api_bp


__all__ = ["create_api_blueprint"]