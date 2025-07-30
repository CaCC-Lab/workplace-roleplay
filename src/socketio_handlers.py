"""Socket.IOイベントハンドラー"""
from flask_socketio import emit, join_room, leave_room
from flask import session
import logging

logger = logging.getLogger(__name__)


def register_socketio_handlers(socketio):
    """Socket.IOイベントハンドラーを登録"""
    
    @socketio.on("connect")
    def handle_connect():
        """クライアント接続時の処理"""
        logger.info("Client connected")
        emit("connected", {"status": "Connected to server"})
    
    @socketio.on("disconnect")
    def handle_disconnect():
        """クライアント切断時の処理"""
        logger.info("Client disconnected")
    
    @socketio.on("join_scenario")
    def handle_join_scenario(data):
        """シナリオルームへの参加"""
        scenario_id = data.get("scenario_id")
        if scenario_id:
            room = f"scenario_{scenario_id}"
            join_room(room)
            emit("joined_room", {"room": room})
            logger.info(f"Client joined room: {room}")
    
    @socketio.on("leave_scenario")
    def handle_leave_scenario(data):
        """シナリオルームからの退出"""
        scenario_id = data.get("scenario_id")
        if scenario_id:
            room = f"scenario_{scenario_id}"
            leave_room(room)
            emit("left_room", {"room": room})
            logger.info(f"Client left room: {room}")
    
    @socketio.on("coaching_feedback")
    def handle_coaching_feedback(data):
        """リアルタイムコーチングフィードバック"""
        try:
            message = data.get("message", "")
            scenario_id = data.get("scenario_id")
            
            # 簡単なフィードバック生成（実際はAIで生成）
            feedback = {
                "type": "suggestion",
                "content": "もう少し具体的に話すと良いでしょう。",
                "confidence": 0.8
            }
            
            emit("coaching_update", feedback)
            
        except Exception as e:
            logger.error(f"Coaching feedback error: {str(e)}")
            emit("error", {"message": str(e)})