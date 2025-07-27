"""
推薦システムAPIエンドポイント

パーソナライズされたシナリオ推薦機能
"""
from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from datetime import datetime
import logging

from services.recommendation import get_recommendations_for_user, get_recommendation_explanation

# ログ設定
logger = logging.getLogger(__name__)

# Blueprint作成
recommendations_bp = Blueprint('recommendations', __name__, url_prefix='/api')


@recommendations_bp.route('/recommended_scenarios', methods=['GET'])
@login_required
def get_recommended_scenarios():
    """
    ユーザーに推薦されるシナリオを取得
    
    Query Parameters:
        limit: 推薦数（デフォルト3、最大10）
        difficulty: 希望難易度（1-5、省略時は自動調整）
    
    Returns:
        推薦シナリオのJSONリスト
    """
    try:
        # パラメータを取得
        limit = min(int(request.args.get('limit', 3)), 10)  # 最大10件まで
        difficulty_preference = request.args.get('difficulty')
        
        # 難易度のバリデーション
        if difficulty_preference:
            try:
                difficulty_preference = int(difficulty_preference)
                if not 1 <= difficulty_preference <= 5:
                    return jsonify({
                        'success': False,
                        'error': 'Difficulty must be between 1 and 5'
                    }), 400
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid difficulty format'
                }), 400
        else:
            difficulty_preference = None
        
        # 推薦シナリオを取得
        recommendations = get_recommendations_for_user(
            current_user.id, limit, difficulty_preference
        )
        
        # セッションに推薦ログを記録（後の改善のため）
        session_recommendations = session.get('recent_recommendations', [])
        session_recommendations.append({
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': current_user.id,
            'limit': limit,
            'difficulty_preference': difficulty_preference,
            'results_count': len(recommendations)
        })
        
        # 直近10件の履歴のみ保持
        session['recent_recommendations'] = session_recommendations[-10:]
        
        logger.info(f"Generated {len(recommendations)} recommendations for user {current_user.id}")
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'metadata': {
                'user_id': current_user.id,
                'limit': limit,
                'difficulty_preference': difficulty_preference,
                'generated_at': datetime.utcnow().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating recommendations for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': '推薦シナリオの取得中にエラーが発生しました'
        }), 500


@recommendations_bp.route('/recommendation_explanation', methods=['GET'])
@login_required
def get_recommendation_explanation():
    """
    推薦根拠の詳細説明を取得
    
    Returns:
        推薦理由とユーザーのスキル分析結果
    """
    try:
        explanation = get_recommendation_explanation(current_user.id)
        
        return jsonify({
            'success': True,
            'explanation': explanation,
            'user_id': current_user.id,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting recommendation explanation for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': '推薦根拠の取得中にエラーが発生しました'
        }), 500


@recommendations_bp.route('/recommendation_feedback', methods=['POST'])
@login_required
def submit_recommendation_feedback():
    """
    推薦結果に対するフィードバックを受信
    
    Request Body:
        scenario_id: 対象シナリオID
        feedback_type: helpful | not_helpful | completed
        comment: 任意のコメント
    
    Returns:
        成功/失敗ステータス
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON'}), 400
        
        scenario_id = data.get('scenario_id')
        feedback_type = data.get('feedback_type')
        comment = data.get('comment', '')
        
        if not scenario_id or not feedback_type:
            return jsonify({
                'success': False,
                'error': 'scenario_id and feedback_type are required'
            }), 400
        
        # フィードバックタイプのバリデーション
        valid_feedback_types = ['helpful', 'not_helpful', 'completed']
        if feedback_type not in valid_feedback_types:
            return jsonify({
                'success': False,
                'error': f'Invalid feedback_type. Must be one of: {", ".join(valid_feedback_types)}'
            }), 400
        
        # フィードバックデータを作成
        feedback_data = {
            'user_id': current_user.id,
            'scenario_id': scenario_id,
            'feedback_type': feedback_type,
            'comment': comment.strip() if comment else None,
            'timestamp': datetime.utcnow().isoformat(),
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        # セッションにフィードバック履歴を記録
        session_feedback = session.get('recommendation_feedback', [])
        session_feedback.append(feedback_data)
        
        # 直近50件のフィードバックのみ保持
        session['recommendation_feedback'] = session_feedback[-50:]
        
        logger.info(f"Recommendation feedback received: {feedback_type} for scenario {scenario_id} by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'フィードバックをありがとうございました'
        })
        
    except Exception as e:
        logger.error(f"Error processing recommendation feedback: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'フィードバックの処理中にエラーが発生しました'
        }), 500


@recommendations_bp.route('/user_learning_path', methods=['GET'])
@login_required
def get_user_learning_path():
    """
    ユーザーの学習パス（推薦シナリオの順序）を取得
    
    Returns:
        段階的な学習パスの提案
    """
    try:
        # 各難易度レベルから推薦シナリオを取得
        learning_path = {}
        
        for difficulty in range(1, 6):
            recommendations = get_recommendations_for_user(
                current_user.id, limit=2, difficulty_preference=difficulty
            )
            if recommendations:
                learning_path[f'level_{difficulty}'] = {
                    'difficulty': difficulty,
                    'difficulty_name': ['初級', '初中級', '中級', '中上級', '上級'][difficulty - 1],
                    'scenarios': recommendations
                }
        
        # 現在のユーザーレベル推定
        explanation = get_recommendation_explanation(current_user.id)
        current_level = 'beginner'
        
        if explanation.get('status') == 'success':
            avg_skill = explanation.get('average_skill', 2.5)
            if avg_skill >= 4.0:
                current_level = 'advanced'
            elif avg_skill >= 3.0:
                current_level = 'intermediate'
            else:
                current_level = 'beginner'
        
        return jsonify({
            'success': True,
            'learning_path': learning_path,
            'user_level': current_level,
            'recommendation': {
                'next_level': min(3, int(explanation.get('average_skill', 2.5)) + 1) if explanation.get('status') == 'success' else 1,
                'focus_skills': explanation.get('weak_skills', [])[:2] if explanation.get('status') == 'success' else []
            },
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating learning path for user {current_user.id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': '学習パスの生成中にエラーが発生しました'
        }), 500


@recommendations_bp.route('/recommendation_stats', methods=['GET'])
@login_required
def get_recommendation_stats():
    """
    推薦システムの統計情報を取得（管理者用）
    
    Returns:
        推薦システムの使用統計
    """
    try:
        # 管理者権限のチェック（簡易版）
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            return jsonify({
                'success': False,
                'error': '管理者権限が必要です'
            }), 403
        
        # セッションからフィードバック統計を生成
        all_feedback = session.get('recommendation_feedback', [])
        recent_recommendations = session.get('recent_recommendations', [])
        
        feedback_stats = {}
        for feedback in all_feedback:
            feedback_type = feedback['feedback_type']
            feedback_stats[feedback_type] = feedback_stats.get(feedback_type, 0) + 1
        
        return jsonify({
            'success': True,
            'stats': {
                'total_recommendations': len(recent_recommendations),
                'feedback_counts': feedback_stats,
                'feedback_rate': len(all_feedback) / max(len(recent_recommendations), 1),
            },
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting recommendation stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': '統計情報の取得に失敗しました'
        }), 500