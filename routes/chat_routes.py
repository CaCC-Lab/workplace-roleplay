"""
チャット関連のルート定義
雑談チャット機能のHTTPエンドポイントを管理
"""
from flask import Blueprint, request, Response, jsonify
from typing import Dict, Any

from services.chat_service import ChatService
from errors import ValidationError, ExternalAPIError


# Blueprintの作成
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """
    チャットメッセージを処理するエンドポイント
    
    Returns:
        SSE形式のストリーミングレスポンス
    """
    try:
        data = request.json
        message = data.get('message', '')
        model = data.get('model')
        
        # ChatServiceを使用してストリーミングレスポンスを生成
        return Response(
            ChatService.handle_chat_message(message, model),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except ExternalAPIError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        # エラーログの改善
        import logging
        logging.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        return jsonify({'error': 'チャット処理中にエラーが発生しました'}), 500


@chat_bp.route('/api/chat_feedback', methods=['POST'])
def chat_feedback():
    """
    チャット練習のフィードバックを生成するエンドポイント
    
    Returns:
        フィードバック情報を含むJSONレスポンス
    """
    try:
        feedback_data = ChatService.generate_chat_feedback()
        return jsonify(feedback_data)
        
    except Exception as e:
        # エラーログの改善
        import logging
        logging.error(f"Chat feedback error: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'フィードバック生成中にエラーが発生しました'
        }), 500


@chat_bp.route('/api/clear_chat', methods=['POST'])
def clear_chat():
    """
    チャット履歴をクリアするエンドポイント
    
    Returns:
        成功メッセージを含むJSONレスポンス
    """
    try:
        result = ChatService.clear_chat_history()
        return jsonify(result)
        
    except Exception as e:
        # エラーログの改善
        import logging
        logging.error(f"Clear chat error: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'チャット履歴のクリアに失敗しました'
        }), 500