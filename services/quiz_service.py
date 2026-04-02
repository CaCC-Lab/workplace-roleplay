"""
観戦モード中のインタラクティブクイズ（ゲーミフィケーション）
"""

from __future__ import annotations

from typing import Any, Callable, Optional


class QuizService:
    """観戦モード中のインタラクティブクイズ"""

    QUIZ_INTERVAL = 5
    BONUS_XP_CORRECT = 10

    def __init__(
        self,
        user_data_service: Optional[Any] = None,
        llm_service: Optional[Any] = None,
        generate_explanation: Optional[Callable[..., str]] = None,
    ) -> None:
        self._uds = user_data_service
        self._llm = llm_service
        self._explain = generate_explanation

    def should_generate_quiz(self, message_count: int) -> bool:
        """会話数が QUIZ_INTERVAL の正の倍数のときのみ True（0 は除く）"""
        if message_count <= 0:
            return False
        return message_count % self.QUIZ_INTERVAL == 0

    def _fallback_quiz(self) -> dict:
        return {
            "question": "会話の要点として最も適切なものはどれですか？",
            "choices": ["選択肢A", "選択肢B", "選択肢C"],
            "correct_answer": 0,
        }

    def generate_quiz(self, conversation_context: list) -> dict:
        """LLMまたはフォールバックでクイズを生成（3〜4択）"""
        if conversation_context is None:
            conversation_context = []
        try:
            if self._llm is not None and hasattr(self._llm, "generate_quiz_content"):
                raw = self._llm.generate_quiz_content(conversation_context)
                if isinstance(raw, dict) and self._validate_quiz_shape(raw):
                    return raw
                try:
                    from services.gamification_vibelogger import get_gamification_vibe_logger

                    get_gamification_vibe_logger().warning(
                        operation="QuizService.generate_quiz",
                        message="LLM quiz response invalid shape; using fallback",
                        context={"reason": "validation_failed"},
                    )
                except Exception:
                    pass
        except Exception as exc:
            try:
                from services.gamification_vibelogger import get_gamification_vibe_logger

                get_gamification_vibe_logger().warning(
                    operation="QuizService.generate_quiz",
                    message="LLM quiz generation failed; using fallback",
                    context={"error": str(exc)},
                )
            except Exception:
                pass
        return self._fallback_quiz()

    def _validate_quiz_shape(self, q: dict) -> bool:
        ch = q.get("choices") or []
        if not isinstance(ch, list) or len(ch) < 3 or len(ch) > 4:
            return False
        ca = q.get("correct_answer", -1)
        try:
            ca = int(ca)
        except (TypeError, ValueError):
            return False
        return 0 <= ca < len(ch)

    def evaluate_answer(
        self,
        quiz: dict,
        user_answer: int,
        conversation_context: list,
    ) -> dict:
        """回答評価。正解時はボーナスXP情報を含む"""
        if quiz is None:
            raise TypeError("quiz must not be None")
        choices = quiz.get("choices") or []
        try:
            correct = int(quiz.get("correct_answer", -1))
        except (TypeError, ValueError):
            correct = -1
        is_correct = (
            isinstance(user_answer, int)
            and 0 <= user_answer < len(choices)
            and user_answer == correct
        )
        xp = self.BONUS_XP_CORRECT if is_correct else 0
        explanation = "お疲れさまでした。"
        try:
            if self._explain:
                explanation = self._explain(quiz, is_correct, conversation_context)
            elif self._llm is not None and hasattr(self._llm, "explain_quiz_answer"):
                explanation = self._llm.explain_quiz_answer(quiz, user_answer, conversation_context)
        except Exception:
            explanation = "解説を取得できませんでした。"
        return {
            "is_correct": is_correct,
            "explanation": explanation,
            "bonus_xp": xp,
        }

    def get_session_summary(self, user_id: str, session_quizzes: list) -> dict:
        """セッション終了時のクイズ正答率サマリー"""
        if session_quizzes is None:
            session_quizzes = []
        if len(session_quizzes) == 0:
            return {"accuracy": 0.0, "total": 0, "correct": 0}
        correct_n = sum(1 for q in session_quizzes if q.get("is_correct"))
        total = len(session_quizzes)
        return {
            "accuracy": correct_n / total if total else 0.0,
            "total": total,
            "correct": correct_n,
        }
