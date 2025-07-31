"""
観戦モード関連のAPIエンドポイント
"""
from flask import Blueprint, request, jsonify, session, Response
from typing import Any
import json
from datetime import datetime

from security_utils import secure_endpoint
from errors import ValidationError
from services.llm_service import LLMService
from services.session_service import SessionService
from services.watch_service import WatchService


watch_bp = Blueprint('watch', __name__)

# サービスのインスタンス
llm_service = LLMService()
session_service = SessionService()
watch_service = WatchService()


@watch_bp.route("/start", methods=["POST"])
@secure_endpoint
def start_watch():
    """観戦モードを開始する"""
    try:
        data = request.get_json()
        partner1_model = data.get("partner1_model", "gemini-1.5-flash")
        partner2_model = data.get("partner2_model", "gemini-1.5-pro")
        topic = data.get("topic", "仕事の進め方について")
        
        # セッション履歴の初期化
        session_service.initialize_history("watch_history")
        session_service.set_start_time("watch_history")
        
        # セッション情報を保存
        session["watch_settings"] = {
            "partner1_model": partner1_model,
            "partner2_model": partner2_model,
            "topic": topic,
            "current_speaker": 1
        }
        
        # 最初のメッセージを生成（パートナー1から開始）
        llm1 = llm_service.initialize_llm(partner1_model)
        initial_prompt = watch_service.generate_initial_prompt(topic)
        
        initial_message = llm_service.create_and_get_response(
            llm1, initial_prompt, extract=True
        )
        
        # 履歴に追加
        entry = {
            "role": "partner1",
            "content": initial_message,
            "timestamp": datetime.now().isoformat(),
            "model": partner1_model
        }
        session_service.add_to_history("watch_history", entry)
        
        return jsonify({
            "message": initial_message,
            "speaker": "partner1",
            "settings": session["watch_settings"]
        })
        
    except Exception as e:
        return jsonify({"error": f"観戦モードの開始中にエラーが発生しました: {str(e)}"}), 500


@watch_bp.route("/next", methods=["POST"])
@secure_endpoint
def next_watch_message() -> Any:
    """観戦モードで次のメッセージを生成する"""
    try:
        watch_settings = session.get("watch_settings")
        if not watch_settings:
            raise ValidationError("観戦モードが開始されていません")
        
        history = session.get("watch_history", [])
        if not history:
            raise ValidationError("会話履歴が見つかりません")
        
        # 現在の話者を切り替え
        current_speaker = watch_settings["current_speaker"]
        next_speaker = 2 if current_speaker == 1 else 1
        
        # 話者に応じたモデルを選択
        if next_speaker == 1:
            model_name = watch_settings["partner1_model"]
            role = "partner1"
        else:
            model_name = watch_settings["partner2_model"]
            role = "partner2"
        
        # LLMを初期化して応答を生成
        llm = llm_service.initialize_llm(model_name)
        
        # ストリーミングレスポンスの生成
        def generate():
            try:
                full_response = ""
                messages = watch_service.format_messages_for_watch(history, role)
                
                stream = llm.stream(messages)
                
                for chunk in stream:
                    chunk_content = llm_service.extract_content(chunk)
                    if chunk_content:
                        full_response += chunk_content
                        yield f"data: {json.dumps({'content': chunk_content, 'speaker': role})}\n\n"
                
                # 応答を履歴に追加
                entry = {
                    "role": role,
                    "content": full_response,
                    "timestamp": datetime.now().isoformat(),
                    "model": model_name
                }
                session_service.add_to_history("watch_history", entry)
                
                # 話者を更新
                session["watch_settings"]["current_speaker"] = next_speaker
                
                yield f"data: {json.dumps({'finished': True, 'speaker': role})}\n\n"
                
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
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"次のメッセージの生成中にエラーが発生しました: {str(e)}"}), 500


@watch_bp.route("/feedback", methods=["POST"])
@secure_endpoint
def get_watch_feedback():
    """観戦モードのフィードバックを生成する"""
    try:
        data = request.get_json()
        model_name = data.get("model", session.get("selected_model", "gemini-1.5-flash"))
        
        history = session.get("watch_history", [])
        if len(history) < 2:
            raise ValidationError("フィードバックを生成するには、少なくとも2つのメッセージが必要です")
        
        watch_settings = session.get("watch_settings", {})
        
        # フィードバックの生成
        llm = llm_service.initialize_llm(model_name)
        feedback = watch_service.generate_watch_feedback(
            llm, history, watch_settings
        )
        
        # フィードバックを履歴に追加
        feedback_entry = {
            "role": "system",
            "content": feedback,
            "timestamp": datetime.now().isoformat(),
            "type": "feedback"
        }
        session_service.add_to_history("watch_history", feedback_entry)
        
        return jsonify({"feedback": feedback})
        
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"フィードバックの生成中にエラーが発生しました: {str(e)}"}), 500


@watch_bp.route("/summary", methods=["GET"])
def get_watch_summary():
    """観戦モードの会話サマリーを取得する"""
    try:
        history = session.get("watch_history", [])
        watch_settings = session.get("watch_settings", {})
        
        if not history:
            return jsonify({
                "summary": None,
                "message_count": 0,
                "settings": watch_settings
            })
        
        # メッセージ数をカウント
        partner1_count = sum(1 for msg in history if msg.get("role") == "partner1")
        partner2_count = sum(1 for msg in history if msg.get("role") == "partner2")
        
        summary = {
            "total_messages": len(history),
            "partner1_messages": partner1_count,
            "partner2_messages": partner2_count,
            "topic": watch_settings.get("topic", "不明"),
            "duration": watch_service.calculate_duration(history),
            "models": {
                "partner1": watch_settings.get("partner1_model", "不明"),
                "partner2": watch_settings.get("partner2_model", "不明")
            }
        }
        
        return jsonify({
            "summary": summary,
            "message_count": len(history),
            "settings": watch_settings
        })
        
    except Exception as e:
        return jsonify({"error": f"サマリーの取得中にエラーが発生しました: {str(e)}"}), 500