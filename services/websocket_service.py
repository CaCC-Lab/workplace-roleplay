"""
WebSocketコーチングサービス

リアルタイムコーチングのWebSocket接続を管理
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from flask import session

from services.realtime_coach import RealTimeCoach
from services.ab_testing import ExperimentationFramework
from database import db, StrengthAnalysisResult

logger = logging.getLogger(__name__)


class WebSocketCoachingService:
    """
WebSocketベースのリアルタイムコーチングサービス
    """
    
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.coaching_engine = RealTimeCoach()
        self.experiment_framework = ExperimentationFramework()
        self.setup_handlers()
    
    def setup_handlers(self):
        """
WebSocketイベントハンドラーの設定
        """
        
        @self.socketio.on('connect')
        def handle_connect():
            """WebSocket接続時の処理"""
            if not current_user.is_authenticated:
                logger.warning("Unauthorized WebSocket connection attempt")
                return False
            
            user_id = current_user.id
            session_id = session.get('session_id', f'session_{user_id}_{datetime.utcnow().timestamp()}')
            
            # A/Bテストのバリアント割り当て
            variant = self.experiment_framework.assign_variant(user_id, 'realtime_coaching')
            
            # セッション情報を保存
            self.active_sessions[session_id] = {
                'user_id': user_id,
                'variant': variant,
                'start_time': datetime.utcnow(),
                'message_count': 0,
                'hints_shown': 0,
                'hints_accepted': 0
            }
            
            # ルームに参加
            join_room(session_id)
            
            # クライアントに設定を送信
            emit('coaching_config', {
                'enabled': variant['coaching_enabled'],
                'hint_level': variant.get('hint_level', 'basic'),
                'session_id': session_id
            })
            
            logger.info(f"User {user_id} connected with variant {variant}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """WebSocket切断時の処理"""
            if current_user.is_authenticated:
                user_id = current_user.id
                session_id = session.get('session_id')
                
                if session_id in self.active_sessions:
                    # セッション終了メトリクスを記録
                    session_data = self.active_sessions[session_id]
                    duration = (datetime.utcnow() - session_data['start_time']).total_seconds()
                    
                    self.experiment_framework.track_metric(
                        user_id, 'session_duration', duration
                    )
                    
                    if session_data['hints_shown'] > 0:
                        acceptance_rate = session_data['hints_accepted'] / session_data['hints_shown']
                        self.experiment_framework.track_metric(
                            user_id, 'hint_acceptance_rate', acceptance_rate
                        )
                    
                    # セッションデータを削除
                    del self.active_sessions[session_id]
                    
                logger.info(f"User {user_id} disconnected")
        
        @self.socketio.on('message_typing')
        def handle_typing(data):
            """ユーザーの入力中の処理"""
            if not current_user.is_authenticated:
                return
            
            session_id = data.get('session_id')
            partial_message = data.get('message', '')
            
            if session_id not in self.active_sessions:
                logger.warning(f"Session {session_id} not found for typing event")
                return
            
            session_data = self.active_sessions[session_id]
            variant = session_data['variant']
            
            # コーチングが無効の場合はスキップ
            if not variant.get('coaching_enabled', False):
                return
            
            # 非同期でヒント生成
            asyncio.create_task(
                self._generate_typing_hints(session_id, partial_message, data.get('context', {}))
            )
        
        @self.socketio.on('message_sent')
        def handle_message_sent(data):
            """メッセージ送信後の処理"""
            if not current_user.is_authenticated:
                return
            
            session_id = data.get('session_id')
            message = data.get('message', '')
            context = data.get('context', {})
            
            if session_id not in self.active_sessions:
                logger.warning(f"Session {session_id} not found for message event")
                return
            
            session_data = self.active_sessions[session_id]
            session_data['message_count'] += 1
            
            # コーチングが無効の場合はスキップ
            variant = session_data['variant']
            if not variant.get('coaching_enabled', False):
                return
            
            # 非同期で詳細分析
            asyncio.create_task(
                self._analyze_complete_message(session_id, message, context)
            )
        
        @self.socketio.on('hint_interaction')
        def handle_hint_interaction(data):
            """ヒントへのユーザーアクションを記録"""
            if not current_user.is_authenticated:
                return
            
            session_id = data.get('session_id')
            action = data.get('action')  # 'accepted', 'dismissed', 'clicked'
            hint_id = data.get('hint_id')
            
            if session_id in self.active_sessions:
                session_data = self.active_sessions[session_id]
                
                if action == 'accepted':
                    session_data['hints_accepted'] += 1
                
                # メトリクス記録
                self.experiment_framework.track_metric(
                    current_user.id, f'hint_{action}', 1
                )
                
                logger.info(f"Hint {hint_id} {action} by user {current_user.id}")
        
        @self.socketio.on('request_scenario_hints')
        def handle_scenario_hints_request(data):
            """シナリオ固有のヒントリクエスト"""
            if not current_user.is_authenticated:
                return
            
            scenario_id = data.get('scenario_id')
            context = data.get('context', {})
            
            hints = self.coaching_engine.get_scenario_specific_hints(scenario_id, context)
            
            emit('scenario_hints', {
                'hints': hints,
                'scenario_id': scenario_id
            })
    
    async def _generate_typing_hints(self, session_id: str, partial_message: str, context: Dict[str, Any]):
        """
        入力中のリアルタイムヒント生成
        """
        try:
            session_data = self.active_sessions.get(session_id)
            if not session_data:
                return
            
            variant = session_data['variant']
            hint_level = variant.get('hint_level', 'basic')
            
            # ヒントレベルに応じて間引きを調整
            min_length = 20 if hint_level == 'basic' else 15 if hint_level == 'advanced' else 25
            
            if len(partial_message.strip()) < min_length:
                return
            
            # ヒント生成
            hints = await self.coaching_engine.get_typing_hints(partial_message, context)
            
            if hints:
                # ヒント表示カウントを增加
                session_data['hints_shown'] += len(hints)
                
                # クライアントに送信
                self.socketio.emit('typing_hints', {
                    'hints': hints,
                    'confidence': self._calculate_hint_confidence(partial_message),
                    'timestamp': datetime.utcnow().isoformat()
                }, room=session_id)
                
                logger.debug(f"Sent {len(hints)} typing hints to session {session_id}")
        
        except Exception as e:
            logger.error(f"Error generating typing hints: {str(e)}")
    
    async def _analyze_complete_message(self, session_id: str, message: str, context: Dict[str, Any]):
        """
        送信完了メッセージの詳細分析
        """
        try:
            session_data = self.active_sessions.get(session_id)
            if not session_data:
                return
            
            # メッセージ分析
            analysis = await self.coaching_engine.analyze_message_realtime(message, context)
            
            # ユーザーの過去の分析履歴を取得
            user_history = StrengthAnalysisResult.query.filter_by(
                user_id=session_data['user_id']
            ).order_by(StrengthAnalysisResult.created_at.desc()).limit(10).all()
            
            # スコアへの影響を計算
            score_impact = self.coaching_engine.calculate_score_impact(analysis, user_history)
            
            # 結果をクライアントに送信
            self.socketio.emit('message_analysis', {
                'analysis': analysis,
                'score_impact': score_impact,
                'recommendations': analysis.get('suggestions', []),
                'timestamp': datetime.utcnow().isoformat()
            }, room=session_id)
            
            # メトリクス記録
            avg_score = sum(analysis['scores'].values()) / len(analysis['scores'])
            self.experiment_framework.track_metric(
                session_data['user_id'], 'message_score', avg_score
            )
            
            logger.debug(f"Analyzed message for session {session_id}, avg score: {avg_score}")
        
        except Exception as e:
            logger.error(f"Error analyzing complete message: {str(e)}")
    
    def _calculate_hint_confidence(self, message: str) -> float:
        """
        ヒントの信頼度を計算
        
        Args:
            message: 分析対象のメッセージ
            
        Returns:
            信頼度 (0.0-1.0)
        """
        # メッセージの長さに基づく信頼度
        length_confidence = min(1.0, len(message) / 50.0)
        
        # 完成度に基づく信頼度（句点があるか）
        completion_confidence = 0.8 if message.strip().endswith(('。', '、', '!', '?')) else 0.6
        
        return min(1.0, (length_confidence + completion_confidence) / 2)
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッションの統計情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            セッション統計
        """
        if session_id not in self.active_sessions:
            return None
        
        session_data = self.active_sessions[session_id]
        current_time = datetime.utcnow()
        duration = (current_time - session_data['start_time']).total_seconds()
        
        return {
            'user_id': session_data['user_id'],
            'variant': session_data['variant'],
            'duration_seconds': duration,
            'message_count': session_data['message_count'],
            'hints_shown': session_data['hints_shown'],
            'hints_accepted': session_data['hints_accepted'],
            'acceptance_rate': (
                session_data['hints_accepted'] / session_data['hints_shown']
                if session_data['hints_shown'] > 0 else 0
            )
        }
    
    def broadcast_system_message(self, message: str, message_type: str = 'info'):
        """
        全ユーザーにシステムメッセージを送信
        
        Args:
            message: メッセージ内容
            message_type: メッセージタイプ ('info', 'warning', 'error')
        """
        self.socketio.emit('system_message', {
            'message': message,
            'type': message_type,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)
        
        logger.info(f"Broadcast system message: {message}")
    
    def get_all_session_stats(self) -> Dict[str, Any]:
        """
        全アクティブセッションの統計を取得
        
        Returns:
            全セッションの統計情報
        """
        total_sessions = len(self.active_sessions)
        total_messages = sum(s['message_count'] for s in self.active_sessions.values())
        total_hints = sum(s['hints_shown'] for s in self.active_sessions.values())
        total_accepted = sum(s['hints_accepted'] for s in self.active_sessions.values())
        
        return {
            'active_sessions': total_sessions,
            'total_messages': total_messages,
            'total_hints_shown': total_hints,
            'total_hints_accepted': total_accepted,
            'overall_acceptance_rate': (
                total_accepted / total_hints if total_hints > 0 else 0
            ),
            'variant_distribution': self._get_variant_distribution()
        }
    
    def _get_variant_distribution(self) -> Dict[str, int]:
        """
A/Bテストのバリアント分布を取得
        """
        distribution = {}
        for session_data in self.active_sessions.values():
            variant_name = session_data['variant'].get('name', 'unknown')
            distribution[variant_name] = distribution.get(variant_name, 0) + 1
        
        return distribution