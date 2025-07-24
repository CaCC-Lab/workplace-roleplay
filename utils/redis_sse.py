"""
Redis Pub/SubとSSEのブリッジユーティリティ
"""
import json
import logging
import time
from typing import Generator, Optional, Dict, Any
import redis
from flask import Response
from config.config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class RedisSSEBridge:
    """Redis Pub/SubメッセージをSSEイベントに変換"""
    
    def __init__(self, redis_host: str = None, redis_port: int = None, redis_db: int = None):
        """
        Args:
            redis_host: Redisホスト（デフォルト: 設定から取得）
            redis_port: Redisポート（デフォルト: 設定から取得）
            redis_db: RedisDB番号（デフォルト: 設定から取得）
        """
        self.redis_client = redis.Redis(
            host=redis_host or config.REDIS_HOST,
            port=redis_port or config.REDIS_PORT,
            db=redis_db or config.REDIS_DB,
            decode_responses=True
        )
        self.pubsub = None
    
    def stream_channel(self, channel: str, timeout: int = 300) -> Generator[str, None, None]:
        """
        Redisチャンネルからメッセージを受信してSSE形式で配信
        
        Args:
            channel: 購読するRedisチャンネル
            timeout: タイムアウト秒数（デフォルト: 5分）
            
        Yields:
            SSE形式のメッセージ
        """
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe(channel)
        
        start_time = time.time()
        
        try:
            # 初期接続メッセージ
            yield self._format_sse({'type': 'connected', 'channel': channel})
            
            # メッセージの受信ループ
            while True:
                # タイムアウトチェック
                if time.time() - start_time > timeout:
                    yield self._format_sse({
                        'type': 'timeout',
                        'message': 'Connection timeout'
                    })
                    break
                
                # メッセージ取得（1秒のタイムアウト付き）
                message = self.pubsub.get_message(timeout=1.0)
                
                if message and message['type'] == 'message':
                    try:
                        # JSONメッセージをパース
                        data = json.loads(message['data'])
                        
                        # SSE形式で送信
                        yield self._format_sse(data)
                        
                        # 完了メッセージの場合は終了
                        if data.get('type') == 'complete':
                            break
                        
                        # エラーメッセージの場合も終了
                        if data.get('type') == 'error':
                            break
                            
                    except json.JSONDecodeError:
                        # JSON以外のメッセージはそのまま送信
                        yield self._format_sse({
                            'type': 'message',
                            'content': message['data']
                        })
                
                # ハートビート（15秒ごと）
                if int(time.time() - start_time) % 15 == 0:
                    yield self._format_sse({'type': 'heartbeat'})
                    
        except Exception as e:
            logger.error(f"Redis SSE streaming error: {str(e)}", exc_info=True)
            yield self._format_sse({
                'type': 'error',
                'error': str(e),
                'message': 'ストリーミング中にエラーが発生しました'
            })
        finally:
            if self.pubsub:
                self.pubsub.unsubscribe(channel)
                self.pubsub.close()
    
    def _format_sse(self, data: Dict[str, Any]) -> str:
        """データをSSE形式にフォーマット"""
        # イベントタイプの設定
        event_type = data.get('type', 'message')
        
        # データのJSON化
        json_data = json.dumps(data, ensure_ascii=False)
        
        # SSE形式
        if event_type != 'message':
            return f"event: {event_type}\ndata: {json_data}\n\n"
        else:
            return f"data: {json_data}\n\n"
    
    @staticmethod
    def create_sse_response(channel: str, timeout: int = 300) -> Response:
        """
        SSEレスポンスを作成
        
        Args:
            channel: Redisチャンネル
            timeout: タイムアウト秒数
            
        Returns:
            Flask Response オブジェクト
        """
        bridge = RedisSSEBridge()
        
        def generate():
            """SSEジェネレータ"""
            for message in bridge.stream_channel(channel, timeout):
                yield message
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # Nginxのバッファリング無効化
                'Connection': 'keep-alive'
            }
        )


class AsyncTaskManager:
    """非同期タスクの管理ユーティリティ"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True
        )
    
    def create_session_channel(self, session_id: str) -> str:
        """セッション用のチャンネル名を生成"""
        return f"stream:{session_id}"
    
    def notify_task_start(self, channel: str, task_id: str, task_type: str):
        """タスク開始を通知"""
        self.redis_client.publish(channel, json.dumps({
            'type': 'task_started',
            'task_id': task_id,
            'task_type': task_type,
            'timestamp': time.time()
        }))
    
    def notify_task_progress(self, channel: str, task_id: str, progress: float, message: str = None):
        """タスク進捗を通知"""
        data = {
            'type': 'task_progress',
            'task_id': task_id,
            'progress': progress,
            'timestamp': time.time()
        }
        if message:
            data['message'] = message
        
        self.redis_client.publish(channel, json.dumps(data))
    
    def get_task_result(self, task_id: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """タスク結果を取得（Celeryのresult backendから）"""
        key = f"celery-task-meta-{task_id}"
        
        # タイムアウトまで結果を待つ
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.redis_client.get(key)
            if result:
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return None
            time.sleep(0.5)
        
        return None