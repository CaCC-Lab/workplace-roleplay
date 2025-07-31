"""
トレンド分析

時系列データの分析と将来予測
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
import numpy as np
from scipy import stats
from collections import defaultdict
from sqlalchemy.orm import joinedload, selectinload

from models import db, StrengthAnalysisResult, PracticeSession


class TrendAnalyzer:
    """学習トレンドの分析と予測"""
    
    def analyze_overall_trends(self, user_id: int, days: int = 90) -> Dict[str, Any]:
        """
        全体的な学習トレンドを分析
        
        Args:
            user_id: ユーザーID
            days: 分析期間（日数）
            
        Returns:
            トレンド分析結果
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # データ収集（関連データを事前にロード）
        analysis_results = StrengthAnalysisResult.query.filter(
            StrengthAnalysisResult.user_id == user_id,
            StrengthAnalysisResult.created_at >= start_date
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).order_by(StrengthAnalysisResult.created_at).all()
        
        conversations = PracticeSession.query.filter(
            PracticeSession.user_id == user_id,
            PracticeSession.started_at >= start_date
        ).options(
            joinedload(PracticeSession.user),
            joinedload(PracticeSession.scenario),
            selectinload(PracticeSession.logs),
            joinedload(PracticeSession.analysis)
        ).order_by(PracticeSession.started_at).all()
        
        if not analysis_results:
            return {'error': 'No data available for trend analysis'}
        
        # 時系列データの構築
        daily_stats = self._aggregate_daily_stats(analysis_results, conversations)
        weekly_stats = self._aggregate_weekly_stats(daily_stats)
        
        # トレンド分析
        trends = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            'activity_trend': self._analyze_activity_trend(daily_stats),
            'performance_trend': self._analyze_performance_trend(analysis_results),
            'skill_trends': self._analyze_skill_trends(analysis_results),
            'weekly_patterns': self._analyze_weekly_patterns(weekly_stats),
            'predictions': self._generate_predictions(analysis_results),
            'insights': self._generate_trend_insights(daily_stats, analysis_results)
        }
        
        return trends
    
    def predict_future_performance(self, user_id: int, skill_name: str, 
                                 days_ahead: int = 30) -> Dict[str, Any]:
        """
        将来のパフォーマンスを予測
        
        Args:
            user_id: ユーザーID
            skill_name: スキル名
            days_ahead: 予測する日数
            
        Returns:
            予測結果
        """
        # 過去90日のデータを使用
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        
        results = StrengthAnalysisResult.query.filter(
            StrengthAnalysisResult.user_id == user_id,
            StrengthAnalysisResult.created_at >= start_date
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).order_by(StrengthAnalysisResult.created_at).all()
        
        if len(results) < 5:
            return {'error': 'Insufficient data for prediction'}
        
        # スキルスコアの時系列データ
        scores = []
        dates = []
        
        for result in results:
            if result.analysis_result:
                score = result.analysis_result.get('scores', {}).get(skill_name)
                if score is not None:
                    scores.append(score)
                    dates.append(result.created_at)
        
        if len(scores) < 5:
            return {'error': f'Insufficient data for {skill_name}'}
        
        # 予測モデルの構築
        prediction = self._build_prediction_model(scores, dates, days_ahead)
        
        # 信頼区間の計算
        confidence_intervals = self._calculate_confidence_intervals(scores, prediction)
        
        return {
            'skill': skill_name,
            'current_score': scores[-1],
            'predicted_score': prediction['predicted_value'],
            'prediction_date': prediction['prediction_date'],
            'confidence_interval': confidence_intervals,
            'trend_strength': prediction['trend_strength'],
            'recommendations': self._generate_prediction_recommendations(
                skill_name, scores[-1], prediction['predicted_value']
            )
        }
    
    def identify_learning_plateaus(self, user_id: int) -> Dict[str, Any]:
        """
        学習の停滞期を特定
        
        Args:
            user_id: ユーザーID
            
        Returns:
            停滞期の分析結果
        """
        # 過去60日のデータを分析
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=60)
        
        results = StrengthAnalysisResult.query.filter(
            StrengthAnalysisResult.user_id == user_id,
            StrengthAnalysisResult.created_at >= start_date
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).order_by(StrengthAnalysisResult.created_at).all()
        
        if len(results) < 10:
            return {'error': 'Insufficient data for plateau analysis'}
        
        plateaus = {}
        
        # 各スキルの停滞期を分析
        for skill in ['empathy', 'clarity', 'active_listening', 'adaptability', 
                     'positivity', 'professionalism']:
            scores = []
            dates = []
            
            for result in results:
                if result.analysis_result:
                    score = result.analysis_result.get('scores', {}).get(skill)
                    if score is not None:
                        scores.append(score)
                        dates.append(result.created_at)
            
            if len(scores) >= 5:
                plateau_info = self._detect_plateau(scores, dates)
                if plateau_info['is_plateau']:
                    plateaus[skill] = plateau_info
        
        return {
            'plateaus_detected': len(plateaus) > 0,
            'affected_skills': list(plateaus.keys()),
            'details': plateaus,
            'breakthrough_strategies': self._suggest_breakthrough_strategies(plateaus)
        }
    
    def analyze_momentum(self, user_id: int) -> Dict[str, Any]:
        """
        学習の勢い（モメンタム）を分析
        
        Args:
            user_id: ユーザーID
            
        Returns:
            モメンタム分析結果
        """
        # 直近30日と前30日を比較
        end_date = datetime.utcnow()
        mid_date = end_date - timedelta(days=30)
        start_date = end_date - timedelta(days=60)
        
        # 期間別のデータ取得（関連データを事前にロード）
        recent_results = StrengthAnalysisResult.query.filter(
            StrengthAnalysisResult.user_id == user_id,
            StrengthAnalysisResult.created_at >= mid_date,
            StrengthAnalysisResult.created_at <= end_date
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).all()
        
        previous_results = StrengthAnalysisResult.query.filter(
            StrengthAnalysisResult.user_id == user_id,
            StrengthAnalysisResult.created_at >= start_date,
            StrengthAnalysisResult.created_at < mid_date
        ).options(
            joinedload(StrengthAnalysisResult.user),
            joinedload(StrengthAnalysisResult.session)
        ).all()
        
        recent_conversations = PracticeSession.query.filter(
            PracticeSession.user_id == user_id,
            PracticeSession.started_at >= mid_date
        ).count()
        
        previous_conversations = PracticeSession.query.filter(
            PracticeSession.user_id == user_id,
            PracticeSession.started_at >= start_date,
            PracticeSession.started_at < mid_date
        ).count()
        
        # モメンタム指標の計算
        activity_momentum = self._calculate_activity_momentum(
            recent_conversations, previous_conversations
        )
        
        performance_momentum = self._calculate_performance_momentum(
            recent_results, previous_results
        )
        
        # 総合モメンタムスコア
        overall_momentum = (activity_momentum['score'] + performance_momentum['score']) / 2
        
        return {
            'overall_momentum': round(overall_momentum, 1),
            'interpretation': self._interpret_momentum(overall_momentum),
            'activity_momentum': activity_momentum,
            'performance_momentum': performance_momentum,
            'recommendations': self._generate_momentum_recommendations(
                overall_momentum, activity_momentum, performance_momentum
            )
        }
    
    # プライベートメソッド
    def _aggregate_daily_stats(self, analysis_results: List[StrengthAnalysisResult], 
                             conversations: List[PracticeSession]) -> Dict[str, Any]:
        """日次統計を集計"""
        daily_stats = defaultdict(lambda: {
            'conversations': 0,
            'analyses': 0,
            'avg_scores': defaultdict(list)
        })
        
        # 会話数の集計
        for conv in conversations:
            date_key = conv.created_at.date().isoformat()
            daily_stats[date_key]['conversations'] += 1
        
        # 分析結果の集計
        for result in analysis_results:
            date_key = result.created_at.date().isoformat()
            daily_stats[date_key]['analyses'] += 1
            
            if result.analysis_result:
                scores = result.analysis_result.get('scores', {})
                for skill, score in scores.items():
                    daily_stats[date_key]['avg_scores'][skill].append(score)
        
        # 平均スコアの計算
        for date_key, stats in daily_stats.items():
            for skill, scores in stats['avg_scores'].items():
                if scores:
                    stats['avg_scores'][skill] = round(np.mean(scores), 1)
        
        return dict(daily_stats)
    
    def _aggregate_weekly_stats(self, daily_stats: Dict[str, Any]) -> Dict[str, Any]:
        """週次統計を集計"""
        weekly_stats = defaultdict(lambda: {
            'conversations': 0,
            'analyses': 0,
            'avg_scores': defaultdict(list),
            'days_active': 0
        })
        
        for date_str, stats in daily_stats.items():
            date = datetime.fromisoformat(date_str).date()
            week_key = date.isocalendar()[1]  # 週番号
            
            weekly_stats[week_key]['conversations'] += stats['conversations']
            weekly_stats[week_key]['analyses'] += stats['analyses']
            
            if stats['conversations'] > 0:
                weekly_stats[week_key]['days_active'] += 1
            
            for skill, score in stats['avg_scores'].items():
                if isinstance(score, (int, float)):
                    weekly_stats[week_key]['avg_scores'][skill].append(score)
        
        # 週平均の計算
        for week_key, stats in weekly_stats.items():
            for skill, scores in stats['avg_scores'].items():
                if scores:
                    stats['avg_scores'][skill] = round(np.mean(scores), 1)
        
        return dict(weekly_stats)
    
    def _analyze_activity_trend(self, daily_stats: Dict[str, Any]) -> Dict[str, Any]:
        """活動トレンドを分析"""
        dates = sorted(daily_stats.keys())
        conversation_counts = [daily_stats[date]['conversations'] for date in dates]
        
        if len(conversation_counts) < 2:
            return {'trend': 'insufficient_data'}
        
        # 線形回帰
        x = np.arange(len(conversation_counts))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, conversation_counts)
        
        # 移動平均（7日間）
        window = min(7, len(conversation_counts))
        moving_avg = []
        for i in range(len(conversation_counts) - window + 1):
            avg = np.mean(conversation_counts[i:i+window])
            moving_avg.append(round(avg, 1))
        
        return {
            'direction': 'increasing' if slope > 0.1 else 'decreasing' if slope < -0.1 else 'stable',
            'slope': round(slope, 3),
            'correlation': round(r_value, 3),
            'average_daily': round(np.mean(conversation_counts), 1),
            'moving_average': moving_avg
        }
    
    def _analyze_performance_trend(self, results: List[StrengthAnalysisResult]) -> Dict[str, Any]:
        """パフォーマンストレンドを分析"""
        if len(results) < 2:
            return {'trend': 'insufficient_data'}
        
        # 総合スコアの推移
        overall_scores = []
        dates = []
        
        for result in results:
            if result.analysis_result:
                scores = result.analysis_result.get('scores', {})
                if scores:
                    avg_score = np.mean(list(scores.values()))
                    overall_scores.append(avg_score)
                    dates.append(result.created_at)
        
        if len(overall_scores) < 2:
            return {'trend': 'insufficient_data'}
        
        # トレンド分析
        x = np.arange(len(overall_scores))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, overall_scores)
        
        # 改善率
        improvement_rate = ((overall_scores[-1] - overall_scores[0]) / overall_scores[0]) * 100
        
        return {
            'direction': 'improving' if slope > 0.5 else 'declining' if slope < -0.5 else 'stable',
            'slope': round(slope, 3),
            'correlation': round(r_value, 3),
            'improvement_rate': round(improvement_rate, 1),
            'current_level': round(overall_scores[-1], 1),
            'initial_level': round(overall_scores[0], 1)
        }
    
    def _analyze_skill_trends(self, results: List[StrengthAnalysisResult]) -> Dict[str, Any]:
        """個別スキルのトレンドを分析"""
        skill_trends = {}
        skills = ['empathy', 'clarity', 'active_listening', 'adaptability', 
                 'positivity', 'professionalism']
        
        for skill in skills:
            scores = []
            for result in results:
                if result.analysis_result:
                    score = result.analysis_result.get('scores', {}).get(skill)
                    if score is not None:
                        scores.append(score)
            
            if len(scores) >= 2:
                # トレンド計算
                x = np.arange(len(scores))
                slope, _, r_value, _, _ = stats.linregress(x, scores)
                
                skill_trends[skill] = {
                    'direction': 'improving' if slope > 0.5 else 'declining' if slope < -0.5 else 'stable',
                    'slope': round(slope, 3),
                    'current': scores[-1],
                    'change': round(scores[-1] - scores[0], 1)
                }
        
        return skill_trends
    
    def _analyze_weekly_patterns(self, weekly_stats: Dict[str, Any]) -> Dict[str, Any]:
        """週次パターンを分析"""
        weeks = sorted(weekly_stats.keys())
        
        if len(weeks) < 2:
            return {'pattern': 'insufficient_data'}
        
        # 週次活動量の推移
        weekly_activities = [weekly_stats[week]['conversations'] for week in weeks]
        weekly_active_days = [weekly_stats[week]['days_active'] for week in weeks]
        
        # 一貫性の評価
        activity_cv = np.std(weekly_activities) / np.mean(weekly_activities) if np.mean(weekly_activities) > 0 else 0
        
        return {
            'total_weeks': len(weeks),
            'avg_sessions_per_week': round(np.mean(weekly_activities), 1),
            'avg_active_days_per_week': round(np.mean(weekly_active_days), 1),
            'consistency': 'high' if activity_cv < 0.3 else 'medium' if activity_cv < 0.6 else 'low',
            'most_active_week': max(weekly_activities) if weekly_activities else 0,
            'least_active_week': min(weekly_activities) if weekly_activities else 0
        }
    
    def _build_prediction_model(self, scores: List[float], dates: List[datetime], 
                              days_ahead: int) -> Dict[str, Any]:
        """予測モデルを構築"""
        # 時系列の数値化（日数）
        base_date = dates[0]
        x = [(date - base_date).days for date in dates]
        
        # 多項式回帰（2次）
        coefficients = np.polyfit(x, scores, 2)
        poly = np.poly1d(coefficients)
        
        # 予測
        future_x = x[-1] + days_ahead
        predicted_score = poly(future_x)
        
        # トレンドの強さ
        linear_coeff = np.polyfit(x, scores, 1)
        trend_strength = abs(linear_coeff[0])
        
        return {
            'predicted_value': round(max(0, min(100, predicted_score)), 1),
            'prediction_date': (dates[-1] + timedelta(days=days_ahead)).isoformat(),
            'trend_strength': 'strong' if trend_strength > 1 else 'moderate' if trend_strength > 0.5 else 'weak'
        }
    
    def _calculate_confidence_intervals(self, scores: List[float], 
                                      prediction: Dict[str, Any]) -> Dict[str, float]:
        """信頼区間を計算"""
        std_dev = np.std(scores)
        margin = 1.96 * std_dev  # 95%信頼区間
        
        return {
            'lower': round(max(0, prediction['predicted_value'] - margin), 1),
            'upper': round(min(100, prediction['predicted_value'] + margin), 1)
        }
    
    def _detect_plateau(self, scores: List[float], dates: List[datetime]) -> Dict[str, Any]:
        """停滞期を検出"""
        if len(scores) < 5:
            return {'is_plateau': False}
        
        # 最近の5つのスコアで分析
        recent_scores = scores[-5:]
        
        # 変動が小さく、改善もない場合は停滞期
        std_dev = np.std(recent_scores)
        improvement = recent_scores[-1] - recent_scores[0]
        
        is_plateau = std_dev < 3 and abs(improvement) < 5
        
        if is_plateau:
            duration = (dates[-1] - dates[-5]).days
            return {
                'is_plateau': True,
                'duration_days': duration,
                'average_score': round(np.mean(recent_scores), 1),
                'variability': round(std_dev, 1)
            }
        
        return {'is_plateau': False}
    
    def _calculate_activity_momentum(self, recent_count: int, previous_count: int) -> Dict[str, Any]:
        """活動モメンタムを計算"""
        if previous_count == 0:
            change_rate = 100 if recent_count > 0 else 0
        else:
            change_rate = ((recent_count - previous_count) / previous_count) * 100
        
        # モメンタムスコア（-100から100）
        momentum_score = max(-100, min(100, change_rate))
        
        return {
            'score': round(momentum_score, 1),
            'recent_sessions': recent_count,
            'previous_sessions': previous_count,
            'change_rate': round(change_rate, 1)
        }
    
    def _calculate_performance_momentum(self, recent_results: List[StrengthAnalysisResult], 
                                      previous_results: List[StrengthAnalysisResult]) -> Dict[str, Any]:
        """パフォーマンスモメンタムを計算"""
        recent_scores = []
        previous_scores = []
        
        for result in recent_results:
            if result.analysis_result:
                scores = list(result.analysis_result.get('scores', {}).values())
                if scores:
                    recent_scores.append(np.mean(scores))
        
        for result in previous_results:
            if result.analysis_result:
                scores = list(result.analysis_result.get('scores', {}).values())
                if scores:
                    previous_scores.append(np.mean(scores))
        
        if not recent_scores or not previous_scores:
            return {'score': 0, 'insufficient_data': True}
        
        recent_avg = np.mean(recent_scores)
        previous_avg = np.mean(previous_scores)
        
        # 改善率をモメンタムスコアに変換
        improvement = ((recent_avg - previous_avg) / previous_avg) * 100
        momentum_score = max(-100, min(100, improvement * 2))  # 感度を上げる
        
        return {
            'score': round(momentum_score, 1),
            'recent_average': round(recent_avg, 1),
            'previous_average': round(previous_avg, 1),
            'improvement': round(improvement, 1)
        }
    
    def _interpret_momentum(self, momentum_score: float) -> str:
        """モメンタムスコアを解釈"""
        if momentum_score >= 50:
            return 'excellent_momentum'
        elif momentum_score >= 20:
            return 'good_momentum'
        elif momentum_score >= -20:
            return 'stable'
        elif momentum_score >= -50:
            return 'declining'
        else:
            return 'significant_decline'
    
    def _generate_trend_insights(self, daily_stats: Dict[str, Any], 
                               results: List[StrengthAnalysisResult]) -> List[str]:
        """トレンドからの洞察を生成"""
        insights = []
        
        # 活動パターンの洞察
        active_days = sum(1 for stats in daily_stats.values() if stats['conversations'] > 0)
        total_days = len(daily_stats)
        
        if total_days > 0:
            activity_rate = active_days / total_days
            if activity_rate > 0.7:
                insights.append('非常に継続的な学習習慣が身についています')
            elif activity_rate < 0.3:
                insights.append('学習頻度を上げることで、より効果的な成長が期待できます')
        
        # スコアトレンドの洞察
        if len(results) >= 5:
            initial_scores = []
            recent_scores = []
            
            for result in results[:3]:
                if result.analysis_result:
                    scores = list(result.analysis_result.get('scores', {}).values())
                    if scores:
                        initial_scores.extend(scores)
            
            for result in results[-3:]:
                if result.analysis_result:
                    scores = list(result.analysis_result.get('scores', {}).values())
                    if scores:
                        recent_scores.extend(scores)
            
            if initial_scores and recent_scores:
                improvement = np.mean(recent_scores) - np.mean(initial_scores)
                if improvement > 10:
                    insights.append('全体的に大幅な改善が見られます')
                elif improvement < -5:
                    insights.append('最近のパフォーマンスが低下傾向です。練習方法の見直しをおすすめします')
        
        return insights
    
    def _generate_prediction_recommendations(self, skill_name: str, current_score: float, 
                                           predicted_score: float) -> List[str]:
        """予測に基づく推奨事項を生成"""
        recommendations = []
        
        if predicted_score > current_score + 5:
            recommendations.append(f'このペースで練習を続ければ、着実に向上が期待できます')
        elif predicted_score < current_score - 5:
            recommendations.append(f'現在のペースでは低下が予想されます。練習頻度を増やしましょう')
        else:
            recommendations.append(f'安定した状態です。新しい練習方法を試してみましょう')
        
        if predicted_score < 70:
            recommendations.append(f'{skill_name}に特化した集中練習をおすすめします')
        
        return recommendations
    
    def _suggest_breakthrough_strategies(self, plateaus: Dict[str, Any]) -> List[str]:
        """停滞期突破の戦略を提案"""
        strategies = []
        
        if len(plateaus) >= 3:
            strategies.append('複数のスキルが停滞しています。練習方法を大きく変えてみましょう')
            strategies.append('より難易度の高いシナリオに挑戦することをおすすめします')
        elif plateaus:
            strategies.append('停滞しているスキルに集中的に取り組む期間を設けましょう')
            strategies.append('フィードバックを詳細に分析し、具体的な改善点を見つけましょう')
        
        strategies.append('他のユーザーの成功事例を参考にすることも有効です')
        
        return strategies
    
    def _generate_momentum_recommendations(self, overall_momentum: float, 
                                         activity_momentum: Dict[str, Any], 
                                         performance_momentum: Dict[str, Any]) -> List[str]:
        """モメンタムに基づく推奨事項を生成"""
        recommendations = []
        
        if overall_momentum >= 50:
            recommendations.append('素晴らしい勢いです！この調子を維持しましょう')
        elif overall_momentum >= 20:
            recommendations.append('良い方向に向かっています。もう少し頻度を上げてみましょう')
        elif overall_momentum < -20:
            recommendations.append('モチベーション維持のため、小さな目標を設定しましょう')
        
        # 活動と成果のバランス
        if activity_momentum['score'] > performance_momentum['score'] + 30:
            recommendations.append('練習量は十分です。質を重視した練習に切り替えましょう')
        elif performance_momentum['score'] > activity_momentum['score'] + 30:
            recommendations.append('成果は出ています。練習頻度を上げればさらに加速できます')
        
        return recommendations