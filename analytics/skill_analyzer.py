"""
スキル進捗分析

個別スキルの詳細な分析と進捗追跡
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from collections import defaultdict
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from models import db, StrengthAnalysisResult, PracticeSession


class SkillProgressAnalyzer:
    """スキル進捗の詳細分析"""
    
    # スキル定義
    SKILL_DEFINITIONS = {
        'empathy': {
            'name': '共感力',
            'description': '相手の気持ちを理解し、適切に反応する能力',
            'indicators': ['感情理解', '配慮表現', '共感的応答']
        },
        'clarity': {
            'name': '明確性',
            'description': '分かりやすく論理的に伝える能力',
            'indicators': ['論理構成', '簡潔性', '要点整理']
        },
        'active_listening': {
            'name': '傾聴力',
            'description': '相手の話を注意深く聞き、理解を示す能力',
            'indicators': ['質問力', '要約力', '確認行動']
        },
        'adaptability': {
            'name': '適応力',
            'description': '状況に応じて柔軟に対応する能力',
            'indicators': ['状況判断', '柔軟な対応', '相手への配慮']
        },
        'positivity': {
            'name': '前向きさ',
            'description': '建設的で前向きな姿勢を保つ能力',
            'indicators': ['ポジティブ表現', '建設的提案', '励まし']
        },
        'professionalism': {
            'name': 'プロフェッショナリズム',
            'description': '職場での適切な振る舞いと判断力',
            'indicators': ['敬語使用', 'ビジネスマナー', '責任感']
        }
    }
    
    def analyze_skill_progress(self, user_id: int, skill_name: str, 
                             days: int = 30) -> Dict[str, Any]:
        """
        特定スキルの詳細な進捗分析
        
        Args:
            user_id: ユーザーID
            skill_name: スキル名
            days: 分析期間（日数）
            
        Returns:
            スキル進捗の詳細分析結果
        """
        if skill_name not in self.SKILL_DEFINITIONS:
            return {'error': f'Unknown skill: {skill_name}'}
        
        # 期間設定
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 分析結果を取得（関連データを事前にロード）
        results = StrengthAnalysisResult.query.filter(
            StrengthAnalysisResult.user_id == user_id,
            StrengthAnalysisResult.created_at >= start_date
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).order_by(StrengthAnalysisResult.created_at).all()
        
        # スキルスコアの抽出
        skill_scores = []
        timestamps = []
        
        for result in results:
            if result.analysis_result:
                scores = result.analysis_result.get('scores', {})
                if skill_name in scores:
                    skill_scores.append(scores[skill_name])
                    timestamps.append(result.created_at)
        
        if not skill_scores:
            return {
                'skill': skill_name,
                'error': 'No data available for this skill'
            }
        
        # 統計分析
        analysis = {
            'skill': skill_name,
            'skill_info': self.SKILL_DEFINITIONS[skill_name],
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'statistics': self._calculate_statistics(skill_scores),
            'trend': self._analyze_trend(skill_scores, timestamps),
            'consistency': self._analyze_consistency(skill_scores, timestamps),
            'milestones': self._identify_milestones(skill_scores, timestamps),
            'practice_patterns': self._analyze_practice_patterns(user_id, skill_name, start_date),
            'improvement_suggestions': self._generate_improvement_suggestions(skill_name, skill_scores)
        }
        
        return analysis
    
    def compare_skills(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        全スキルの比較分析
        
        Args:
            user_id: ユーザーID
            days: 分析期間（日数）
            
        Returns:
            スキル間の比較分析結果
        """
        # 最新の分析結果を取得（関連データを事前にロード）
        latest_result = StrengthAnalysisResult.query.filter_by(
            user_id=user_id
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).order_by(StrengthAnalysisResult.created_at.desc()).first()
        
        if not latest_result or not latest_result.analysis_result:
            return {'error': 'No analysis data available'}
        
        current_scores = latest_result.analysis_result.get('scores', {})
        
        # 期間内の全データを取得
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        results = StrengthAnalysisResult.query.filter(
            StrengthAnalysisResult.user_id == user_id,
            StrengthAnalysisResult.created_at >= start_date
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).all()
        
        # スキル別の成長率を計算
        skill_growth = {}
        for skill in self.SKILL_DEFINITIONS.keys():
            scores = []
            for result in results:
                if result.analysis_result:
                    score = result.analysis_result.get('scores', {}).get(skill)
                    if score is not None:
                        scores.append(score)
            
            if len(scores) >= 2:
                growth_rate = ((scores[-1] - scores[0]) / scores[0]) * 100
                skill_growth[skill] = {
                    'initial': scores[0],
                    'current': scores[-1],
                    'growth_rate': round(growth_rate, 1),
                    'trend': 'improving' if growth_rate > 0 else 'declining'
                }
            else:
                skill_growth[skill] = {
                    'current': current_scores.get(skill, 0),
                    'growth_rate': 0,
                    'trend': 'insufficient_data'
                }
        
        # バランス分析
        balance_analysis = self._analyze_skill_balance(current_scores)
        
        return {
            'current_scores': current_scores,
            'skill_growth': skill_growth,
            'balance_analysis': balance_analysis,
            'strongest_skills': self._get_top_skills(current_scores, 3),
            'weakest_skills': self._get_bottom_skills(current_scores, 3),
            'most_improved': self._get_most_improved_skills(skill_growth, 3),
            'recommendations': self._generate_skill_recommendations(current_scores, skill_growth)
        }
    
    def get_skill_correlations(self, user_id: int) -> Dict[str, Any]:
        """
        スキル間の相関関係を分析
        
        Args:
            user_id: ユーザーID
            
        Returns:
            スキル相関分析結果
        """
        # 全分析結果を取得（関連データを事前にロード）
        results = StrengthAnalysisResult.query.filter_by(
            user_id=user_id
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).all()
        
        if len(results) < 5:
            return {'error': 'Insufficient data for correlation analysis'}
        
        # スキルスコアの行列を作成
        skill_matrix = defaultdict(list)
        for result in results:
            if result.analysis_result:
                scores = result.analysis_result.get('scores', {})
                for skill in self.SKILL_DEFINITIONS.keys():
                    skill_matrix[skill].append(scores.get(skill, 0))
        
        # 相関係数を計算
        correlations = {}
        skills = list(self.SKILL_DEFINITIONS.keys())
        
        for i, skill1 in enumerate(skills):
            correlations[skill1] = {}
            for j, skill2 in enumerate(skills):
                if i != j:
                    corr = np.corrcoef(skill_matrix[skill1], skill_matrix[skill2])[0, 1]
                    correlations[skill1][skill2] = round(corr, 3)
        
        # 強い相関を特定
        strong_correlations = []
        for skill1, corr_dict in correlations.items():
            for skill2, corr_value in corr_dict.items():
                if abs(corr_value) > 0.7:
                    strong_correlations.append({
                        'skill1': skill1,
                        'skill2': skill2,
                        'correlation': corr_value,
                        'relationship': 'positive' if corr_value > 0 else 'negative'
                    })
        
        return {
            'correlations': correlations,
            'strong_correlations': strong_correlations,
            'insights': self._generate_correlation_insights(strong_correlations)
        }
    
    # プライベートメソッド
    def _calculate_statistics(self, scores: List[float]) -> Dict[str, float]:
        """統計情報を計算"""
        return {
            'mean': round(np.mean(scores), 1),
            'median': round(np.median(scores), 1),
            'std_dev': round(np.std(scores), 1),
            'min': round(min(scores), 1),
            'max': round(max(scores), 1),
            'range': round(max(scores) - min(scores), 1)
        }
    
    def _analyze_trend(self, scores: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """トレンド分析"""
        if len(scores) < 2:
            return {'trend': 'insufficient_data'}
        
        # 線形回帰で傾向を分析
        x = np.arange(len(scores))
        coefficients = np.polyfit(x, scores, 1)
        slope = coefficients[0]
        
        # 移動平均
        window_size = min(3, len(scores))
        moving_avg = []
        for i in range(len(scores) - window_size + 1):
            avg = np.mean(scores[i:i + window_size])
            moving_avg.append(round(avg, 1))
        
        return {
            'direction': 'improving' if slope > 0.5 else 'declining' if slope < -0.5 else 'stable',
            'slope': round(slope, 2),
            'moving_average': moving_avg,
            'recent_change': round(scores[-1] - scores[-2], 1) if len(scores) >= 2 else 0
        }
    
    def _analyze_consistency(self, scores: List[float], timestamps: List[datetime]) -> Dict[str, Any]:
        """一貫性の分析"""
        if len(scores) < 3:
            return {'consistency': 'insufficient_data'}
        
        # 変動係数（CV）を計算
        cv = np.std(scores) / np.mean(scores) if np.mean(scores) > 0 else 0
        
        # 練習間隔の分析
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).days
            intervals.append(interval)
        
        avg_interval = np.mean(intervals) if intervals else 0
        
        return {
            'variability': 'low' if cv < 0.1 else 'medium' if cv < 0.2 else 'high',
            'coefficient_of_variation': round(cv, 3),
            'average_practice_interval': round(avg_interval, 1),
            'regular_practice': avg_interval < 3
        }
    
    def _identify_milestones(self, scores: List[float], timestamps: List[datetime]) -> List[Dict[str, Any]]:
        """マイルストーンを特定"""
        milestones = []
        
        # 最高スコア達成
        max_score = max(scores)
        max_index = scores.index(max_score)
        milestones.append({
            'type': 'highest_score',
            'score': max_score,
            'date': timestamps[max_index].isoformat(),
            'achievement': f'最高スコア {max_score} を達成'
        })
        
        # 大幅な改善
        for i in range(1, len(scores)):
            improvement = scores[i] - scores[i-1]
            if improvement >= 10:
                milestones.append({
                    'type': 'significant_improvement',
                    'score': scores[i],
                    'date': timestamps[i].isoformat(),
                    'achievement': f'{improvement:.1f}ポイントの改善'
                })
        
        # スコア到達
        thresholds = [60, 70, 80, 90]
        for threshold in thresholds:
            for i, score in enumerate(scores):
                if score >= threshold and (i == 0 or scores[i-1] < threshold):
                    milestones.append({
                        'type': 'threshold_reached',
                        'score': score,
                        'date': timestamps[i].isoformat(),
                        'achievement': f'{threshold}点を突破'
                    })
        
        return sorted(milestones, key=lambda x: x['date'], reverse=True)[:5]
    
    def _analyze_practice_patterns(self, user_id: int, skill_name: str, 
                                 start_date: datetime) -> Dict[str, Any]:
        """練習パターンの分析"""
        # 会話履歴を取得（関連データを事前にロード）
        conversations = PracticeSession.query.filter(
            PracticeSession.user_id == user_id,
            PracticeSession.started_at >= start_date
        ).options(
            joinedload(PracticeSession.user),
            joinedload(PracticeSession.scenario),
            selectinload(PracticeSession.logs),
            joinedload(PracticeSession.analysis)
        ).all()
        
        # 曜日別・時間帯別の練習回数
        weekday_counts = defaultdict(int)
        hour_counts = defaultdict(int)
        
        for conv in conversations:
            weekday_counts[conv.started_at.weekday()] += 1
            hour_counts[conv.started_at.hour] += 1
        
        # 最も練習している曜日と時間帯
        if weekday_counts:
            best_weekday = max(weekday_counts.items(), key=lambda x: x[1])
            weekdays = ['月', '火', '水', '木', '金', '土', '日']
            best_weekday_name = weekdays[best_weekday[0]]
        else:
            best_weekday_name = 'データなし'
        
        if hour_counts:
            best_hour = max(hour_counts.items(), key=lambda x: x[1])
            best_time_slot = f'{best_hour[0]}:00-{best_hour[0]+1}:00'
        else:
            best_time_slot = 'データなし'
        
        return {
            'total_sessions': len(conversations),
            'weekday_distribution': dict(weekday_counts),
            'hour_distribution': dict(hour_counts),
            'best_practice_day': best_weekday_name,
            'best_practice_time': best_time_slot
        }
    
    def _generate_improvement_suggestions(self, skill_name: str, 
                                        scores: List[float]) -> List[str]:
        """改善提案を生成"""
        suggestions = []
        current_score = scores[-1] if scores else 0
        
        # スコアレベルに応じた提案
        if current_score < 50:
            suggestions.append(f'{self.SKILL_DEFINITIONS[skill_name]["name"]}の基礎練習を増やしましょう')
            suggestions.append('関連するシナリオを重点的に練習することをおすすめします')
        elif current_score < 70:
            suggestions.append('練習の頻度を上げて、スキルの定着を図りましょう')
            suggestions.append('フィードバックを参考に、具体的な改善点に取り組みましょう')
        else:
            suggestions.append('高いレベルを維持できています。より難しいシナリオに挑戦してみましょう')
            suggestions.append('他のスキルとのバランスも意識して練習しましょう')
        
        # 変動性に基づく提案
        if len(scores) >= 3:
            cv = np.std(scores) / np.mean(scores) if np.mean(scores) > 0 else 0
            if cv > 0.2:
                suggestions.append('スコアの変動が大きいです。安定した発揮を目指しましょう')
        
        return suggestions[:3]
    
    def _analyze_skill_balance(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """スキルバランスの分析"""
        if not scores:
            return {'balance': 'no_data'}
        
        values = list(scores.values())
        mean_score = np.mean(values)
        std_dev = np.std(values)
        
        # バランス指標（標準偏差が小さいほどバランスが良い）
        balance_score = 100 - (std_dev * 2)  # 0-100のスケール
        
        return {
            'balance_score': round(max(0, balance_score), 1),
            'interpretation': 'excellent' if balance_score > 80 else 'good' if balance_score > 60 else 'needs_improvement',
            'mean_score': round(mean_score, 1),
            'std_deviation': round(std_dev, 1)
        }
    
    def _get_top_skills(self, scores: Dict[str, float], n: int) -> List[Tuple[str, float]]:
        """上位スキルを取得"""
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]
    
    def _get_bottom_skills(self, scores: Dict[str, float], n: int) -> List[Tuple[str, float]]:
        """下位スキルを取得"""
        return sorted(scores.items(), key=lambda x: x[1])[:n]
    
    def _get_most_improved_skills(self, skill_growth: Dict[str, Dict], n: int) -> List[Tuple[str, float]]:
        """最も改善したスキルを取得"""
        improvements = []
        for skill, data in skill_growth.items():
            if 'growth_rate' in data:
                improvements.append((skill, data['growth_rate']))
        return sorted(improvements, key=lambda x: x[1], reverse=True)[:n]
    
    def _generate_skill_recommendations(self, current_scores: Dict[str, float], 
                                      skill_growth: Dict[str, Dict]) -> List[str]:
        """スキル改善の推奨事項を生成"""
        recommendations = []
        
        # 最も低いスキルに焦点を当てる
        weakest_skills = self._get_bottom_skills(current_scores, 2)
        for skill, score in weakest_skills:
            if score < 60:
                recommendations.append(
                    f'{self.SKILL_DEFINITIONS[skill]["name"]}を重点的に練習しましょう（現在: {score}点）'
                )
        
        # 成長が停滞しているスキル
        for skill, data in skill_growth.items():
            if data.get('trend') == 'declining':
                recommendations.append(
                    f'{self.SKILL_DEFINITIONS[skill]["name"]}の練習方法を見直してみましょう'
                )
        
        # バランスの改善
        values = list(current_scores.values())
        if np.std(values) > 15:
            recommendations.append('スキル間のバランスを意識して、弱いスキルも練習しましょう')
        
        return recommendations[:3]
    
    def _generate_correlation_insights(self, strong_correlations: List[Dict]) -> List[str]:
        """相関関係からの洞察を生成"""
        insights = []
        
        for corr in strong_correlations:
            skill1_name = self.SKILL_DEFINITIONS[corr['skill1']]['name']
            skill2_name = self.SKILL_DEFINITIONS[corr['skill2']]['name']
            
            if corr['relationship'] == 'positive':
                insights.append(
                    f'{skill1_name}と{skill2_name}は相互に向上する傾向があります'
                )
            else:
                insights.append(
                    f'{skill1_name}と{skill2_name}はトレードオフの関係にある可能性があります'
                )
        
        return insights