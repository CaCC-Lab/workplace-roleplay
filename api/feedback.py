"""
フィードバックAPIエンドポイント

リアルタイムコーチングとA/Bテストのフィードバック収集
"""
from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
from datetime import datetime
import logging
import uuid

from services.feedback_widget import FeedbackWidget, FeedbackItem, FeedbackType
from services.ab_testing import ExperimentationFramework

# ログ設定
logger = logging.getLogger(__name__)

# Blueprint作成
feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')

# サービスインスタンス
feedback_widget = FeedbackWidget()
experiment_framework = ExperimentationFramework()


@feedback_bp.route('/hint', methods=['POST'])
@login_required
def submit_hint_feedback():
    """
    ヒントに対するフィードバックを受け取り
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON'}), 400
        
        hint_id = data.get('hint_id')
        feedback_type = data.get('feedback_type')
        context = data.get('context', 'after_coaching_hint')
        
        if not hint_id or not feedback_type:
            return jsonify({
                'success': False, 
                'error': 'hint_id and feedback_type are required'
            }), 400
        
        # フィードバックタイプのマッピング
        type_mapping = {
            'helpful': FeedbackType.HINT_HELPFUL,
            'not_helpful': FeedbackType.HINT_NOT_HELPFUL,
            'intrusive': FeedbackType.HINT_INTRUSIVE
        }
        
        feedback_enum = type_mapping.get(feedback_type)
        if not feedback_enum:
            return jsonify({
                'success': False, 
                'error': 'Invalid feedback_type'
            }), 400
        
        # フィードバックアイテムを作成
        feedback_item = FeedbackItem(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            feedback_type=feedback_enum,
            context=context,
            metadata={
                'hint_id': hint_id,
                'feedback_value': feedback_type,
                'user_agent': request.headers.get('User-Agent', ''),
                'session_id': session.get('session_id')
            },
            timestamp=datetime.utcnow()
        )
        
        # フィードバックを保存
        success = feedback_widget.store_feedback(feedback_item)
        
        if success:
            # A/Bテストメトリクスとして記録
            experiment_framework.track_metric(
                current_user.id, f'hint_{feedback_type}', 1.0, 'realtime_coaching'
            )
            
            logger.info(f"Hint feedback recorded: {feedback_type} for hint {hint_id} by user {current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'フィードバックをありがとうございました'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'フィードバックの保存に失敗しました'
            }), 500
        
    except Exception as e:
        logger.error(f"Error processing hint feedback: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'フィードバックの処理中にエラーが発生しました'
        }), 500


@feedback_bp.route('/session', methods=['POST'])
@login_required
def submit_session_feedback():
    """
    セッション完了時のフィードバックを受け取り
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON'}), 400
        
        session_id = data.get('session_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        context = data.get('context', 'session_complete')
        
        if not session_id:
            return jsonify({
                'success': False, 
                'error': 'session_id is required'
            }), 400
        
        # 評価のバリデーション
        if rating is not None:
            try:
                rating = int(rating)
                if not 1 <= rating <= 5:
                    return jsonify({
                        'success': False, 
                        'error': 'Rating must be between 1 and 5'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False, 
                    'error': 'Invalid rating format'
                }), 400
        
        # フィードバックアイテムを作成
        feedback_item = FeedbackItem(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            feedback_type=FeedbackType.SESSION_RATING,
            context=context,
            rating=rating,
            comment=comment.strip() if comment else None,
            metadata={
                'session_id': session_id,
                'comment_length': len(comment.strip()) if comment else 0,
                'user_agent': request.headers.get('User-Agent', '')
            },
            timestamp=datetime.utcnow()
        )
        
        # フィードバックを保存
        success = feedback_widget.store_feedback(feedback_item)
        
        if success:
            # A/Bテストメトリクスとして記録
            if rating is not None:
                experiment_framework.track_metric(
                    current_user.id, 'session_rating', float(rating), 'realtime_coaching'
                )
            
            experiment_framework.track_metric(
                current_user.id, 'session_feedback_submitted', 1.0, 'realtime_coaching'
            )
            
            logger.info(f"Session feedback recorded: rating={rating}, comment_length={len(comment) if comment else 0} for session {session_id} by user {current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'フィードバックをありがとうございました'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'フィードバックの保存に失敗しました'
            }), 500
        
    except Exception as e:
        logger.error(f"Error processing session feedback: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'フィードバックの処理中にエラーが発生しました'
        }), 500


@feedback_bp.route('/milestone', methods=['POST'])
@login_required
def submit_milestone_feedback():
    """
    マイルストーン達成時のフィードバックを受け取り
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON'}), 400
        
        milestone_type = data.get('milestone_type')
        emotion = data.get('emotion')
        context = data.get('context', 'skill_milestone')
        
        if not milestone_type or not emotion:
            return jsonify({
                'success': False, 
                'error': 'milestone_type and emotion are required'
            }), 400
        
        # 感情のバリデーション
        valid_emotions = ['excited', 'proud', 'motivated', 'satisfied', 'disappointed']
        if emotion not in valid_emotions:
            return jsonify({
                'success': False, 
                'error': f'Invalid emotion. Must be one of: {", ".join(valid_emotions)}'
            }), 400
        
        # フィードバックアイテムを作成
        feedback_item = FeedbackItem(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            feedback_type=FeedbackType.GENERAL,
            context=context,
            metadata={
                'milestone_type': milestone_type,
                'emotion': emotion,
                'user_agent': request.headers.get('User-Agent', ''),
                'session_id': session.get('session_id')
            },
            timestamp=datetime.utcnow()
        )
        
        # フィードバックを保存
        success = feedback_widget.store_feedback(feedback_item)
        
        if success:
            # モチベーションメトリクスとして記録
            motivation_score = {
                'excited': 5.0,
                'proud': 4.5,
                'motivated': 4.8,
                'satisfied': 3.5,
                'disappointed': 1.0
            }.get(emotion, 3.0)
            
            experiment_framework.track_metric(
                current_user.id, 'milestone_motivation', motivation_score, 'realtime_coaching'
            )
            
            logger.info(f"Milestone feedback recorded: {emotion} for {milestone_type} by user {current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'フィードバックをありがとうございました'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'フィードバックの保存に失敗しました'
            }), 500
        
    except Exception as e:
        logger.error(f"Error processing milestone feedback: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'フィードバックの処理中にエラーが発生しました'
        }), 500


@feedback_bp.route('/widget/<widget_type>', methods=['GET'])
@login_required
def get_feedback_widget(widget_type):
    """
    指定されたタイプのフィードバックウィジェットHTMLを生成
    """
    try:
        widget_html = ''
        
        if widget_type == 'hint':
            hint_id = request.args.get('hint_id', 'default')
            hint_content = request.args.get('hint_content', '')
            context = {'user_id': current_user.id}
            widget_html = feedback_widget.generate_hint_feedback_widget(
                hint_id, hint_content, context
            )
        
        elif widget_type == 'session':
            session_id = request.args.get('session_id', 'default')
            session_stats = {'user_id': current_user.id}
            widget_html = feedback_widget.generate_session_feedback_widget(
                session_id, session_stats
            )
        
        elif widget_type == 'milestone':
            milestone_type = request.args.get('milestone_type', 'default')
            achievement = {
                'description': request.args.get('description', 'マイルストーンを達成しました！')
            }
            widget_html = feedback_widget.generate_milestone_feedback_widget(
                milestone_type, achievement
            )
        
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid widget type'
            }), 400
        
        return jsonify({
            'success': True,
            'widget_html': widget_html,
            'styles': feedback_widget.get_widget_styles(),
            'scripts': feedback_widget.get_widget_scripts()
        })
        
    except Exception as e:
        logger.error(f"Error generating feedback widget: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'ウィジェットの生成に失敗しました'
        }), 500


@feedback_bp.route('/stats', methods=['GET'])
@login_required
def get_feedback_stats():
    """
    フィードバックの統計情報を取得（管理者用）
    """
    try:
        # 管理者権限のチェック（簡易版）
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            return jsonify({
                'success': False,
                'error': '管理者権限が必要です'
            }), 403
        
        # A/Bテストの結果を取得
        experiment_results = experiment_framework.get_experiment_results('realtime_coaching', days=7)
        
        return jsonify({
            'success': True,
            'experiment_results': experiment_results,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': '統計情報の取得に失敗しました'
        }), 500