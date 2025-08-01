"""
観戦モード関連のルート定義
AI同士の会話観戦機能のHTTPエンドポイントを管理
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any

from services.watch_service import WatchService
from errors import ValidationError, ExternalAPIError


# Blueprintの作成
watch_bp = Blueprint('watch', __name__)


@watch_bp.route('/api/watch/start', methods=['POST'])
def start_watch():
    """
    観戦モードを開始するエンドポイント
    
    Request JSON:
        - partner1_type: AI1のタイプ（同僚、友人、先輩、カウンセラー）
        - partner2_type: AI2のタイプ
        - topic: 会話の話題（仕事、趣味、日常、悩み）
        - model: 使用するモデル名
        
    Returns:
        初期設定と最初のメッセージを含むJSONレスポンス
    """
    try:
        data = request.json or {}
        
        result = WatchService.start_watch_mode(
            partner1_type=data.get('partner1_type'),
            partner2_type=data.get('partner2_type'),
            topic=data.get('topic'),
            model_name=data.get('model')
        )
        
        return jsonify(result)
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except ExternalAPIError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        print(f"Start watch error: {str(e)}")
        return jsonify({'error': '観戦モードの開始に失敗しました'}), 500


@watch_bp.route('/api/watch/next', methods=['POST'])
def next_watch_message():
    """
    次のメッセージを生成するエンドポイント
    
    Returns:
        次のメッセージと話者情報を含むJSONレスポンス
    """
    try:
        result = WatchService.generate_next_message()
        return jsonify(result)
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except ExternalAPIError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        print(f"Next watch message error: {str(e)}")
        return jsonify({'error': '次のメッセージ生成に失敗しました'}), 500


@watch_bp.route('/api/watch/summary', methods=['GET'])
def get_watch_summary():
    """
    観戦モードの要約を取得するエンドポイント
    
    Returns:
        会話の要約情報を含むJSONレスポンス
    """
    try:
        summary = WatchService.get_watch_summary()
        return jsonify(summary)
        
    except Exception as e:
        print(f"Get watch summary error: {str(e)}")
        return jsonify({
            'error': '要約の取得に失敗しました',
            'details': str(e)
        }), 500


@watch_bp.route('/api/watch/partner_types', methods=['GET'])
def get_partner_types():
    """
    利用可能なパートナータイプを取得するエンドポイント
    
    Returns:
        パートナータイプのリストを含むJSONレスポンス
    """
    try:
        partner_types = []
        for type_name, description in WatchService.PARTNER_TYPES.items():
            partner_types.append({
                'name': type_name,
                'description': description
            })
        
        return jsonify({
            'partner_types': partner_types,
            'total': len(partner_types)
        })
        
    except Exception as e:
        print(f"Get partner types error: {str(e)}")
        return jsonify({'error': 'パートナータイプの取得に失敗しました'}), 500


@watch_bp.route('/api/watch/topics', methods=['GET'])
def get_topics():
    """
    利用可能な話題を取得するエンドポイント
    
    Returns:
        話題のリストを含むJSONレスポンス
    """
    try:
        topics = []
        for topic_name, description in WatchService.TOPICS.items():
            topics.append({
                'name': topic_name,
                'description': description
            })
        
        return jsonify({
            'topics': topics,
            'total': len(topics)
        })
        
    except Exception as e:
        print(f"Get topics error: {str(e)}")
        return jsonify({'error': '話題の取得に失敗しました'}), 500