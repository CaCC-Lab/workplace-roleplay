"""
履歴関連のルート定義
学習履歴の取得や管理のHTTPエンドポイントを管理
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any, List
from datetime import datetime

from services.session_service import SessionService
from scenarios import load_scenarios


# Blueprintの作成
history_bp = Blueprint('history', __name__)


@history_bp.route('/api/learning_history', methods=['GET'])
def get_learning_history():
    """
    学習履歴を取得するエンドポイント
    
    Returns:
        各モードの履歴を含むJSONレスポンス
    """
    try:
        # 各モードの履歴を取得
        chat_history = SessionService.get_session_history('chat_history')
        scenario_history_data = SessionService.get_session_data('scenario_history', {})
        watch_history = SessionService.get_session_history('watch_history')
        
        # 履歴サマリーの作成
        history_summary = {
            'chat': {
                'count': len(chat_history),
                'last_practice': _get_last_timestamp(chat_history),
                'recent_conversations': _format_chat_history(chat_history[-5:])
            },
            'scenarios': {
                'practiced_scenarios': _get_practiced_scenarios(scenario_history_data),
                'total_practices': _count_total_scenario_practices(scenario_history_data),
                'recent_practices': _format_scenario_practices(scenario_history_data)
            },
            'watch': {
                'count': len(watch_history),
                'last_watched': _get_last_timestamp(watch_history),
                'recent_sessions': _format_watch_sessions(watch_history)
            },
            'overall': {
                'total_activities': (
                    len(chat_history) + 
                    _count_total_scenario_practices(scenario_history_data) + 
                    len(watch_history)
                ),
                'active_since': _get_earliest_activity_time()
            }
        }
        
        return jsonify(history_summary)
        
    except Exception as e:
        print(f"Get learning history error: {str(e)}")
        return jsonify({'error': '学習履歴の取得に失敗しました'}), 500


@history_bp.route('/api/chat_history', methods=['GET'])
def get_chat_history():
    """
    チャット履歴の詳細を取得するエンドポイント
    
    Returns:
        チャット履歴を含むJSONレスポンス
    """
    try:
        history = SessionService.get_session_history('chat_history')
        
        return jsonify({
            'history': history,
            'count': len(history),
            'start_time': SessionService.get_session_start_time('chat')
        })
        
    except Exception as e:
        print(f"Get chat history error: {str(e)}")
        return jsonify({'error': 'チャット履歴の取得に失敗しました'}), 500


@history_bp.route('/api/scenario_history/<scenario_id>', methods=['GET'])
def get_scenario_history(scenario_id: str):
    """
    特定のシナリオの履歴を取得するエンドポイント
    
    Args:
        scenario_id: シナリオID
        
    Returns:
        シナリオ履歴を含むJSONレスポンス
    """
    try:
        history = SessionService.get_session_history('scenario_history', scenario_id)
        
        # シナリオ情報を取得
        scenarios = load_scenarios()
        scenario_info = scenarios.get(scenario_id, {})
        
        return jsonify({
            'scenario_id': scenario_id,
            'scenario_title': scenario_info.get('title', '不明'),
            'history': history,
            'count': len(history),
            'start_time': SessionService.get_session_start_time('scenario', scenario_id)
        })
        
    except Exception as e:
        print(f"Get scenario history error: {str(e)}")
        return jsonify({'error': 'シナリオ履歴の取得に失敗しました'}), 500


@history_bp.route('/api/clear_all_history', methods=['POST'])
def clear_all_history():
    """
    すべての履歴をクリアするエンドポイント
    
    Returns:
        成功メッセージを含むJSONレスポンス
    """
    try:
        # 各モードの履歴をクリア
        SessionService.clear_session_history('chat_history')
        SessionService.clear_session_history('scenario_history')
        SessionService.clear_session_history('watch_history')
        
        # 開始時刻もクリア
        SessionService.remove_session_data('chat_start_time')
        SessionService.remove_session_data('scenario_start_time')
        SessionService.remove_session_data('watch_start_time')
        
        return jsonify({
            'message': 'すべての履歴をクリアしました',
            'cleared': ['chat', 'scenarios', 'watch']
        })
        
    except Exception as e:
        print(f"Clear all history error: {str(e)}")
        return jsonify({'error': '履歴のクリアに失敗しました'}), 500


# ヘルパー関数

def _get_last_timestamp(history: List[Dict[str, Any]]) -> str:
    """履歴から最後のタイムスタンプを取得"""
    if not history:
        return None
    
    last_entry = history[-1]
    return last_entry.get('timestamp')


def _format_chat_history(history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """チャット履歴を整形"""
    formatted = []
    for entry in history:
        if 'user' in entry and 'assistant' in entry:
            formatted.append({
                'user_message': entry['user'][:50] + '...' if len(entry['user']) > 50 else entry['user'],
                'assistant_response': entry['assistant'][:50] + '...' if len(entry['assistant']) > 50 else entry['assistant'],
                'timestamp': entry.get('timestamp', '')
            })
    return formatted


def _get_practiced_scenarios(scenario_history_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """練習したシナリオのリストを取得"""
    scenarios = load_scenarios()
    practiced = []
    
    for scenario_id, history in scenario_history_data.items():
        if isinstance(history, list) and len(history) > 0:
            scenario_info = scenarios.get(scenario_id, {})
            practiced.append({
                'id': scenario_id,
                'title': scenario_info.get('title', '不明'),
                'practice_count': len(history),
                'last_practice': _get_last_timestamp(history)
            })
    
    return practiced


def _count_total_scenario_practices(scenario_history_data: Dict[str, Any]) -> int:
    """シナリオ練習の総数をカウント"""
    total = 0
    for history in scenario_history_data.values():
        if isinstance(history, list):
            total += len(history)
    return total


def _format_scenario_practices(scenario_history_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """最近のシナリオ練習を整形"""
    scenarios = load_scenarios()
    all_practices = []
    
    # すべての練習を収集
    for scenario_id, history in scenario_history_data.items():
        if isinstance(history, list):
            scenario_info = scenarios.get(scenario_id, {})
            for entry in history:
                if 'timestamp' in entry:
                    all_practices.append({
                        'scenario_id': scenario_id,
                        'scenario_title': scenario_info.get('title', '不明'),
                        'timestamp': entry['timestamp'],
                        'character': entry.get('character', '不明')
                    })
    
    # タイムスタンプでソートして最新5件を返す
    all_practices.sort(key=lambda x: x['timestamp'], reverse=True)
    return all_practices[:5]


def _format_watch_sessions(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """観戦セッションを整形"""
    sessions = []
    current_session = None
    
    for entry in history:
        if 'speaker' in entry and 'partner_type' in entry:
            # 新しいセッションの開始を検出
            if current_session is None or entry['speaker'] == 'AI1':
                if current_session is not None:
                    sessions.append(current_session)
                
                current_session = {
                    'start_time': entry.get('timestamp', ''),
                    'messages': 1,
                    'participants': set([entry['partner_type']])
                }
            else:
                current_session['messages'] += 1
                current_session['participants'].add(entry['partner_type'])
    
    # 最後のセッションを追加
    if current_session is not None:
        sessions.append(current_session)
    
    # participantsをリストに変換
    for session in sessions:
        session['participants'] = list(session['participants'])
    
    return sessions[-5:]  # 最新5セッション


def _get_earliest_activity_time() -> str:
    """最も古いアクティビティの時刻を取得"""
    times = []
    
    # 各モードの開始時刻を収集
    chat_start = SessionService.get_session_start_time('chat')
    if chat_start:
        times.append(chat_start)
    
    scenario_start = SessionService.get_session_start_time('scenario')
    if scenario_start:
        times.append(scenario_start)
    
    watch_start = SessionService.get_session_start_time('watch')
    if watch_start:
        times.append(watch_start)
    
    if times:
        return min(times)
    
    return None