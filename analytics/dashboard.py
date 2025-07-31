"""
学習成果ダッシュボード

ユーザーの学習進捗と成果を可視化するダッシュボード機能
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import redis
from collections import defaultdict
import numpy as np

from models import db, StrengthAnalysisResult, PracticeSession, ConversationLog
from config.config import get_config


class LearningDashboard:
    """学習成果の統合ダッシュボード"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = redis.Redis(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            db=self.config.REDIS_DB,
            decode_responses=True
        )
        
    def get_user_overview(self, user_id: int) -> Dict[str, Any]:
        """
        ユーザーの学習概要を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            学習概要データ
        """
        # キャッシュチェック
        cache_key = f"dashboard:overview:{user_id}"
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        
        # データ集計
        overview = {
            'total_sessions': self._get_total_sessions(user_id),
            'total_practice_time': self._get_total_practice_time(user_id),
            'skill_summary': self._get_skill_summary(user_id),
            'recent_activity': self._get_recent_activity(user_id),
            'achievements': self._get_achievements(user_id),
            'recommendation': self._get_personalized_recommendation(user_id)
        }
        
        # キャッシュに保存（1時間）
        self.redis_client.setex(
            cache_key, 
            3600, 
            json.dumps(overview, ensure_ascii=False, default=str)
        )
        
        return overview
    
    def get_skill_progression(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        スキルの成長推移を取得
        
        Args:
            user_id: ユーザーID
            days: 取得する日数（デフォルト30日）
            
        Returns:
            スキル成長データ
        """
        # 期間の計算
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 分析結果を取得
        results = StrengthAnalysisResult.query.filter(
            StrengthAnalysisResult.user_id == user_id,
            StrengthAnalysisResult.created_at >= start_date
        ).order_by(StrengthAnalysisResult.created_at).all()
        
        # スキル別の推移データを構築
        skill_data = defaultdict(list)
        dates = []
        
        for result in results:
            if result.analysis_result:
                scores = result.analysis_result.get('scores', {})
                dates.append(result.created_at.isoformat())
                
                for skill, score in scores.items():
                    skill_data[skill].append({
                        'date': result.created_at.isoformat(),
                        'score': score
                    })
        
        # 成長率の計算
        growth_rates = {}
        for skill, data in skill_data.items():
            if len(data) >= 2:
                initial_score = data[0]['score']
                final_score = data[-1]['score']
                growth_rate = ((final_score - initial_score) / initial_score) * 100
                growth_rates[skill] = round(growth_rate, 1)
            else:
                growth_rates[skill] = 0
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'skill_trends': dict(skill_data),
            'growth_rates': growth_rates,
            'total_analyses': len(results)
        }
    
    def get_scenario_performance(self, user_id: int) -> Dict[str, Any]:
        """
        シナリオ別のパフォーマンス分析
        
        Args:
            user_id: ユーザーID
            
        Returns:
            シナリオ別パフォーマンスデータ
        """
        # 会話履歴からシナリオ別のデータを集計
        conversations = PracticeSession.query.filter_by(
            user_id=user_id,
            session_type='scenario'
        ).all()
        
        scenario_stats = defaultdict(lambda: {
            'count': 0,
            'total_messages': 0,
            'avg_message_length': 0,
            'completion_rate': 0,
            'skill_improvements': defaultdict(list)
        })
        
        for conv in conversations:
            scenario_id = conv.scenario_id
            if scenario_id:
                stats = scenario_stats[scenario_id]
                stats['count'] += 1
                
                # メッセージ数と長さの計算
                conv_logs = ConversationLog.query.filter_by(session_id=conv.id).all()
                if conv_logs:
                    user_messages = [log for log in conv_logs if log.speaker == 'user']
                    stats['total_messages'] += len(user_messages)
                    
                    if user_messages:
                        avg_length = sum(len(log.message) for log in user_messages) / len(user_messages)
                        stats['avg_message_length'] = (
                            stats['avg_message_length'] * (stats['count'] - 1) + avg_length
                        ) / stats['count']
                
                # 関連する強み分析結果があれば追加
                analysis = StrengthAnalysisResult.query.filter_by(
                    user_id=user_id,
                    session_id=conv.id
                ).first()
                
                if analysis and analysis.analysis_result:
                    scores = analysis.analysis_result.get('scores', {})
                    for skill, score in scores.items():
                        stats['skill_improvements'][skill].append(score)
        
        # 各シナリオの平均スキルスコアを計算
        for scenario_id, stats in scenario_stats.items():
            for skill, scores in stats['skill_improvements'].items():
                if scores:
                    stats['skill_improvements'][skill] = round(np.mean(scores), 1)
        
        return {
            'scenarios': dict(scenario_stats),
            'most_practiced': self._get_most_practiced_scenarios(scenario_stats),
            'best_performing': self._get_best_performing_scenarios(scenario_stats),
            'recommendations': self._get_scenario_recommendations(user_id, scenario_stats)
        }
    
    def get_comparative_analysis(self, user_id: int) -> Dict[str, Any]:
        """
        他のユーザーとの比較分析（匿名化）
        
        Args:
            user_id: ユーザーID
            
        Returns:
            比較分析データ
        """
        # 自分の最新スコア
        user_latest = StrengthAnalysisResult.query.filter_by(
            user_id=user_id
        ).order_by(StrengthAnalysisResult.created_at.desc()).first()
        
        if not user_latest or not user_latest.analysis_result:
            return {'error': 'No analysis data available'}
        
        user_scores = user_latest.analysis_result.get('scores', {})
        
        # 全ユーザーの平均スコアを計算（匿名化）
        all_results = db.session.query(StrengthAnalysisResult).filter(
            StrengthAnalysisResult.created_at >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        skill_aggregates = defaultdict(list)
        for result in all_results:
            if result.analysis_result:
                scores = result.analysis_result.get('scores', {})
                for skill, score in scores.items():
                    skill_aggregates[skill].append(score)
        
        # 統計情報の計算
        comparison = {}
        for skill, scores in skill_aggregates.items():
            if scores:
                comparison[skill] = {
                    'user_score': user_scores.get(skill, 0),
                    'average': round(np.mean(scores), 1),
                    'percentile': round(
                        (sum(1 for s in scores if s < user_scores.get(skill, 0)) / len(scores)) * 100, 
                        1
                    ),
                    'min': min(scores),
                    'max': max(scores),
                    'std_dev': round(np.std(scores), 1)
                }
        
        return {
            'comparison': comparison,
            'total_users': len(set(r.user_id for r in all_results)),
            'analysis_period': '30 days',
            'strengths': self._identify_relative_strengths(comparison),
            'areas_for_improvement': self._identify_improvement_areas(comparison)
        }
    
    # プライベートメソッド
    def _get_total_sessions(self, user_id: int) -> int:
        """総セッション数を取得"""
        return PracticeSession.query.filter_by(user_id=user_id).count()
    
    def _get_total_practice_time(self, user_id: int) -> int:
        """総練習時間を取得（分単位）"""
        conversations = PracticeSession.query.filter_by(user_id=user_id).all()
        total_minutes = 0
        
        for conv in conversations:
            if conv.started_at and conv.ended_at:
                duration = (conv.ended_at - conv.started_at).total_seconds() / 60
                total_minutes += duration
        
        return int(total_minutes)
    
    def _get_skill_summary(self, user_id: int) -> Dict[str, Any]:
        """スキルサマリーを取得"""
        latest_result = StrengthAnalysisResult.query.filter_by(
            user_id=user_id
        ).order_by(StrengthAnalysisResult.created_at.desc()).first()
        
        if not latest_result or not latest_result.analysis_result:
            return {}
        
        scores = latest_result.analysis_result.get('scores', {})
        return {
            'current_scores': scores,
            'top_skills': sorted(
                scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3],
            'improvement_areas': sorted(
                scores.items(), 
                key=lambda x: x[1]
            )[:3]
        }
    
    def _get_recent_activity(self, user_id: int) -> List[Dict[str, Any]]:
        """最近のアクティビティを取得"""
        recent_conversations = PracticeSession.query.filter_by(
            user_id=user_id
        ).order_by(PracticeSession.started_at.desc()).limit(5).all()
        
        activities = []
        for conv in recent_conversations:
            # メッセージ数を取得
            message_count = ConversationLog.query.filter_by(session_id=conv.id).count()
            activities.append({
                'date': conv.started_at.isoformat(),
                'session_type': conv.session_type.value if hasattr(conv.session_type, 'value') else conv.session_type,
                'scenario_id': conv.scenario_id,
                'message_count': message_count
            })
        
        return activities
    
    def _get_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """達成したアチーブメントを取得"""
        # TODO: アチーブメントシステムの実装
        return []
    
    def _get_personalized_recommendation(self, user_id: int) -> Dict[str, Any]:
        """パーソナライズされた推奨事項を生成"""
        skill_summary = self._get_skill_summary(user_id)
        
        if not skill_summary:
            return {
                'message': '練習を始めて、あなたの強みを発見しましょう！',
                'next_action': 'scenario_practice'
            }
        
        improvement_areas = skill_summary.get('improvement_areas', [])
        if improvement_areas:
            weakest_skill = improvement_areas[0][0]
            return {
                'message': f'{weakest_skill}を強化する練習をおすすめします',
                'next_action': 'focused_practice',
                'skill_focus': weakest_skill
            }
        
        return {
            'message': 'すばらしい成長です！新しいシナリオに挑戦してみましょう',
            'next_action': 'advanced_scenario'
        }
    
    def _get_most_practiced_scenarios(self, scenario_stats: Dict) -> List[str]:
        """最も練習されたシナリオを取得"""
        sorted_scenarios = sorted(
            scenario_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        return [s[0] for s in sorted_scenarios[:3]]
    
    def _get_best_performing_scenarios(self, scenario_stats: Dict) -> List[str]:
        """最もパフォーマンスが良いシナリオを取得"""
        # 平均スキルスコアが高いシナリオを抽出
        scenario_scores = []
        for scenario_id, stats in scenario_stats.items():
            if stats['skill_improvements']:
                avg_score = np.mean(list(stats['skill_improvements'].values()))
                scenario_scores.append((scenario_id, avg_score))
        
        sorted_scenarios = sorted(scenario_scores, key=lambda x: x[1], reverse=True)
        return [s[0] for s in sorted_scenarios[:3]]
    
    def _get_scenario_recommendations(self, user_id: int, scenario_stats: Dict) -> List[str]:
        """推奨シナリオを取得"""
        # 練習していないか、練習回数が少ないシナリオを推奨
        all_scenarios = set(f'scenario{i}' for i in range(1, 36))
        practiced_scenarios = set(scenario_stats.keys())
        unpracticed = all_scenarios - practiced_scenarios
        
        if unpracticed:
            return list(unpracticed)[:3]
        
        # 練習回数が少ないシナリオを推奨
        sorted_scenarios = sorted(
            scenario_stats.items(),
            key=lambda x: x[1]['count']
        )
        return [s[0] for s in sorted_scenarios[:3]]
    
    def _identify_relative_strengths(self, comparison: Dict) -> List[str]:
        """相対的な強みを特定"""
        strengths = []
        for skill, data in comparison.items():
            if data['percentile'] >= 75:
                strengths.append(skill)
        return sorted(strengths, key=lambda s: comparison[s]['percentile'], reverse=True)
    
    def _identify_improvement_areas(self, comparison: Dict) -> List[str]:
        """改善が必要な領域を特定"""
        areas = []
        for skill, data in comparison.items():
            if data['percentile'] < 50:
                areas.append(skill)
        return sorted(areas, key=lambda s: comparison[s]['percentile'])