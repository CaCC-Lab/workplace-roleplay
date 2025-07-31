"""
分析・統計サービス
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta

from models import db, User
from errors import NotFoundError


class AnalyticsService:
    """分析・統計関連の操作を管理するサービスクラス"""
    
    def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """ユーザーの分析データを取得"""
        user = User.query.get(user_id)
        if not user:
            raise NotFoundError("ユーザーが見つかりません")
        
        # ダミーデータ（実際の実装では、データベースから取得）
        analytics = {
            "user_id": user_id,
            "username": user.username,
            "total_sessions": 25,
            "total_practice_time": 450,  # 分
            "scenarios_completed": 15,
            "chat_sessions": 10,
            "watch_sessions": 5,
            "average_session_duration": 18,  # 分
            "last_activity": datetime.now() - timedelta(days=1),
            "streak_days": 7,
            "preferred_time": "19:00-21:00",
            "most_practiced_category": "会議",
            "improvement_rate": 85.5  # パーセント
        }
        
        return analytics
    
    def get_scenario_progress(self, user_id: int, scenario_id: str) -> Dict[str, Any]:
        """特定のシナリオの進捗状況を取得"""
        # ダミーデータ（実際の実装では、データベースから取得）
        progress = {
            "scenario_id": scenario_id,
            "user_id": user_id,
            "completion_count": 3,
            "last_completed": datetime.now() - timedelta(days=2),
            "average_score": 82.5,
            "best_score": 90,
            "improvement_trend": "increasing",
            "time_spent": 45,  # 分
            "feedback_points": [
                "アクティブリスニングが改善されています",
                "共感的な言葉遣いが増えました",
                "質問のタイミングが適切になりました"
            ]
        }
        
        return progress
    
    def get_progress_summary(self, user_id: int) -> Dict[str, Any]:
        """ユーザーの進捗サマリーを取得"""
        # ダミーデータ（実際の実装では、データベースから計算）
        summary = {
            "overall_progress": 65,  # パーセント
            "scenarios": {
                "total": 30,
                "completed": 15,
                "in_progress": 5,
                "not_started": 10
            },
            "skills": {
                "listening": 75,
                "empathy": 80,
                "clarity": 70,
                "persuasion": 60,
                "conflict_resolution": 55
            },
            "recent_achievements": [
                {
                    "title": "連続7日間練習",
                    "date": datetime.now() - timedelta(days=1),
                    "icon": "🔥"
                },
                {
                    "title": "難しいシナリオをクリア",
                    "date": datetime.now() - timedelta(days=3),
                    "icon": "🏆"
                }
            ],
            "next_recommendations": [
                "コンフリクト解決のシナリオに挑戦",
                "プレゼンテーションスキルの練習",
                "フィードバックの与え方を学習"
            ]
        }
        
        return summary
    
    def get_skill_assessment(self, user_id: int) -> Dict[str, Any]:
        """スキル評価を取得"""
        # ダミーデータ（実際の実装では、会話分析から算出）
        assessment = {
            "assessment_date": datetime.now(),
            "overall_level": "中級",
            "skills": [
                {
                    "name": "アクティブリスニング",
                    "score": 75,
                    "level": "良好",
                    "trend": "improving",
                    "description": "相手の話をしっかり聞き、適切な相槌を打てています"
                },
                {
                    "name": "共感力",
                    "score": 80,
                    "level": "優秀",
                    "trend": "stable",
                    "description": "相手の感情を理解し、適切に反応できています"
                },
                {
                    "name": "明確な表現",
                    "score": 70,
                    "level": "良好",
                    "trend": "improving",
                    "description": "意図を明確に伝える能力が向上しています"
                },
                {
                    "name": "説得力",
                    "score": 60,
                    "level": "発展中",
                    "trend": "improving",
                    "description": "論理的な説明と感情的な訴求のバランスが必要です"
                },
                {
                    "name": "コンフリクト解決",
                    "score": 55,
                    "level": "発展中",
                    "trend": "stable",
                    "description": "対立状況での冷静な対応を練習しましょう"
                }
            ],
            "strengths": [
                "共感的なコミュニケーション",
                "傾聴スキル",
                "前向きな態度"
            ],
            "areas_for_improvement": [
                "論理的な説明力",
                "難しい会話での対応",
                "時間管理とペース配分"
            ]
        }
        
        return assessment
    
    def get_growth_data(self, user_id: int) -> Dict[str, Any]:
        """成長データを取得"""
        # ダミーデータ（実際の実装では、時系列データから生成）
        growth_data = {
            "user_id": user_id,
            "start_date": datetime.now() - timedelta(days=90),
            "current_date": datetime.now(),
            "overall_improvement": 45,  # パーセント
            "monthly_progress": [
                {"month": "1月", "score": 55},
                {"month": "2月", "score": 62},
                {"month": "3月", "score": 70},
                {"month": "4月", "score": 80}
            ],
            "skill_progression": {
                "listening": [60, 65, 70, 75],
                "empathy": [65, 70, 75, 80],
                "clarity": [55, 60, 65, 70],
                "persuasion": [45, 50, 55, 60],
                "conflict_resolution": [40, 45, 50, 55]
            },
            "practice_frequency": {
                "daily_average": 1.5,  # セッション数
                "weekly_total": 10.5,  # セッション数
                "consistency_score": 85  # パーセント
            }
        }
        
        return growth_data
    
    def get_milestones(self, user_id: int) -> List[Dict[str, Any]]:
        """達成したマイルストーンを取得"""
        milestones = [
            {
                "id": 1,
                "title": "初めての練習",
                "description": "最初のシナリオを完了しました",
                "achieved_date": datetime.now() - timedelta(days=89),
                "icon": "🎯",
                "category": "beginner"
            },
            {
                "id": 2,
                "title": "10回練習達成",
                "description": "10回の練習セッションを完了",
                "achieved_date": datetime.now() - timedelta(days=60),
                "icon": "📚",
                "category": "practice"
            },
            {
                "id": 3,
                "title": "週間戦士",
                "description": "1週間連続で練習",
                "achieved_date": datetime.now() - timedelta(days=30),
                "icon": "🗓️",
                "category": "consistency"
            },
            {
                "id": 4,
                "title": "スキルマスター",
                "description": "1つのスキルで80点以上を達成",
                "achieved_date": datetime.now() - timedelta(days=14),
                "icon": "🏅",
                "category": "skill"
            },
            {
                "id": 5,
                "title": "改善の達人",
                "description": "3ヶ月で40%以上の改善",
                "achieved_date": datetime.now() - timedelta(days=7),
                "icon": "📈",
                "category": "improvement"
            }
        ]
        
        return milestones
    
    def get_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """パーソナライズされた推奨事項を取得"""
        recommendations = [
            {
                "type": "scenario",
                "title": "難しい顧客への対応",
                "reason": "コンフリクト解決スキルの向上に効果的です",
                "difficulty": "上級",
                "estimated_time": 20,
                "priority": "high"
            },
            {
                "type": "skill_focus",
                "title": "論理的な説明力を鍛える",
                "reason": "説得力スコアが60点なので、改善の余地があります",
                "exercises": ["PREP法の練習", "数字を使った説明"],
                "priority": "medium"
            },
            {
                "type": "practice_time",
                "title": "朝の時間帯での練習",
                "reason": "新しい時間帯での練習は脳の活性化に効果的です",
                "suggested_time": "7:00-8:00",
                "priority": "low"
            },
            {
                "type": "challenge",
                "title": "上級シナリオウィーク",
                "reason": "現在のスキルレベルなら挑戦可能です",
                "duration": "1週間",
                "reward": "上級バッジ",
                "priority": "medium"
            }
        ]
        
        return recommendations