"""
シナリオ関連のルート定義
職場シナリオロールプレイ機能のHTTPエンドポイントを管理
"""
from flask import Blueprint, request, Response, jsonify
from typing import Dict, Any

from services.scenario_service import ScenarioService
from scenarios import load_scenarios
from errors import ValidationError, NotFoundError, ExternalAPIError


# Blueprintの作成
scenario_bp = Blueprint('scenario', __name__)


@scenario_bp.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    """
    利用可能なシナリオのリストを取得するエンドポイント
    
    Returns:
        シナリオリストを含むJSONレスポンス
    """
    try:
        scenarios = load_scenarios()
        # シナリオ情報を簡潔に整形
        scenario_list = []
        for scenario_id, scenario in scenarios.items():
            scenario_list.append({
                'id': scenario_id,
                'title': scenario['title'],
                'description': scenario['description'],
                'difficulty': scenario['difficulty'],
                'tags': scenario['tags'],
                'character': {
                    'name': scenario['character']['name'],
                    'role': scenario['character']['role']
                }
            })
        
        return jsonify({
            'scenarios': scenario_list,
            'total': len(scenario_list)
        })
        
    except Exception as e:
        print(f"Get scenarios error: {str(e)}")
        return jsonify({'error': 'シナリオ一覧の取得に失敗しました'}), 500


@scenario_bp.route('/api/scenario/<scenario_id>', methods=['GET'])
def get_scenario(scenario_id: str):
    """
    特定のシナリオの詳細情報を取得するエンドポイント
    
    Args:
        scenario_id: シナリオID
        
    Returns:
        シナリオ詳細を含むJSONレスポンス
    """
    try:
        scenario = ScenarioService.get_scenario(scenario_id)
        return jsonify(scenario)
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Get scenario error: {str(e)}")
        return jsonify({'error': 'シナリオ情報の取得に失敗しました'}), 500


@scenario_bp.route('/api/scenario_chat', methods=['POST'])
def scenario_chat():
    """
    シナリオモードでチャットメッセージを処理するエンドポイント
    
    Returns:
        SSE形式のストリーミングレスポンス
    """
    try:
        data = request.json
        scenario_id = data.get('scenario_id', '')
        message = data.get('message', '')
        model = data.get('model')
        
        # ScenarioServiceを使用してストリーミングレスポンスを生成
        return Response(
            ScenarioService.handle_scenario_message(scenario_id, message, model),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ExternalAPIError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        print(f"Scenario chat error: {str(e)}")
        return jsonify({'error': 'シナリオチャット処理中にエラーが発生しました'}), 500


@scenario_bp.route('/api/scenario_feedback', methods=['POST'])
def scenario_feedback():
    """
    シナリオ練習のフィードバックを生成するエンドポイント
    
    Returns:
        フィードバック情報を含むJSONレスポンス
    """
    try:
        data = request.json
        scenario_id = data.get('scenario_id', '')
        
        if not scenario_id:
            return jsonify({'error': 'シナリオIDが指定されていません'}), 400
        
        feedback_data = ScenarioService.generate_scenario_feedback(scenario_id)
        return jsonify(feedback_data)
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Scenario feedback error: {str(e)}")
        return jsonify({
            'error': 'フィードバック生成中にエラーが発生しました',
            'details': str(e)
        }), 500


@scenario_bp.route('/api/clear_scenario/<scenario_id>', methods=['POST'])
def clear_scenario(scenario_id: str):
    """
    特定のシナリオの履歴をクリアするエンドポイント
    
    Args:
        scenario_id: シナリオID
        
    Returns:
        成功メッセージを含むJSONレスポンス
    """
    try:
        result = ScenarioService.clear_scenario_history(scenario_id)
        return jsonify(result)
        
    except Exception as e:
        print(f"Clear scenario error: {str(e)}")
        return jsonify({
            'error': 'シナリオ履歴のクリアに失敗しました',
            'details': str(e)
        }), 500


@scenario_bp.route('/api/scenario/<scenario_id>/initial_message', methods=['GET'])
def get_initial_message(scenario_id: str):
    """
    シナリオの初期メッセージを取得するエンドポイント
    
    Args:
        scenario_id: シナリオID
        
    Returns:
        初期メッセージを含むJSONレスポンス
    """
    try:
        initial_message = ScenarioService.get_initial_message(scenario_id)
        return jsonify({
            'initial_message': initial_message,
            'has_message': initial_message is not None
        })
        
    except NotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        print(f"Get initial message error: {str(e)}")
        return jsonify({'error': '初期メッセージの取得に失敗しました'}), 500