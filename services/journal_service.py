"""
学習履歴（ジャーナル）サービス
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from models import db, User
from errors import NotFoundError


class JournalService:
    """学習履歴関連の操作を管理するサービスクラス"""
    
    def get_user_history(self, user_id: int) -> List[Dict[str, Any]]:
        """ユーザーの学習履歴を取得"""
        # ダミーデータ（実際の実装では、データベースから取得）
        history = [
            {
                "id": 1,
                "date": datetime.now() - timedelta(hours=2),
                "type": "scenario",
                "title": "上司への進捗報告",
                "duration": 15,
                "score": 85,
                "feedback_summary": "明確な説明ができていました",
                "improvements": ["数字を使った具体的な説明", "結論から話す"],
                "tags": ["報告", "上司", "進捗"]
            },
            {
                "id": 2,
                "date": datetime.now() - timedelta(days=1),
                "type": "chat",
                "title": "同僚との雑談練習",
                "duration": 10,
                "score": None,
                "feedback_summary": "自然な会話ができていました",
                "improvements": ["話題の広げ方", "相手への質問"],
                "tags": ["雑談", "同僚"]
            },
            {
                "id": 3,
                "date": datetime.now() - timedelta(days=2),
                "type": "watch",
                "title": "プロジェクト会議の観戦",
                "duration": 20,
                "score": None,
                "feedback_summary": "効果的な会議進行を学習",
                "improvements": [],
                "tags": ["会議", "観戦", "学習"]
            },
            {
                "id": 4,
                "date": datetime.now() - timedelta(days=3),
                "type": "scenario",
                "title": "クライアントへの提案",
                "duration": 25,
                "score": 78,
                "feedback_summary": "説得力のある提案でした",
                "improvements": ["相手のニーズの確認", "代替案の提示"],
                "tags": ["提案", "クライアント", "営業"]
            }
        ]
        
        return history
    
    def calculate_user_stats(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ユーザーの統計情報を計算"""
        if not history:
            return {
                "total_sessions": 0,
                "total_time": 0,
                "average_score": 0,
                "most_practiced_type": None,
                "favorite_tags": [],
                "improvement_areas": []
            }
        
        # 統計を計算
        total_sessions = len(history)
        total_time = sum(item["duration"] for item in history)
        
        # スコアがあるセッションの平均スコアを計算
        scored_sessions = [item for item in history if item.get("score") is not None]
        average_score = (
            sum(item["score"] for item in scored_sessions) / len(scored_sessions)
            if scored_sessions else 0
        )
        
        # タイプ別の集計
        type_counts = defaultdict(int)
        for item in history:
            type_counts[item["type"]] += 1
        most_practiced_type = max(type_counts.items(), key=lambda x: x[1])[0]
        
        # タグの集計
        tag_counts = defaultdict(int)
        for item in history:
            for tag in item.get("tags", []):
                tag_counts[tag] += 1
        favorite_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 改善エリアの集計
        improvement_counts = defaultdict(int)
        for item in history:
            for improvement in item.get("improvements", []):
                improvement_counts[improvement] += 1
        common_improvements = sorted(
            improvement_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        return {
            "total_sessions": total_sessions,
            "total_time": total_time,
            "average_score": round(average_score, 1),
            "most_practiced_type": most_practiced_type,
            "favorite_tags": [tag for tag, _ in favorite_tags],
            "improvement_areas": [imp for imp, _ in common_improvements],
            "type_breakdown": dict(type_counts),
            "sessions_this_week": self._count_sessions_this_week(history),
            "streak_days": self._calculate_streak(history)
        }
    
    def get_recent_activities(
        self, 
        user_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """最近のアクティビティを取得"""
        # 全履歴を取得してソート（実際の実装では、データベースでソート）
        all_history = self.get_user_history(user_id)
        sorted_history = sorted(all_history, key=lambda x: x["date"], reverse=True)
        
        # 指定された数だけ返す
        return sorted_history[:limit]
    
    def get_activity_summary(
        self, 
        user_id: int, 
        days: int = 30
    ) -> Dict[str, Any]:
        """指定期間のアクティビティサマリーを取得"""
        cutoff_date = datetime.now() - timedelta(days=days)
        history = self.get_user_history(user_id)
        
        # 期間内のアクティビティをフィルター
        recent_history = [
            item for item in history 
            if item["date"] >= cutoff_date
        ]
        
        # 日別のアクティビティ数を集計
        daily_counts = defaultdict(int)
        for item in recent_history:
            date_key = item["date"].date()
            daily_counts[date_key] += 1
        
        # カレンダー形式のデータを生成
        calendar_data = []
        current_date = datetime.now().date()
        for i in range(days):
            date = current_date - timedelta(days=i)
            calendar_data.append({
                "date": date,
                "count": daily_counts.get(date, 0)
            })
        
        return {
            "period_days": days,
            "total_activities": len(recent_history),
            "active_days": len(daily_counts),
            "calendar_data": calendar_data,
            "busiest_day": max(daily_counts.items(), key=lambda x: x[1])[0] if daily_counts else None,
            "average_per_day": len(recent_history) / days if days > 0 else 0
        }
    
    def save_session_record(
        self,
        user_id: int,
        session_type: str,
        session_data: Dict[str, Any]
    ) -> bool:
        """セッション記録を保存"""
        # 実際の実装では、データベースに保存
        # ここではダミー実装
        print(f"Saving session for user {user_id}: {session_type}")
        print(f"Session data: {session_data}")
        return True
    
    def _count_sessions_this_week(self, history: List[Dict[str, Any]]) -> int:
        """今週のセッション数をカウント"""
        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return sum(1 for item in history if item["date"] >= week_start)
    
    def _calculate_streak(self, history: List[Dict[str, Any]]) -> int:
        """連続練習日数を計算"""
        if not history:
            return 0
        
        # 日付でグループ化
        dates_with_activity = set()
        for item in history:
            dates_with_activity.add(item["date"].date())
        
        # 今日から遡って連続日数をカウント
        streak = 0
        current_date = datetime.now().date()
        
        while current_date in dates_with_activity:
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak