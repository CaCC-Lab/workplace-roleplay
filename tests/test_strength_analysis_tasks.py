"""
強み分析Celeryタスクのユニットテスト（修正版）

TDD原則に従い、実装前にテストを作成
Celeryタスクの正しい呼び出し方法に修正
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from celery import states, current_task
from tasks.strength_analysis import (
    analyze_conversation_strengths_task,
    get_analysis_status_task
)


class TestAnalyzeConversationStrengthsTask:
    """analyze_conversation_strengths_taskのテスト"""
    
    @pytest.fixture
    def sample_conversation(self):
        """サンプル会話履歴"""
        return [
            {"role": "user", "content": "こんにちは。新しいプロジェクトについて相談があります。"},
            {"role": "assistant", "content": "こんにちは！プロジェクトについて、ぜひお聞かせください。"},
            {"role": "user", "content": "チームメンバーとのコミュニケーションをもっと円滑にしたいんです。"}
        ]
    
    @patch('app.app')
    def test_正常な分析処理(self, mock_app, sample_conversation):
        """正常な分析処理のテスト"""
        # LLMのモック
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content=json.dumps({
            "empathy": 75,
            "clarity": 70,
            "active_listening": 80,
            "adaptability": 65,
            "positivity": 72,
            "professionalism": 78
        }))
        
        # タスクメソッドのモック
        with patch.object(analyze_conversation_strengths_task, 'update_state'), \
             patch.object(analyze_conversation_strengths_task, 'get_llm', return_value=mock_llm), \
             patch('tasks.strength_analysis.current_task') as mock_current_task:
            # current_taskのモック設定
            mock_current_task.request.id = 'test-task-id'
            mock_current_task.update_state = Mock()
            
            # タスク実行
            with mock_app.app_context():
                result = analyze_conversation_strengths_task.run(
                    user_id=1,
                    conversation_history=sample_conversation,
                    session_type='chat'
                )
        
            # 検証
            assert result['success'] is True
            assert result['user_id'] == 1
            assert result['session_type'] == 'chat'
            assert 'analysis' in result
            assert 'scores' in result['analysis']
            assert 'top_strengths' in result['analysis']
            assert 'encouragement_messages' in result['analysis']
            
            # 結果の詳細確認
            assert len(result['analysis']['top_strengths']) == 3
            assert result['analysis']['scores']['empathy'] == 75
    
    @patch('app.app')
    def test_空の会話履歴の処理(self, mock_app):
        """空の会話履歴の場合のテスト"""
        
        with patch('tasks.strength_analysis.current_task') as mock_current_task:
            # current_taskのモック設定
            mock_current_task.request.id = 'test-task-id'
            mock_current_task.update_state = Mock()
            
            with mock_app.app_context():
                result = analyze_conversation_strengths_task.run(
                    user_id=1,
                    conversation_history=[],
                    session_type='chat'
                )
        
        assert result['success'] is False
        assert result['error'] == 'No conversation history available'
    
    @patch('app.app')
    def test_LLMエラー時の処理(self, mock_app, sample_conversation):
        """LLMエラー時の処理のテスト"""
        
        # LLMエラーをシミュレート
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM API Error")
        
        # タスク実行（retryの代わりにエラー処理のテスト）
        with mock_app.app_context():
            with patch.object(analyze_conversation_strengths_task, 'retry') as mock_retry, \
                 patch.object(analyze_conversation_strengths_task, 'get_llm', return_value=mock_llm), \
                 patch('tasks.strength_analysis.current_task') as mock_current_task:
                # current_taskのモック設定
                mock_current_task.request.id = 'test-task-id'
                mock_current_task.update_state = Mock()
                
                mock_retry.side_effect = Exception("Retry called")
                
                with pytest.raises(Exception, match="Retry called"):
                    analyze_conversation_strengths_task.run(
                        user_id=1,
                        conversation_history=sample_conversation,
                        session_type='chat'
                    )
                
                # リトライが呼ばれたことを確認
                assert mock_retry.called


class TestGetAnalysisStatusTask:
    """get_analysis_status_taskのテスト"""
    
    @patch('celery.result.AsyncResult')
    def test_ペンディング状態の取得(self, mock_async_result):
        """PENDING状態のタスクステータス取得テスト"""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_async_result.return_value = mock_result
        
        result = get_analysis_status_task.run('test-task-id')
        
        assert result['state'] == 'PENDING'
        assert result['current'] == 0
        assert result['total'] == 100
        assert 'タスクが開始されるのを待っています' in result['status']
    
    @patch('celery.result.AsyncResult')
    def test_進行中状態の取得(self, mock_async_result):
        """PROGRESS状態のタスクステータス取得テスト"""
        mock_result = Mock()
        mock_result.state = 'PROGRESS'
        mock_result.info = {
            'current': 60,
            'total': 100,
            'status': '分析を実行中...'
        }
        mock_async_result.return_value = mock_result
        
        result = get_analysis_status_task.run('test-task-id')
        
        assert result['state'] == 'PROGRESS'
        assert result['current'] == 60
        assert result['total'] == 100
        assert result['status'] == '分析を実行中...'
    
    @patch('celery.result.AsyncResult')
    def test_成功状態の取得(self, mock_async_result):
        """SUCCESS状態のタスクステータス取得テスト"""
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.info = {
            'success': True,
            'analysis': {'scores': {}}
        }
        mock_async_result.return_value = mock_result
        
        result = get_analysis_status_task.run('test-task-id')
        
        assert result['state'] == 'SUCCESS'
        assert 'result' in result
        assert result['result']['success'] is True
    
    @patch('celery.result.AsyncResult')
    def test_失敗状態の取得(self, mock_async_result):
        """FAILURE状態のタスクステータス取得テスト"""
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.info = Exception("Task failed")
        mock_async_result.return_value = mock_result
        
        result = get_analysis_status_task.run('test-task-id')
        
        assert result['state'] == 'FAILURE'
        assert result['status'] == 'エラーが発生しました'
        assert 'error' in result
    
    @patch('celery.result.AsyncResult')
    def test_例外発生時の処理(self, mock_async_result):
        """例外発生時のエラーハンドリングテスト"""
        mock_async_result.side_effect = Exception("Connection error")
        
        result = get_analysis_status_task.run('test-task-id')
        
        assert result['state'] == 'ERROR'
        assert 'ステータス取得中にエラーが発生しました' in result['status']
        assert result['error'] == 'Connection error'