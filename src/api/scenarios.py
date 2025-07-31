"""シナリオAPI"""
from flask import request, jsonify, current_app
from typing import Dict, Any

from ..services import ScenarioService


def scenario_chat(scenario_id: str) -> tuple[Dict[str, Any], int]:
    """シナリオチャットエンドポイント
    
    Args:
        scenario_id: シナリオID
        
    Returns:
        レスポンスとHTTPステータスコード
    """
    try:
        # リクエストデータの取得
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # シナリオサービスの初期化
        scenario_service = ScenarioService()
        
        # シナリオの存在確認
        if not scenario_service.exists(scenario_id):
            return jsonify({"error": "Scenario not found"}), 404
        
        # メッセージの処理
        response = scenario_service.process_message(
            scenario_id=scenario_id,
            message=message
        )
        
        return jsonify({
            "response": response,
            "scenario_id": scenario_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Scenario chat error: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "シナリオチャット処理中にエラーが発生しました"
        }), 500


def scenario_feedback(scenario_id: str) -> tuple[Dict[str, Any], int]:
    """シナリオフィードバックエンドポイント
    
    Args:
        scenario_id: シナリオID
        
    Returns:
        レスポンスとHTTPステータスコード
    """
    try:
        # シナリオサービスの初期化
        scenario_service = ScenarioService()
        
        # シナリオの存在確認
        if not scenario_service.exists(scenario_id):
            return jsonify({"error": "Scenario not found"}), 404
        
        # フィードバックの生成
        feedback = scenario_service.generate_feedback(scenario_id)
        
        return jsonify({
            "feedback": feedback,
            "scenario_id": scenario_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Scenario feedback error: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "フィードバック生成中にエラーが発生しました"
        }), 500