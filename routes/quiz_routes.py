"""
観戦モードクイズ API ルート
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from services.gamification_service import GamificationService
from services.quiz_service import QuizService
from services.session_service import SessionService
from services.user_data_service import UserDataService

quiz_bp = Blueprint("quiz", __name__, url_prefix="/api/quiz")

_SESSION_KEY = "gamification_quiz_session"


_session_svc = SessionService()


def _uid() -> str:
    return _session_svc.get_user_id()


@quiz_bp.route("/generate", methods=["POST"])
def generate():
    """クイズ生成"""
    payload = request.get_json(silent=True) or {}
    ctx = payload.get("context") or []
    qz = QuizService().generate_quiz(ctx)
    sess = session.get(_SESSION_KEY) or {"results": []}
    sess["last_quiz"] = qz
    session[_SESSION_KEY] = sess
    return jsonify({"quiz": qz})


@quiz_bp.route("/answer", methods=["POST"])
def answer():
    """クイズ回答・評価"""
    payload = request.get_json(silent=True) or {}
    user_answer = payload.get("user_answer")
    ctx = payload.get("context") or []

    sess = session.get(_SESSION_KEY) or {"results": []}
    quiz = sess.get("last_quiz")
    if quiz is None:
        quiz = payload.get("quiz")
    if quiz is None:
        return jsonify({"error": "quiz is required"}), 400
    try:
        ua = int(user_answer)
    except (TypeError, ValueError):
        return jsonify({"error": "user_answer must be int"}), 400
    svc = QuizService()
    result = svc.evaluate_answer(quiz, ua, ctx)

    uid = _uid()
    uds = UserDataService()
    if result.get("is_correct"):
        bonus = result.get("bonus_xp", 0)
        if bonus > 0:
            gs = GamificationService(uds)
            axes = ("empathy", "clarity", "active_listening", "adaptability", "positivity", "professionalism")
            base = bonus // len(axes)
            remainder = bonus % len(axes)
            xp_dist = {a: base + (1 if i < remainder else 0) for i, a in enumerate(axes)}
            gs.add_xp(uid, xp_dist, "quiz_bonus")
    data = uds.get_user_data(uid)
    stats = data.setdefault("stats", {})
    stats["total_quizzes_answered"] = int(stats.get("total_quizzes_answered", 0) or 0) + 1
    if result.get("is_correct"):
        stats["total_quizzes_correct"] = int(stats.get("total_quizzes_correct", 0) or 0) + 1
    uds.save_user_data(uid, data)

    rec = {
        "is_correct": result.get("is_correct"),
        "question": quiz.get("question"),
    }
    sess.setdefault("results", []).append(rec)
    session[_SESSION_KEY] = sess
    return jsonify(result)


@quiz_bp.route("/summary", methods=["GET"])
def summary():
    """セッションサマリー"""
    uid = _uid()
    sess = session.get(_SESSION_KEY) or {}
    quizzes = sess.get("results") or []
    svc = QuizService()
    data = svc.get_session_summary(uid, quizzes)
    return jsonify(data)
