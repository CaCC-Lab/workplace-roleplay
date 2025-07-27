"""
分析APIエンドポイント

学習成果の分析・可視化機能へのAPIアクセスを提供
"""
from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from datetime import datetime
import logging

from analytics import LearningDashboard, SkillProgressAnalyzer, TrendAnalyzer

# ログ設定
logger = logging.getLogger(__name__)

# Blueprint作成
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

# 分析インスタンス
dashboard = LearningDashboard()
skill_analyzer = SkillProgressAnalyzer()
trend_analyzer = TrendAnalyzer()


@analytics_bp.route('/overview', methods=['GET'])
@login_required
def get_user_overview():
    """ユーザーの学習概要を取得"""
    try:
        user_id = current_user.id
        overview = dashboard.get_user_overview(user_id)
        
        return jsonify({
            'success': True,
            'data': overview
        })
        
    except Exception as e:
        logger.error(f"Error getting user overview: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get overview'
        }), 500


@analytics_bp.route('/skill-progression', methods=['GET'])
@login_required
def get_skill_progression():
    """スキルの成長推移を取得"""
    try:
        user_id = current_user.id
        days = request.args.get('days', 30, type=int)
        
        # 日数の制限（最大180日）
        days = min(days, 180)
        
        progression = dashboard.get_skill_progression(user_id, days)
        
        return jsonify({
            'success': True,
            'data': progression
        })
        
    except Exception as e:
        logger.error(f"Error getting skill progression: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get skill progression'
        }), 500


@analytics_bp.route('/scenario-performance', methods=['GET'])
@login_required
def get_scenario_performance():
    """シナリオ別のパフォーマンス分析を取得"""
    try:
        user_id = current_user.id
        performance = dashboard.get_scenario_performance(user_id)
        
        return jsonify({
            'success': True,
            'data': performance
        })
        
    except Exception as e:
        logger.error(f"Error getting scenario performance: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get scenario performance'
        }), 500


@analytics_bp.route('/comparative-analysis', methods=['GET'])
@login_required
def get_comparative_analysis():
    """他のユーザーとの比較分析を取得"""
    try:
        user_id = current_user.id
        comparison = dashboard.get_comparative_analysis(user_id)
        
        return jsonify({
            'success': True,
            'data': comparison
        })
        
    except Exception as e:
        logger.error(f"Error getting comparative analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get comparative analysis'
        }), 500


@analytics_bp.route('/skill/<skill_name>/progress', methods=['GET'])
@login_required
def analyze_skill_progress(skill_name):
    """特定スキルの詳細な進捗分析"""
    try:
        user_id = current_user.id
        days = request.args.get('days', 30, type=int)
        days = min(days, 180)
        
        analysis = skill_analyzer.analyze_skill_progress(user_id, skill_name, days)
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        logger.error(f"Error analyzing skill progress: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to analyze skill progress'
        }), 500


@analytics_bp.route('/skill-comparison', methods=['GET'])
@login_required
def compare_skills():
    """全スキルの比較分析"""
    try:
        user_id = current_user.id
        days = request.args.get('days', 30, type=int)
        days = min(days, 180)
        
        comparison = skill_analyzer.compare_skills(user_id, days)
        
        return jsonify({
            'success': True,
            'data': comparison
        })
        
    except Exception as e:
        logger.error(f"Error comparing skills: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to compare skills'
        }), 500


@analytics_bp.route('/skill-correlations', methods=['GET'])
@login_required
def get_skill_correlations():
    """スキル間の相関関係を分析"""
    try:
        user_id = current_user.id
        correlations = skill_analyzer.get_skill_correlations(user_id)
        
        return jsonify({
            'success': True,
            'data': correlations
        })
        
    except Exception as e:
        logger.error(f"Error getting skill correlations: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get skill correlations'
        }), 500


@analytics_bp.route('/trends', methods=['GET'])
@login_required
def analyze_trends():
    """全体的な学習トレンドを分析"""
    try:
        user_id = current_user.id
        days = request.args.get('days', 90, type=int)
        days = min(days, 365)
        
        trends = trend_analyzer.analyze_overall_trends(user_id, days)
        
        return jsonify({
            'success': True,
            'data': trends
        })
        
    except Exception as e:
        logger.error(f"Error analyzing trends: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to analyze trends'
        }), 500


@analytics_bp.route('/predict/<skill_name>', methods=['GET'])
@login_required
def predict_performance(skill_name):
    """将来のパフォーマンスを予測"""
    try:
        user_id = current_user.id
        days_ahead = request.args.get('days_ahead', 30, type=int)
        days_ahead = min(days_ahead, 90)
        
        prediction = trend_analyzer.predict_future_performance(
            user_id, skill_name, days_ahead
        )
        
        return jsonify({
            'success': True,
            'data': prediction
        })
        
    except Exception as e:
        logger.error(f"Error predicting performance: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to predict performance'
        }), 500


@analytics_bp.route('/plateaus', methods=['GET'])
@login_required
def identify_plateaus():
    """学習の停滞期を特定"""
    try:
        user_id = current_user.id
        plateaus = trend_analyzer.identify_learning_plateaus(user_id)
        
        return jsonify({
            'success': True,
            'data': plateaus
        })
        
    except Exception as e:
        logger.error(f"Error identifying plateaus: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to identify plateaus'
        }), 500


@analytics_bp.route('/momentum', methods=['GET'])
@login_required
def analyze_momentum():
    """学習の勢い（モメンタム）を分析"""
    try:
        user_id = current_user.id
        momentum = trend_analyzer.analyze_momentum(user_id)
        
        return jsonify({
            'success': True,
            'data': momentum
        })
        
    except Exception as e:
        logger.error(f"Error analyzing momentum: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to analyze momentum'
        }), 500


@analytics_bp.route('/export', methods=['GET'])
@login_required
def export_analytics_data():
    """分析データをエクスポート（CSV/JSON形式）"""
    try:
        user_id = current_user.id
        format_type = request.args.get('format', 'json')
        
        # 各種データを収集
        export_data = {
            'export_date': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'overview': dashboard.get_user_overview(user_id),
            'skill_progression': dashboard.get_skill_progression(user_id, 90),
            'skill_comparison': skill_analyzer.compare_skills(user_id, 90),
            'trends': trend_analyzer.analyze_overall_trends(user_id, 90)
        }
        
        if format_type == 'csv':
            # CSV形式への変換（簡略版）
            # TODO: 詳細なCSV変換実装
            return jsonify({
                'success': False,
                'error': 'CSV export not yet implemented'
            }), 501
        
        return jsonify({
            'success': True,
            'data': export_data
        })
        
    except Exception as e:
        logger.error(f"Error exporting analytics data: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to export analytics data'
        }), 500