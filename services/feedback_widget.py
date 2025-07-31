"""
フィードバックウィジェットシステム

ユーザーからのリアルタイムフィードバック収集
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

from database import db


class FeedbackType(Enum):
    """フィードバックの種類"""
    HINT_HELPFUL = "hint_helpful"
    HINT_NOT_HELPFUL = "hint_not_helpful"
    HINT_INTRUSIVE = "hint_intrusive"
    SESSION_RATING = "session_rating"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL = "general"


@dataclass
class FeedbackItem:
    """フィードバック項目"""
    id: str
    user_id: int
    feedback_type: FeedbackType
    context: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


class FeedbackWidget:
    """
    インラインフィードバックウィジェットの管理
    """
    
    def __init__(self):
        self.feedback_points = {
            'after_coaching_hint': {
                'trigger': 'hint_shown',
                'delay_seconds': 0,
                'auto_dismiss': True,
                'dismiss_after': 30
            },
            'session_complete': {
                'trigger': 'session_end',
                'delay_seconds': 1,
                'auto_dismiss': False,
                'dismiss_after': None
            },
            'skill_milestone': {
                'trigger': 'milestone_reached',
                'delay_seconds': 2,
                'auto_dismiss': True,
                'dismiss_after': 45
            }
        }
    
    def generate_hint_feedback_widget(self, hint_id: str, hint_content: str, 
                                    context: Dict[str, Any]) -> str:
        """
        ヒント表示後のフィードバックウィジェットを生成
        
        Args:
            hint_id: ヒントのID
            hint_content: ヒントの内容
            context: コンテキスト情報
            
        Returns:
            HTMLウィジェット
        """
        widget_html = f'''
        <div class="feedback-widget hint-feedback" 
             data-hint-id="{hint_id}" 
             data-context="after_coaching_hint">
            <div class="feedback-content">
                <p class="feedback-question">このヒントは役に立ちましたか？</p>
                <div class="feedback-buttons">
                    <button class="btn-feedback helpful" 
                            onclick="submitHintFeedback('{hint_id}', 'helpful')">
                        <i class="fas fa-thumbs-up"></i> 役立った
                    </button>
                    <button class="btn-feedback not-helpful" 
                            onclick="submitHintFeedback('{hint_id}', 'not_helpful')">
                        <i class="fas fa-thumbs-down"></i> 役立たなかった
                    </button>
                    <button class="btn-feedback intrusive" 
                            onclick="submitHintFeedback('{hint_id}', 'intrusive')">
                        <i class="fas fa-times"></i> 邪魔だった
                    </button>
                </div>
                <button class="btn-close-widget" onclick="dismissFeedback('{hint_id}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
        '''
        
        return widget_html
    
    def generate_session_feedback_widget(self, session_id: str, 
                                       session_stats: Dict[str, Any]) -> str:
        """
        セッション完了時のフィードバックウィジェットを生成
        
        Args:
            session_id: セッションID
            session_stats: セッション統計
            
        Returns:
            HTMLウィジェット
        """
        widget_html = f'''
        <div class="feedback-widget session-feedback" 
             data-session-id="{session_id}" 
             data-context="session_complete">
            <div class="feedback-content">
                <h4>練習セッションはいかがでしたか？</h4>
                <div class="rating-section">
                    <p>総合評価:</p>
                    <div class="star-rating">
                        <span class="star" data-rating="1" onclick="setRating('{session_id}', 1)">★</span>
                        <span class="star" data-rating="2" onclick="setRating('{session_id}', 2)">★</span>
                        <span class="star" data-rating="3" onclick="setRating('{session_id}', 3)">★</span>
                        <span class="star" data-rating="4" onclick="setRating('{session_id}', 4)">★</span>
                        <span class="star" data-rating="5" onclick="setRating('{session_id}', 5)">★</span>
                    </div>
                </div>
                <div class="comment-section">
                    <p>改善点やご感想をお聞かせください（任意）:</p>
                    <textarea id="feedback-comment-{session_id}" 
                              placeholder="より良い練習体験のために、ご意見をお聞かせください"
                              maxlength="500"></textarea>
                </div>
                <div class="feedback-actions">
                    <button class="btn btn-primary" onclick="submitSessionFeedback('{session_id}')">
                        送信
                    </button>
                    <button class="btn btn-secondary" onclick="dismissFeedback('{session_id}')">
                        スキップ
                    </button>
                </div>
            </div>
        </div>
        '''
        
        return widget_html
    
    def generate_milestone_feedback_widget(self, milestone_type: str, 
                                         achievement: Dict[str, Any]) -> str:
        """
        マイルストーン達成時のフィードバックウィジェットを生成
        
        Args:
            milestone_type: マイルストーンの種類
            achievement: 達成内容
            
        Returns:
            HTMLウィジェット
        """
        widget_html = f'''
        <div class="feedback-widget milestone-feedback" 
             data-milestone="{milestone_type}" 
             data-context="skill_milestone">
            <div class="feedback-content congratulations">
                <div class="achievement-icon">
                    <i class="fas fa-trophy"></i>
                </div>
                <h4>おめでとうございます！</h4>
                <p>{achievement.get('description', 'マイルストーンを達成しました！')}</p>
                <div class="motivation-question">
                    <p>この成果をどう感じますか？</p>
                    <div class="emotion-buttons">
                        <button class="btn-emotion excited" 
                                onclick="submitMilestoneFeedback('{milestone_type}', 'excited')">
                            😄 嬉しい
                        </button>
                        <button class="btn-emotion proud" 
                                onclick="submitMilestoneFeedback('{milestone_type}', 'proud')">
                            😌 誇らしい
                        </button>
                        <button class="btn-emotion motivated" 
                                onclick="submitMilestoneFeedback('{milestone_type}', 'motivated')">
                            💪 やる気が出た
                        </button>
                    </div>
                </div>
                <button class="btn-close-widget" onclick="dismissFeedback('{milestone_type}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
        '''
        
        return widget_html
    
    def get_widget_styles(self) -> str:
        """
        ウィジェット用のCSSスタイルを生成
        
        Returns:
            CSS文字列
        """
        styles = '''
        <style>
        .feedback-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            padding: 20px;
            max-width: 350px;
            z-index: 1000;
            border-left: 4px solid #007bff;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .feedback-widget.session-feedback {
            border-left-color: #28a745;
            max-width: 400px;
        }
        
        .feedback-widget.milestone-feedback {
            border-left-color: #ffc107;
            text-align: center;
        }
        
        .feedback-content h4 {
            margin: 0 0 15px 0;
            color: #333;
            font-size: 16px;
        }
        
        .feedback-question {
            margin: 0 0 15px 0;
            font-size: 14px;
            color: #555;
        }
        
        .feedback-buttons {
            display: flex;
            gap: 8px;
            margin-bottom: 10px;
        }
        
        .btn-feedback {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        
        .btn-feedback:hover {
            background: #f8f9fa;
        }
        
        .btn-feedback.helpful:hover {
            background: #d4edda;
            border-color: #28a745;
            color: #28a745;
        }
        
        .btn-feedback.not-helpful:hover {
            background: #f8d7da;
            border-color: #dc3545;
            color: #dc3545;
        }
        
        .btn-feedback.intrusive:hover {
            background: #fff3cd;
            border-color: #ffc107;
            color: #856404;
        }
        
        .btn-close-widget {
            position: absolute;
            top: 8px;
            right: 8px;
            background: none;
            border: none;
            color: #999;
            cursor: pointer;
            font-size: 14px;
        }
        
        .btn-close-widget:hover {
            color: #333;
        }
        
        .star-rating {
            font-size: 24px;
            margin: 10px 0;
        }
        
        .star {
            color: #ddd;
            cursor: pointer;
            transition: color 0.2s;
        }
        
        .star:hover,
        .star.active {
            color: #ffc107;
        }
        
        .comment-section textarea {
            width: 100%;
            min-height: 60px;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 8px;
            font-size: 13px;
            resize: vertical;
            margin-top: 8px;
        }
        
        .feedback-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .feedback-actions .btn {
            flex: 1;
            padding: 8px 16px;
            border-radius: 4px;
            border: 1px solid #ddd;
            cursor: pointer;
            font-size: 13px;
        }
        
        .feedback-actions .btn-primary {
            background: #007bff;
            color: white;
            border-color: #007bff;
        }
        
        .feedback-actions .btn-secondary {
            background: #6c757d;
            color: white;
            border-color: #6c757d;
        }
        
        .achievement-icon {
            font-size: 32px;
            color: #ffc107;
            margin-bottom: 10px;
        }
        
        .emotion-buttons {
            display: flex;
            gap: 8px;
            justify-content: center;
            margin-top: 10px;
        }
        
        .btn-emotion {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 20px;
            background: white;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        
        .btn-emotion:hover {
            transform: scale(1.05);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .rating-section p {
            margin: 5px 0;
            font-size: 14px;
            color: #555;
        }
        
        .comment-section p {
            margin: 10px 0 5px 0;
            font-size: 14px;
            color: #555;
        }
        
        .motivation-question p {
            margin: 15px 0 10px 0;
            font-size: 14px;
            color: #555;
        }
        
        @media (max-width: 768px) {
            .feedback-widget {
                bottom: 10px;
                right: 10px;
                left: 10px;
                max-width: none;
            }
            
            .feedback-buttons {
                flex-direction: column;
            }
            
            .emotion-buttons {
                flex-direction: column;
                align-items: center;
            }
        }
        </style>
        '''
        
        return styles
    
    def get_widget_scripts(self) -> str:
        """
        ウィジェット用のJavaScriptを生成
        
        Returns:
            JavaScript文字列
        """
        scripts = '''
        <script>
        // フィードバックウィジェット用のJavaScript
        
        function submitHintFeedback(hintId, feedbackType) {
            fetch('/api/feedback/hint', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    hint_id: hintId,
                    feedback_type: feedbackType,
                    context: 'after_coaching_hint'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showFeedbackThanks();
                    dismissFeedback(hintId);
                }
            })
            .catch(error => console.error('Feedback error:', error));
        }
        
        function setRating(sessionId, rating) {
            // 星の表示を更新
            const stars = document.querySelectorAll(`[data-session-id="${sessionId}"] .star`);
            stars.forEach((star, index) => {
                if (index < rating) {
                    star.classList.add('active');
                } else {
                    star.classList.remove('active');
                }
            });
            
            // 評価を保存
            window.currentSessionRating = rating;
        }
        
        function submitSessionFeedback(sessionId) {
            const rating = window.currentSessionRating || 0;
            const comment = document.getElementById(`feedback-comment-${sessionId}`).value;
            
            fetch('/api/feedback/session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    rating: rating,
                    comment: comment,
                    context: 'session_complete'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showFeedbackThanks();
                    dismissFeedback(sessionId);
                }
            })
            .catch(error => console.error('Feedback error:', error));
        }
        
        function submitMilestoneFeedback(milestoneType, emotion) {
            fetch('/api/feedback/milestone', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    milestone_type: milestoneType,
                    emotion: emotion,
                    context: 'skill_milestone'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showFeedbackThanks();
                    dismissFeedback(milestoneType);
                }
            })
            .catch(error => console.error('Feedback error:', error));
        }
        
        function dismissFeedback(widgetId) {
            const widget = document.querySelector(`[data-hint-id="${widgetId}"], [data-session-id="${widgetId}"], [data-milestone="${widgetId}"]`);
            if (widget) {
                widget.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => {
                    widget.remove();
                }, 300);
            }
        }
        
        function showFeedbackThanks() {
            // 一時的な感謝メッセージを表示
            const thanksMessage = document.createElement('div');
            thanksMessage.className = 'feedback-thanks';
            thanksMessage.innerHTML = `
                <div class="thanks-content">
                    <i class="fas fa-check-circle"></i>
                    <p>フィードバックをありがとうございました！</p>
                </div>
            `;
            thanksMessage.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #28a745;
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 1001;
                animation: slideIn 0.3s ease-out;
            `;
            
            document.body.appendChild(thanksMessage);
            
            setTimeout(() => {
                thanksMessage.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => {
                    thanksMessage.remove();
                }, 300);
            }, 2000);
        }
        
        function getCSRFToken() {
            const token = document.querySelector('meta[name="csrf-token"]');
            return token ? token.getAttribute('content') : '';
        }
        
        // 自動削除の設定
        function setupAutoMissWedgets() {
            document.querySelectorAll('.feedback-widget[data-auto-dismiss="true"]').forEach(widget => {
                const dismissAfter = parseInt(widget.dataset.dismissAfter) || 30;
                setTimeout(() => {
                    if (widget.parentNode) {
                        dismissFeedback(widget.dataset.hintId || widget.dataset.milestone);
                    }
                }, dismissAfter * 1000);
            });
        }
        
        // ページ読み込み時に自動削除を設定
        document.addEventListener('DOMContentLoaded', setupAutoMissWedgets);
        
        // 新しいウィジェットが追加された時用のオブザーバー
        const widgetObserver = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1 && node.classList && node.classList.contains('feedback-widget')) {
                        setupAutoMissWedgets();
                    }
                });
            });
        });
        
        widgetObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // スライドアウトアニメーション
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
            
            .feedback-thanks .thanks-content {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .feedback-thanks .thanks-content i {
                font-size: 18px;
            }
            
            .feedback-thanks .thanks-content p {
                margin: 0;
                font-size: 14px;
            }
        `;
        document.head.appendChild(style);
        </script>
        '''
        
        return scripts
    
    def store_feedback(self, feedback_item: FeedbackItem) -> bool:
        """
        フィードバックをデータベースに保存
        
        Args:
            feedback_item: フィードバック項目
            
        Returns:
            保存成功かどうか
        """
        try:
            # 実際のプロダクションでは専用のFeedbackテーブルを作成すべき
            # ここでは簡易的な実装
            feedback_data = {
                'id': feedback_item.id,
                'user_id': feedback_item.user_id,
                'type': feedback_item.feedback_type.value,
                'context': feedback_item.context,
                'rating': feedback_item.rating,
                'comment': feedback_item.comment,
                'metadata': feedback_item.metadata,
                'timestamp': feedback_item.timestamp or datetime.utcnow()
            }
            
            # Redis等への保存ロジックをここに実装
            # 現在は単純にログ出力
            print(f"Feedback stored: {feedback_data}")
            
            return True
        except Exception as e:
            print(f"Error storing feedback: {str(e)}")
            return False