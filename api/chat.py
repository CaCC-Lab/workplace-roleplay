"""
チャット関連のAPIエンドポイント
"""
from flask import Blueprint, request, jsonify, session, Response
from typing import Any
import json
from datetime import datetime

from security_utils import secure_endpoint
from errors import ValidationError
from services.llm_service import LLMService
from services.session_service import SessionService
from services.conversation_service import ConversationService


chat_bp = Blueprint('chat', __name__)

# サービスのインスタンス
llm_service = LLMService()
session_service = SessionService()
conversation_service = ConversationService()


@chat_bp.route("/chat", methods=["POST"])
@secure_endpoint
def handle_chat() -> Any:
    """チャットメッセージを処理し、AIの応答をストリーミングで返す"""
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        model_name = data.get("model", session.get("selected_model", "gemini-1.5-flash"))
        
        if not message:
            raise ValidationError("メッセージが空です", field="message")
        
        # セッション履歴の初期化
        session_service.initialize_history("chat_history")
        
        # ユーザーメッセージを履歴に追加
        user_entry = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        session_service.add_to_history("chat_history", user_entry)
        
        # LLMの初期化と応答生成
        llm = llm_service.initialize_llm(model_name)
        history = session.get("chat_history", [])
        
        # ストリーミングレスポンスの生成
        def generate():
            try:
                full_response = ""
                messages = conversation_service.format_messages_for_chat(history, message)
                
                stream = llm.stream(messages)
                
                for chunk in stream:
                    chunk_content = llm_service.extract_content(chunk)
                    if chunk_content:
                        full_response += chunk_content
                        yield f"data: {json.dumps({'content': chunk_content})}\n\n"
                
                # AIの応答を履歴に追加
                ai_entry = {
                    "role": "assistant",
                    "content": full_response,
                    "timestamp": datetime.now().isoformat(),
                    "model": model_name
                }
                session_service.add_to_history("chat_history", ai_entry)
                
                yield f"data: {json.dumps({'finished': True})}\n\n"
                
            except Exception as e:
                error_msg = f"ストリーミング中にエラーが発生しました: {str(e)}"
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )
        
    except ValidationError as e:
        return jsonify({"error": str(e), "field": e.field}), 400
    except Exception as e:
        return jsonify({"error": f"エラーが発生しました: {str(e)}"}), 500


@chat_bp.route("/clear_history", methods=["POST"])
@secure_endpoint
def clear_history():
    """チャット履歴をクリアする"""
    try:
        data = request.get_json()
        mode = data.get("mode", "chat")
        
        if mode == "chat":
            session_service.clear_history("chat_history")
            message = "雑談履歴がクリアされました。"
        elif mode == "scenario":
            scenario_id = data.get("scenario_id")
            if scenario_id:
                session_service.clear_history("scenario_histories", scenario_id)
                message = f"シナリオ {scenario_id} の履歴がクリアされました。"
            else:
                session_service.clear_history("scenario_histories")
                message = "すべてのシナリオ履歴がクリアされました。"
        elif mode == "watch":
            session_service.clear_history("watch_history")
            message = "観戦履歴がクリアされました。"
        elif mode == "all":
            # すべての履歴をクリア
            for key in ["chat_history", "scenario_histories", "watch_history"]:
                session_service.clear_history(key)
            message = "すべての履歴がクリアされました。"
        else:
            raise ValidationError("無効なモードです", field="mode")
        
        return jsonify({"message": message})
        
    except ValidationError as e:
        return jsonify({"error": str(e), "field": e.field}), 400
    except Exception as e:
        return jsonify({"error": f"履歴のクリア中にエラーが発生しました: {str(e)}"}), 500


@chat_bp.route("/start_chat", methods=["POST"])
@secure_endpoint
def start_chat() -> Any:
    """雑談を開始し、初期メッセージを生成する"""
    try:
        data = request.get_json()
        partner_type = data.get("partner_type", "colleague")
        situation = data.get("situation", "morning_greeting")
        topic = data.get("topic", "weather")
        model_name = data.get("model", session.get("selected_model", "gemini-1.5-flash"))
        
        # セッション履歴の初期化
        session_service.initialize_history("chat_history")
        session_service.set_start_time("chat_history")
        
        # 初期メッセージの生成
        llm = llm_service.initialize_llm(model_name)
        initial_message = conversation_service.generate_initial_message(
            llm, partner_type, situation, topic
        )
        
        # 初期メッセージを履歴に追加
        ai_entry = {
            "role": "assistant",
            "content": initial_message,
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "is_initial": True
        }
        session_service.add_to_history("chat_history", ai_entry)
        
        # セッション情報を保存
        session["chat_settings"] = {
            "partner_type": partner_type,
            "situation": situation,
            "topic": topic
        }
        
        return jsonify({
            "message": initial_message,
            "settings": session["chat_settings"]
        })
        
    except Exception as e:
        return jsonify({"error": f"チャットの開始中にエラーが発生しました: {str(e)}"}), 500


@chat_bp.route("/chat_feedback", methods=["POST"])
@secure_endpoint
def get_chat_feedback():
    """雑談練習のフィードバックを生成する"""
    try:
        data = request.get_json()
        model_name = data.get("model", session.get("selected_model", "gemini-1.5-flash"))
        
        history = session.get("chat_history", [])
        if len(history) < 2:
            raise ValidationError("フィードバックを生成するには、少なくとも1回の会話が必要です")
        
        # チャット設定を取得
        chat_settings = session.get("chat_settings", {})
        
        # フィードバックの生成
        llm = llm_service.initialize_llm(model_name)
        feedback = conversation_service.generate_chat_feedback(
            llm, history, chat_settings
        )
        
        # フィードバックを履歴に追加
        feedback_entry = {
            "role": "system",
            "content": feedback,
            "timestamp": datetime.now().isoformat(),
            "type": "feedback"
        }
        session_service.add_to_history("chat_history", feedback_entry)
        
        return jsonify({"feedback": feedback})
        
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"フィードバックの生成中にエラーが発生しました: {str(e)}"}), 500


@chat_bp.route("/conversation_history", methods=["POST"])
def get_conversation_history():
    """会話履歴を取得する"""
    try:
        data = request.get_json()
        mode = data.get("mode", "chat")
        scenario_id = data.get("scenario_id")
        
        if mode == "chat":
            history = session.get("chat_history", [])
        elif mode == "scenario" and scenario_id:
            histories = session.get("scenario_histories", {})
            history = histories.get(scenario_id, [])
        elif mode == "watch":
            history = session.get("watch_history", [])
        else:
            history = []
        
        # 履歴の整形
        formatted_history = []
        for entry in history:
            formatted_entry = {
                "role": entry.get("role", "unknown"),
                "content": entry.get("content", ""),
                "timestamp": entry.get("timestamp", ""),
                "type": entry.get("type", "message")
            }
            
            # 追加情報があれば含める
            if "model" in entry:
                formatted_entry["model"] = entry["model"]
            if "is_initial" in entry:
                formatted_entry["is_initial"] = entry["is_initial"]
            
            formatted_history.append(formatted_entry)
        
        return jsonify({
            "history": formatted_history,
            "count": len(formatted_history)
        })
        
    except Exception as e:
        return jsonify({"error": f"履歴の取得中にエラーが発生しました: {str(e)}"}), 500