"""
Celeryタスクの進捗監視とキャンセル機能を提供するFlaskルート

Server-Sent Events (SSE)を使用してリアルタイムでタスクの状態を配信し、
部分レスポンスの表示やタスクキャンセル機能を提供する
"""
import json
import logging
import time
from flask import Blueprint, request, jsonify, Response
from celery import current_app as celery_app
from celery.result import AsyncResult
from tasks.retry_strategy import get_retry_status, PartialResponseManager
from utils.redis_sse import RedisSSEBridge
from utils.security import CSRFToken

logger = logging.getLogger(__name__)

# Blueprintを作成
progress_bp = Blueprint('task_progress', __name__, url_prefix='/api/tasks')


@progress_bp.route('/<task_id>/status', methods=['GET'])
def get_task_status(task_id):
    """
    タスクの現在の状態を取得
    
    Args:
        task_id (str): CeleryタスクID
        
    Returns:
        JSON: タスクの状態情報
    """
    try:
        # Celery AsyncResultから基本情報を取得
        result = AsyncResult(task_id, app=celery_app)
        
        # リトライ状態を取得
        retry_status = get_retry_status(task_id)
        
        status_data = {
            'task_id': task_id,
            'state': result.state,
            'result': result.result if result.ready() else None,
            'info': result.info,
            'retry_status': retry_status,
            'ready': result.ready(),
            'successful': result.successful() if result.ready() else False,
            'failed': result.failed() if result.ready() else False
        }
        
        # エラー情報があれば追加
        if result.failed() and result.info:
            status_data['error'] = {
                'type': type(result.info).__name__,
                'message': str(result.info)
            }
        
        return jsonify({
            'status': 'success',
            'data': status_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': 'タスク状態の取得に失敗しました'
        }), 500


@progress_bp.route('/<task_id>/cancel', methods=['POST'])
@CSRFToken.require_csrf
def cancel_task(task_id):
    """
    実行中のタスクをキャンセル
    
    Args:
        task_id (str): CeleryタスクID
        
    Returns:
        JSON: キャンセル結果
    """
    try:
        # タスクの存在確認
        result = AsyncResult(task_id, app=celery_app)
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': 'タスクが見つかりません'
            }), 404
        
        # 既に完了済みの場合
        if result.ready():
            return jsonify({
                'status': 'error',
                'message': 'タスクは既に完了しています',
                'task_state': result.state
            }), 400
        
        # タスクをキャンセル
        result.revoke(terminate=True)
        
        # 部分レスポンスがあれば削除
        PartialResponseManager.delete_partial_response(task_id)
        
        logger.info(f"Task {task_id} cancelled by user")
        
        return jsonify({
            'status': 'success',
            'message': 'タスクをキャンセルしました',
            'task_id': task_id
        })
        
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': 'タスクのキャンセルに失敗しました'
        }), 500


@progress_bp.route('/<task_id>/partial', methods=['GET'])
def get_partial_response(task_id):
    """
    タスクの部分レスポンスを取得
    
    Args:
        task_id (str): CeleryタスクID
        
    Returns:
        JSON: 部分レスポンスデータ
    """
    try:
        partial_data = PartialResponseManager.get_partial_response(task_id)
        
        if not partial_data:
            return jsonify({
                'status': 'error',
                'message': '部分レスポンスが見つかりません'
            }), 404
        
        # 部分コンテンツを再構築
        partial_content = PartialResponseManager.reconstruct_content(
            partial_data.get('chunks', [])
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'task_id': task_id,
                'content': partial_content,
                'chunks_count': partial_data.get('total_chunks', 0),
                'saved_at': partial_data.get('saved_at'),
                'metadata': partial_data.get('metadata', {})
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get partial response for {task_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': '部分レスポンスの取得に失敗しました'
        }), 500


@progress_bp.route('/stream/<session_id>', methods=['GET'])
def stream_task_progress(session_id):
    """
    タスクの進捗をServer-Sent Eventsでストリーミング
    
    Args:
        session_id (str): セッションID
        
    Returns:
        Response: SSEストリーム
    """
    try:
        # パラメータの取得
        timeout = int(request.args.get('timeout', 300))  # デフォルト5分
        heartbeat_interval = int(request.args.get('heartbeat_interval', 15))  # デフォルト15秒
        
        # RedisSSEBridgeを使用してストリーミング
        return RedisSSEBridge.create_sse_response(
            channel=f"stream:{session_id}",
            timeout=timeout,
            heartbeat_interval=heartbeat_interval
        )
        
    except ValueError as e:
        logger.error(f"Invalid parameter in stream request: {e}")
        return jsonify({
            'status': 'error',
            'message': 'パラメータが無効です'
        }), 400
    except Exception as e:
        logger.error(f"Failed to create SSE stream for session {session_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': 'ストリーミングの開始に失敗しました'
        }), 500


@progress_bp.route('/active', methods=['GET'])
def get_active_tasks():
    """
    アクティブなタスクの一覧を取得
    
    Returns:
        JSON: アクティブタスクの情報
    """
    try:
        # Celeryから実行中のタスクを取得
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        if not active_tasks:
            return jsonify({
                'status': 'success',
                'data': {
                    'tasks': [],
                    'total': 0
                }
            })
        
        # タスク情報を整理
        tasks = []
        for worker, task_list in active_tasks.items():
            for task_info in task_list:
                task_id = task_info.get('id')
                retry_status = get_retry_status(task_id) if task_id else {}
                
                tasks.append({
                    'task_id': task_id,
                    'worker': worker,
                    'name': task_info.get('name'),
                    'args': task_info.get('args', []),
                    'kwargs': task_info.get('kwargs', {}),
                    'time_start': task_info.get('time_start'),
                    'retry_status': retry_status
                })
        
        return jsonify({
            'status': 'success',
            'data': {
                'tasks': tasks,
                'total': len(tasks)
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        return jsonify({
            'status': 'error',
            'message': 'アクティブタスクの取得に失敗しました'
        }), 500


@progress_bp.route('/stats', methods=['GET'])
def get_task_stats():
    """
    タスクの統計情報を取得
    
    Returns:
        JSON: タスク統計情報
    """
    try:
        inspect = celery_app.control.inspect()
        
        # 各種統計を取得
        stats = inspect.stats()
        reserved = inspect.reserved()
        scheduled = inspect.scheduled()
        active = inspect.active()
        
        # 統計情報を集計
        total_workers = len(stats) if stats else 0
        total_active = sum(len(tasks) for tasks in active.values()) if active else 0
        total_reserved = sum(len(tasks) for tasks in reserved.values()) if reserved else 0
        total_scheduled = sum(len(tasks) for tasks in scheduled.values()) if scheduled else 0
        
        return jsonify({
            'status': 'success',
            'data': {
                'workers': total_workers,
                'active_tasks': total_active,
                'reserved_tasks': total_reserved,
                'scheduled_tasks': total_scheduled,
                'total_pending': total_active + total_reserved + total_scheduled,
                'stats': stats
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        return jsonify({
            'status': 'error',
            'message': 'タスク統計の取得に失敗しました'
        }), 500


@progress_bp.route('/health', methods=['GET'])
def health_check():
    """
    タスクシステムのヘルスチェック
    
    Returns:
        JSON: ヘルスチェック結果
    """
    try:
        inspect = celery_app.control.inspect()
        
        # ワーカーの生存確認
        ping_result = inspect.ping()
        
        healthy_workers = []
        unhealthy_workers = []
        
        if ping_result:
            for worker, pong in ping_result.items():
                if pong.get('ok') == 'pong':
                    healthy_workers.append(worker)
                else:
                    unhealthy_workers.append(worker)
        
        # ヘルス状態の判定
        total_workers = len(healthy_workers) + len(unhealthy_workers)
        health_status = 'healthy' if len(unhealthy_workers) == 0 else 'degraded'
        
        if total_workers == 0:
            health_status = 'unhealthy'
        
        return jsonify({
            'status': 'success',
            'data': {
                'health_status': health_status,
                'total_workers': total_workers,
                'healthy_workers': len(healthy_workers),
                'unhealthy_workers': len(unhealthy_workers),
                'worker_details': {
                    'healthy': healthy_workers,
                    'unhealthy': unhealthy_workers
                },
                'timestamp': int(time.time())
            }
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'message': 'ヘルスチェックに失敗しました',
            'data': {
                'health_status': 'unhealthy',
                'error': str(e)
            }
        }), 500


# エラーハンドラー
@progress_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'リソースが見つかりません'
    }), 404


@progress_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error in task progress API: {error}")
    return jsonify({
        'status': 'error',
        'message': '内部サーバーエラーが発生しました'
    }), 500