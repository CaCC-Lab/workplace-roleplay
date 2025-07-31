"""
シナリオ関連のAPIエンドポイント
"""
from flask import Blueprint, request, jsonify, session, Response
from typing import Any
import json
from datetime import datetime

from security_utils import secure_endpoint
from errors import ValidationError
from scenarios import load_scenarios
from services.llm_service import LLMService
from services.session_service import SessionService
from services.scenario_service import ScenarioService
from strength_analyzer import analyze_user_strengths


scenarios_bp = Blueprint('scenarios', __name__)

# サービスのインスタンス
llm_service = LLMService()
session_service = SessionService()
scenario_service = ScenarioService()

# シナリオデータの読み込み
SCENARIOS = load_scenarios()


@scenarios_bp.route("/scenario_chat", methods=["POST"])
@secure_endpoint
def scenario_chat():
    """シナリオベースのチャットを処理する"""
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        scenario_id = data.get("scenario_id")
        model_name = data.get("model", session.get("selected_model", "gemini-1.5-flash"))
        
        if not message:
            raise ValidationError("メッセージが空です", field="message")
        
        if not scenario_id or scenario_id not in SCENARIOS:
            raise ValidationError("無効なシナリオIDです", field="scenario_id")
        
        scenario = SCENARIOS[scenario_id]
        
        # シナリオ履歴の初期化
        session_service.initialize_history("scenario_histories", scenario_id)
        
        # 初回の場合、開始時刻を記録
        histories = session.get("scenario_histories", {})
        if scenario_id not in histories or not histories[scenario_id]:
            session_service.set_start_time("scenario_histories", scenario_id)
        
        # ユーザーメッセージを履歴に追加
        user_entry = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        session_service.add_to_history("scenario_histories", user_entry, scenario_id)
        
        # LLMの初期化と応答生成
        llm = llm_service.initialize_llm(model_name)
        history = histories.get(scenario_id, [])
        
        # ストリーミングレスポンスの生成
        def generate():
            try:
                full_response = ""
                messages = scenario_service.format_messages_for_scenario(
                    scenario, history, message
                )
                
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
                session_service.add_to_history("scenario_histories", ai_entry, scenario_id)
                
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


@scenarios_bp.route("/scenario_clear", methods=["POST"])
@secure_endpoint
def clear_scenario_history():
    """シナリオの会話履歴をクリアする"""
    try:
        data = request.get_json()
        scenario_id = data.get("scenario_id")
        
        if not scenario_id:
            raise ValidationError("シナリオIDが指定されていません", field="scenario_id")
        
        if scenario_id not in SCENARIOS:
            raise ValidationError("無効なシナリオIDです", field="scenario_id")
        
        # 履歴をクリア
        session_service.clear_history("scenario_histories", scenario_id)
        
        return jsonify({
            "message": f"シナリオ '{SCENARIOS[scenario_id]['title']}' の履歴がクリアされました。"
        })
        
    except ValidationError as e:
        return jsonify({"error": str(e), "field": e.field}), 400
    except Exception as e:
        return jsonify({"error": f"履歴のクリア中にエラーが発生しました: {str(e)}"}), 500


@scenarios_bp.route("/scenario_feedback", methods=["POST"])
@secure_endpoint
def get_scenario_feedback():
    """シナリオ練習のフィードバックを生成する"""
    try:
        data = request.get_json()
        scenario_id = data.get("scenario_id")
        model_name = data.get("model", session.get("selected_model", "gemini-1.5-flash"))
        include_strength_analysis = data.get("include_strength_analysis", True)
        
        if not scenario_id or scenario_id not in SCENARIOS:
            raise ValidationError("無効なシナリオIDです", field="scenario_id")
        
        scenario = SCENARIOS[scenario_id]
        histories = session.get("scenario_histories", {})
        history = histories.get(scenario_id, [])
        
        if len(history) < 2:
            raise ValidationError("フィードバックを生成するには、少なくとも1回の会話が必要です")
        
        # フィードバックの生成
        llm = llm_service.initialize_llm(model_name)
        feedback_response = scenario_service.generate_scenario_feedback(
            llm, scenario, history
        )
        
        # 強み分析を含める場合
        if include_strength_analysis:
            # 会話履歴をテキストに変換
            conversation_text = "\n".join([
                f"{'User' if entry['role'] == 'user' else 'Assistant'}: {entry['content']}"
                for entry in history
            ])
            strength_analysis = analyze_user_strengths(conversation_text)
            feedback_response = scenario_service.update_feedback_with_strength_analysis(
                feedback_response, strength_analysis
            )
        
        # フィードバックを履歴に追加
        feedback_entry = {
            "role": "system",
            "content": feedback_response,
            "timestamp": datetime.now().isoformat(),
            "type": "feedback"
        }
        session_service.add_to_history("scenario_histories", feedback_entry, scenario_id)
        
        return jsonify({"feedback": feedback_response})
        
    except ValidationError as e:
        return jsonify({"error": str(e), "field": e.field}), 400
    except Exception as e:
        return jsonify({"error": f"フィードバックの生成中にエラーが発生しました: {str(e)}"}), 500


@scenarios_bp.route("/get_assist", methods=["POST"])
def get_assist() -> Any:
    """シナリオ練習中のアシストを提供する"""
    try:
        data = request.get_json()
        scenario_id = data.get("scenario_id")
        model_name = data.get("model", session.get("selected_model", "gemini-1.5-flash"))
        
        if not scenario_id or scenario_id not in SCENARIOS:
            raise ValidationError("無効なシナリオIDです", field="scenario_id")
        
        scenario = SCENARIOS[scenario_id]
        histories = session.get("scenario_histories", {})
        history = histories.get(scenario_id, [])
        
        # アシストメッセージの生成
        llm = llm_service.initialize_llm(model_name)
        assist_message = scenario_service.generate_assist_message(
            llm, scenario, history
        )
        
        return jsonify({"assist": assist_message})
        
    except ValidationError as e:
        return jsonify({"error": str(e), "field": e.field}), 400
    except Exception as e:
        return jsonify({"error": f"アシストの生成中にエラーが発生しました: {str(e)}"}), 500