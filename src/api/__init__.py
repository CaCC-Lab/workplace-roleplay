"""APIモジュール"""
from flask import Blueprint


def create_api_blueprint() -> Blueprint:
    """APIブループリントを作成"""
    from . import chat, models, scenarios
    
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
    
    return api_bp


__all__ = ["create_api_blueprint"]