"""モデル管理API"""
from flask import current_app, jsonify
from typing import Dict, Any


def get_models() -> tuple[Dict[str, Any], int]:
    """利用可能なモデル一覧を返す
    
    Returns:
        モデル情報とHTTPステータスコード
    """
    try:
        # 設定からモデルリストを取得
        available_models = current_app.config.get("AVAILABLE_MODELS", [])
        
        # モデル情報を整形
        models = []
        for model_id in available_models:
            model_name = model_id.split("/")[-1]
            models.append({
                "id": model_id,
                "name": model_name,
                "provider": "gemini"
            })
        
        return jsonify({
            "models": models,
            "default": current_app.config.get("DEFAULT_MODEL")
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching models: {e}")
        return jsonify({
            "error": "Failed to fetch models",
            "message": str(e)
        }), 500