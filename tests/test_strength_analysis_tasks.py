"""
強み分析Celeryタスクのユニットテスト

TDD原則に従い、実装前にテストを作成
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from celery import states
from tasks.strength_analysis import (
    analyze_conversation_strengths_task,
    get_analysis_status_task
)


class TestAnalyzeConversationStrengthsTask:
    """analyze_conversation_strengths_taskのテスト"""
    
    @pytest.fixture
    def mock_task(self):
        """モックタスクのセットアップ"""
        task = Mock()
        task.request.id = 'test-task-id'
        task.update_state = Mock()
        task.retry = Mock()
        return task
    
    @pytest.fixture
    def sample_conversation(self):
        """サンプル会話履歴"""
        return [
            {"role": "user", "content": "こんにちは。新しいプロジェクトについて相談があります。"},
            {"role": "assistant", "content": "こんにちは！プロジェクトについて、ぜひお聞かせください。"},
            {"role": "user", "content": "チームメンバーとのコミュニケーションをもっと円滑にしたいんです。"}
        ]
    
    @patch('app.app')
    def test_正常な分析処理(self, mock_app, mock_task, sample_conversation):
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
        
        # get_llmメソッドのモック
        mock_task.get_llm = Mock(return_value=mock_llm)
        
        # タスク実行
        with mock_app.app_context():
            result = analyze_conversation_strengths_task(
                mock_task,
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
        
        # 進捗更新が呼ばれたことを確認
        assert mock_task.update_state.call_count >= 4
        
        # 最終的な進捗が100%になっていることを確認
        final_call = mock_task.update_state.call_args_list[-1]
        assert final_call[1]['meta']['current'] == 100
        assert final_call[1]['meta']['total'] == 100
    
    @patch('app.app')
    def test_空の会話履歴の処理(self, mock_app, mock_task):
        """空の会話履歴の場合のテスト"""
        with mock_app.app_context():
            result = analyze_conversation_strengths_task(
                mock_task,
                user_id=1,
                conversation_history=[],
                session_type='chat'
            )
        
        assert result['success'] is False
        assert result['error'] == 'No conversation history available'
    
    @patch('app.app')
    def test_LLMエラー時のリトライ(self, mock_app, mock_task):
        """LLMエラー時のリトライ処理のテスト"""
        # LLMエラーをシミュレート
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM API Error")
        mock_task.get_llm = Mock(return_value=mock_llm)
        
        # タスク実行
        with mock_app.app_context():
            with pytest.raises(Exception):
                analyze_conversation_strengths_task(
                    mock_task,
                    user_id=1,
                    conversation_history=[{"role": "user", "content": "test"}],
                    session_type='chat'
                )
        
        # リトライが呼ばれたことを確認
        mock_task.retry.assert_called_once()
        assert mock_task.retry.call_args[1]['countdown'] == 60
    
    @patch('app.app')
    def test_プロンプト生成の正確性(self, mock_app, mock_task, sample_conversation):
        """プロンプト生成が正しく行われるかのテスト"""
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content='{"empathy": 50}')
        mock_task.get_llm = Mock(return_value=mock_llm)
        
        with mock_app.app_context():
            analyze_conversation_strengths_task(
                mock_task,
                user_id=1,
                conversation_history=sample_conversation,
                session_type='chat'
            )
        
        # LLMが呼ばれた際のメッセージを確認
        call_args = mock_llm.invoke.call_args[0][0]
        assert len(call_args) == 2  # SystemMessageとHumanMessage
        
        # プロンプトに会話履歴が含まれていることを確認
        human_message = call_args[1].content
        assert "こんにちは。新しいプロジェクトについて相談があります。" in human_message


class TestGetAnalysisStatusTask:
    """get_analysis_status_taskのテスト"""
    
    @patch('celery.result.AsyncResult')
    def test_ペンディング状態の取得(self, mock_async_result):
        """PENDING状態のタスクステータス取得テスト"""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_async_result.return_value = mock_result
        
        task = Mock()
        result = get_analysis_status_task(task, 'test-task-id')
        
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
        
        task = Mock()
        result = get_analysis_status_task(task, 'test-task-id')
        
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
        
        task = Mock()
        result = get_analysis_status_task(task, 'test-task-id')
        
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
        
        task = Mock()
        result = get_analysis_status_task(task, 'test-task-id')
        
        assert result['state'] == 'FAILURE'
        assert result['status'] == 'エラーが発生しました'
        assert 'error' in result
    
    @patch('celery.result.AsyncResult')
    def test_例外発生時の処理(self, mock_async_result):
        """例外発生時のエラーハンドリングテスト"""
        mock_async_result.side_effect = Exception("Connection error")
        
        task = Mock()
        result = get_analysis_status_task(task, 'test-task-id')
        
        assert result['state'] == 'ERROR'
        assert 'ステータス取得中にエラーが発生しました' in result['status']
        assert result['error'] == 'Connection error'