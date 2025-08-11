"""
A/Bテスト用の並行エンドポイント
既存システムに影響を与えずに新サービスをテスト
"""
from flask import Blueprint, request, jsonify, Response, session
from typing import Dict, Any
import json
import time
import asyncio
from datetime import datetime

# サービスインポート
from services.chat_service import ChatService
from services.session_service import SessionService
from services.llm_service import LLMService
from config.feature_flags import feature_flags

# Blueprintの作成
ab_test_bp = Blueprint('ab_test', __name__, url_prefix='/api/v2')

# サービスインスタンス（遅延初期化）
_chat_service = None
_session_service = None
_llm_service = None

def get_services():
    """サービスインスタンスの取得（シングルトン）"""
    global _chat_service, _session_service, _llm_service
    
    if _llm_service is None:
        _llm_service = LLMService()
    if _session_service is None:
        _session_service = SessionService()
    if _chat_service is None:
        _chat_service = ChatService(
            llm_service=_llm_service,
            session_service=_session_service
        )
    
    return _chat_service, _session_service, _llm_service

# ============= チャット関連 =============

@ab_test_bp.route('/chat', methods=['POST'])
def chat_v2():
    """
    新サービスを使用したチャットエンドポイント
    /api/v2/chat
    """
    try:
        chat_service, _, _ = get_services()
        
        # リクエストデータ取得
        data = request.get_json()
        message = data.get('message', '').strip()
        model_name = data.get('model')
        
        if not message:
            return jsonify({'error': 'メッセージが空です'}), 400
        
        # SSEレスポンスの生成
        def generate():
            try:
                # 非同期処理を同期的に実行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def stream_response():
                    accumulated = ""
                    async for chunk in chat_service.process_chat_message(message, model_name):
                        accumulated += chunk
                        yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
                    
                    # 最終データ
                    yield f"data: {json.dumps({'done': True, 'full_content': accumulated}, ensure_ascii=False)}\n\n"
                
                # 非同期ジェネレータを実行
                async_gen = stream_response()
                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        break
                    
            except Exception as e:
                error_msg = f"ストリーミングエラー: {str(e)}"
                yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'X-Service-Version': 'v2-new'
            }
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ab_test_bp.route('/chat/compare', methods=['POST'])
def chat_compare():
    """
    新旧サービスの出力を比較（開発用）
    /api/v2/chat/compare
    """
    try:
        from app import process_chat_message_legacy  # 既存実装をインポート
        chat_service, _, _ = get_services()
        
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'メッセージが空です'}), 400
        
        # タイミング測定
        start_time = time.time()
        
        # 既存実装の実行
        legacy_start = time.time()
        legacy_response = ""
        try:
            # 既存実装を呼び出し（同期的に収集）
            for chunk in process_chat_message_legacy(message):
                if isinstance(chunk, dict) and 'content' in chunk:
                    legacy_response += chunk['content']
                elif isinstance(chunk, str):
                    legacy_response += chunk
        except Exception as e:
            legacy_response = f"Error: {str(e)}"
        legacy_time = time.time() - legacy_start
        
        # 新実装の実行
        new_start = time.time()
        new_response = ""
        try:
            # 非同期処理を同期的に実行
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def get_new_response():
                result = ""
                async for chunk in chat_service.process_chat_message(message):
                    result += chunk
                return result
            
            new_response = loop.run_until_complete(get_new_response())
            loop.close()
        except Exception as e:
            new_response = f"Error: {str(e)}"
        new_time = time.time() - new_start
        
        # 比較結果
        total_time = time.time() - start_time
        
        # 差分検出
        is_identical = legacy_response == new_response
        
        comparison_result = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'legacy': {
                'response': legacy_response[:1000],  # 最初の1000文字
                'length': len(legacy_response),
                'time': legacy_time
            },
            'new': {
                'response': new_response[:1000],
                'length': len(new_response),
                'time': new_time
            },
            'comparison': {
                'identical': is_identical,
                'time_diff': new_time - legacy_time,
                'time_ratio': new_time / legacy_time if legacy_time > 0 else 0,
                'length_diff': len(new_response) - len(legacy_response)
            },
            'total_time': total_time
        }
        
        # 差分があればログ出力
        if not is_identical and feature_flags.log_differences:
            print(f"[A/B Test Difference] Message: {message[:50]}...")
            print(f"  Legacy length: {len(legacy_response)}, New length: {len(new_response)}")
            print(f"  Time: Legacy {legacy_time:.2f}s, New {new_time:.2f}s")
        
        return jsonify(comparison_result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= 設定関連 =============

@ab_test_bp.route('/config', methods=['GET'])
def get_ab_config():
    """
    現在のA/Bテスト設定を取得
    /api/v2/config
    """
    return jsonify(feature_flags.get_config())

@ab_test_bp.route('/health', methods=['GET'])
def health_check():
    """
    新サービスのヘルスチェック
    /api/v2/health
    """
    try:
        chat_service, session_service, llm_service = get_services()
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'chat_service': chat_service is not None,
                'session_service': session_service is not None,
                'llm_service': llm_service is not None
            },
            'feature_flags': feature_flags.get_config()
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ============= シナリオ関連（今後の拡張用）=============

@ab_test_bp.route('/scenario_chat', methods=['POST'])
def scenario_chat_v2():
    """
    新サービスを使用したシナリオチャット（将来の実装用）
    /api/v2/scenario_chat
    """
    return jsonify({
        'message': 'Scenario chat v2 endpoint - Coming soon',
        'service_version': 'v2'
    }), 501  # Not Implemented

# ============= 観戦モード関連（今後の拡張用）=============

@ab_test_bp.route('/watch/start', methods=['POST'])
def watch_start_v2():
    """
    新サービスを使用した観戦モード開始（将来の実装用）
    /api/v2/watch/start
    """
    return jsonify({
        'message': 'Watch mode v2 endpoint - Coming soon',
        'service_version': 'v2'
    }), 501  # Not Implemented