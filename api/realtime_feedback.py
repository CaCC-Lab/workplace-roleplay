"""
リアルタイムフィードバック API エンドポイント
"""
import json
import uuid
from flask import Blueprint, request, jsonify, Response, session, current_app
from typing import Iterator
import logging

from services.realtime_feedback_service import realtime_feedback_service
from services.persona_service import persona_service

logger = logging.getLogger(__name__)

# Blueprint作成
realtime_feedback_bp = Blueprint('realtime_feedback', __name__, url_prefix='/api/realtime-feedback')


@realtime_feedback_bp.route('/stream')
def feedback_stream():
    """
    SSEを使ったリアルタイムフィードバック配信エンドポイント
    """
    def generate_feedback_stream() -> Iterator[str]:
        """フィードバックストリームを生成"""
        # 基本的なSSE実装
        # 実際の実装では、フィードバック生成とリアルタイム配信を行う
        yield f"data: {json.dumps({'event': 'connected', 'message': 'フィードバックストリーム接続'})}\n\n"
        
        # デモ用の基本的なフィードバック
        demo_feedback = {
            'feedback_id': str(uuid.uuid4()),
            'content': 'デモフィードバック：会話の要点を整理することをお勧めします',
            'type': 'suggestion',
            'confidence': 0.75,
            'priority': 3,
            'persona_code': 'DEMO_PERSONA'
        }
        
        yield f"data: {json.dumps({'event': 'feedback', 'data': demo_feedback})}\n\n"
    
    return Response(
        generate_feedback_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@realtime_feedback_bp.route('/toggle', methods=['POST'])
def toggle_feedback():
    """
    フィードバック機能のON/OFF切り替え
    """
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        # セッションにフィードバック設定を保存
        session['feedback_enabled'] = enabled
        
        return jsonify({
            'success': True,
            'feedback_enabled': enabled,
            'message': f"フィードバック機能を{'有効' if enabled else '無効'}にしました"
        })
        
    except Exception as e:
        logger.error(f"フィードバック切り替えエラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'フィードバック設定の切り替えに失敗しました'
        }), 500


@realtime_feedback_bp.route('/settings', methods=['GET'])
def get_feedback_settings():
    """
    フィードバック設定の取得
    """
    try:
        # デフォルト設定
        default_settings = {
            'enabled': True,
            'feedback_frequency': 'moderate',  # low, moderate, high
            'feedback_types': ['suggestion', 'guidance', 'praise'],
            'auto_timing': True,
            'confidence_threshold': 0.6
        }
        
        # セッションから設定を取得
        settings = {
            'enabled': session.get('feedback_enabled', True),
            'feedback_frequency': session.get('feedback_frequency', 'moderate'),
            'feedback_types': session.get('feedback_types', default_settings['feedback_types']),
            'auto_timing': session.get('feedback_auto_timing', True),
            'confidence_threshold': session.get('feedback_confidence_threshold', 0.6)
        }
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"フィードバック設定取得エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'フィードバック設定の取得に失敗しました'
        }), 500


@realtime_feedback_bp.route('/settings', methods=['POST'])
def update_feedback_settings():
    """
    フィードバック設定の更新
    """
    try:
        data = request.get_json()
        
        # 設定の検証と保存
        if 'enabled' in data:
            session['feedback_enabled'] = bool(data['enabled'])
        
        if 'feedback_frequency' in data:
            frequency = data['feedback_frequency']
            if frequency in ['low', 'moderate', 'high']:
                session['feedback_frequency'] = frequency
        
        if 'feedback_types' in data:
            types = data['feedback_types']
            if isinstance(types, list):
                session['feedback_types'] = types
        
        if 'auto_timing' in data:
            session['feedback_auto_timing'] = bool(data['auto_timing'])
        
        if 'confidence_threshold' in data:
            threshold = data['confidence_threshold']
            if isinstance(threshold, (int, float)) and 0 <= threshold <= 1:
                session['feedback_confidence_threshold'] = threshold
        
        return jsonify({
            'success': True,
            'message': 'フィードバック設定を更新しました'
        })
        
    except Exception as e:
        logger.error(f"フィードバック設定更新エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'フィードバック設定の更新に失敗しました'
        }), 500


@realtime_feedback_bp.route('/generate', methods=['POST'])
def generate_feedback():
    """
    手動フィードバック生成エンドポイント（テスト用）
    """
    try:
        data = request.get_json()
        
        persona_code = data.get('persona_code')
        conversation_context = data.get('conversation_context', {})
        
        if not persona_code:
            return jsonify({
                'success': False,
                'error': 'ペルソナコードが必要です'
            }), 400
        
        # ペルソナを取得
        from models import AIPersona
        with current_app.app_context():
            persona = AIPersona.query.filter_by(persona_code=persona_code).first()
            
            if not persona:
                return jsonify({
                    'success': False,
                    'error': 'ペルソナが見つかりません'
                }), 404
            
            # フィードバックを生成
            feedback = realtime_feedback_service.generate_feedback(persona, conversation_context)
            
            if feedback:
                return jsonify({
                    'success': True,
                    'feedback': {
                        'content': feedback.content,
                        'type': feedback.feedback_type,
                        'confidence': feedback.confidence_score,
                        'priority': feedback.timing_priority,
                        'relevance': feedback.persona_specialty_relevance
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'feedback': None,
                    'message': 'このタイミングではフィードバックを生成しませんでした'
                })
        
    except Exception as e:
        logger.error(f"フィードバック生成エラー: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'フィードバック生成に失敗しました'
        }), 500