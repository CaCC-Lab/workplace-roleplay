"""推薦API"""
from flask import jsonify, request
from typing import Dict, Any, List
import random


def get_recommended_scenarios() -> tuple[Dict[str, Any], int]:
    """推薦シナリオを取得
    
    Returns:
        レスポンスとステータスコード
    """
    try:
        # リクエストパラメータを取得
        limit = request.args.get('limit', 3, type=int)
        
        # シナリオデータを取得
        from scenarios import load_scenarios
        all_scenarios = load_scenarios()
        
        # シナリオIDのリストを作成
        scenario_ids = list(all_scenarios.keys())
        
        # ランダムに推薦（本来はユーザーの履歴や分析結果に基づく）
        recommended_ids = random.sample(
            scenario_ids, 
            min(limit, len(scenario_ids))
        )
        
        # 推薦シナリオの詳細を構築
        recommendations = []
        for scenario_id in recommended_ids:
            scenario = all_scenarios[scenario_id]
            recommendations.append({
                "scenario_id": scenario_id,
                "title": scenario.get("title", ""),
                "difficulty": scenario.get("difficulty", ""),
                "tags": scenario.get("tags", []),
                "description": scenario.get("description", ""),
                "recommendation_reason": "あなたのスキルレベルに最適です"  # 仮の理由
            })
        
        return jsonify({
            "status": "success",
            "recommendations": recommendations,
            "total": len(recommendations)
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500