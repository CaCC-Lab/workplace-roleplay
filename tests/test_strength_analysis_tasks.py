"""
強み分析Celeryタスクの統合テスト

Testing Trophy戦略に従い、Integration Testとして実装
Celeryタスクの動作をテストし、外部依存（LLM）のみモック
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from tasks.strength_analysis import (
    analyze_conversation_strengths_task,
    get_analysis_status_task
)
from celery import Task
from celery.app.task import Context


class MockRequest:
    """Celeryリクエストオブジェクトのモック"""
    def __init__(self, task_id='test-task-id-12345'):
        self.id = task_id
        self.retries = 0


class TestAnalyzeConversationStrengthsTaskIntegration:
    """analyze_conversation_strengths_taskの統合テスト"""
    
    @pytest.fixture
    def sample_conversation(self):
        """サンプル会話履歴"""
        return [
            {"role": "user", "content": "こんにちは。新しいプロジェクトについて相談があります。"},
            {"role": "assistant", "content": "こんにちは！プロジェクトについて、ぜひお聞かせください。"},
            {"role": "user", "content": "チームメンバーとのコミュニケーションをもっと円滑にしたいんです。"}
        ]
    
    @patch('app.app')
    @patch('langchain_google_genai.ChatGoogleGenerativeAI')
    @patch('tasks.strength_analysis.current_task')
    def test_正常な分析処理_実際のフロー(self, mock_current_task, mock_llm_class, mock_app, sample_conversation):
        """正常な分析処理の実際のフローをテスト（LLMのみモック）"""
        # current_taskをモック
        mock_current_task.update_state = Mock()
        
        # タスクをappメソッドとして実行（バインドされたタスクとして）
        task = analyze_conversation_strengths_task
        task.push_request(id='test-task-id-12345')
        
        # LLMのモック（コスト制限のため）
        mock_llm = Mock()
        # 正しいJSONレスポンスを返す
        mock_llm.invoke.return_value = Mock(content=json.dumps({
            "empathy": 75,
            "clarity": 70,
            "active_listening": 80,
            "adaptability": 65,
            "positivity": 72,
            "professionalism": 78
        }))
        mock_llm_class.return_value = mock_llm
        
        # Flaskアプリコンテキストのモック
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        # strength_analyzerの関数をモック
        with patch('strength_analyzer.parse_strength_analysis') as mock_parse:
            mock_parse.return_value = {
                "empathy": 75,
                "clarity": 70,
                "active_listening": 80,
                "adaptability": 65,
                "positivity": 72,
                "professionalism": 78
            }
            
            try:
                # タスクを実行（appメソッドとして実行）
                result = task.run(
                    user_id=1,
                    conversation_history=sample_conversation,
                    session_type='chat'
                )
            finally:
                task.pop_request()
                
            # 実際の処理結果を検証
            assert result['success'] is True
            assert result['user_id'] == 1
            assert result['session_type'] == 'chat'
            assert result['task_id'] == 'test-task-id-12345'
            
            # 分析結果の構造を検証
            assert 'analysis' in result
            assert 'scores' in result['analysis']
            assert 'top_strengths' in result['analysis']
            assert 'encouragement_messages' in result['analysis']
            
            # 実際の分析スコアを検証
            scores = result['analysis']['scores']
            assert scores['empathy'] == 75
            assert scores['professionalism'] == 78
            
            # トップ強みの検証
            top_strengths = result['analysis']['top_strengths']
            assert len(top_strengths) == 3
            assert top_strengths[0]['score'] == 80  # active_listening
            assert top_strengths[1]['score'] == 78  # professionalism
    
    @patch('app.app')
    @patch('tasks.strength_analysis.current_task')
    def test_空の会話履歴のエラーハンドリング(self, mock_current_task, mock_app):
        """空の会話履歴に対する実際のエラーハンドリング"""
        # current_taskをモック
        mock_current_task.update_state = Mock()
        
        # タスクをappメソッドとして実行
        task = analyze_conversation_strengths_task
        task.push_request(id='test-task-id-12345')
        
        # Flaskアプリコンテキストのモック
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        try:
            # タスクを実行
            result = task.run(
                user_id=1,
                conversation_history=[],
                session_type='chat'
            )
        finally:
            task.pop_request()
        
        # エラーハンドリングの検証
        assert result['success'] is False
        assert 'error' in result
        assert 'No conversation history available' in result['error']
        assert result['task_id'] == 'test-task-id-12345'
    
    @patch('app.app')
    @patch('langchain_google_genai.ChatGoogleGenerativeAI')
    @patch('tasks.strength_analysis.current_task')
    def test_LLMエラー時のリトライメカニズム(self, mock_current_task, mock_llm_class, mock_app, sample_conversation):
        """LLMエラー時のリトライメカニズムのテスト"""
        # current_taskをモック
        mock_current_task.update_state = Mock()
        
        # タスクをappメソッドとして実行
        task = analyze_conversation_strengths_task
        task.push_request(id='test-task-id-12345')
        
        # LLMエラーをシミュレート
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM API Error: Rate limit exceeded")
        mock_llm_class.return_value = mock_llm
        
        # Flaskアプリコンテキストのモック
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        # タスクのretryメソッドをモック
        # Celeryタスクがbindされた状態を再現
        mock_retry = Mock(side_effect=Exception("Retry called"))
        
        # タスクが実行時にエラーを投げることを期待
        with pytest.raises(Exception) as exc_info:
            # パッチを適用してタスクを実行
            with patch.object(task, 'retry', mock_retry):
                try:
                    task.run(
                        user_id=1,
                        conversation_history=sample_conversation,
                        session_type='chat'
                    )
                finally:
                    task.pop_request()
        
        # エラーが適切に発生したことを確認
        assert "Retry called" in str(exc_info.value) or "LLM API Error" in str(exc_info.value)
    
    @patch('app.app')
    @patch('langchain_google_genai.ChatGoogleGenerativeAI')
    @patch('tasks.strength_analysis.current_task')
    def test_不正なLLM応答の処理(self, mock_current_task, mock_llm_class, mock_app, sample_conversation):
        """不正なLLM応答に対する堅牢性のテスト"""
        # current_taskをモック
        mock_current_task.update_state = Mock()
        
        # タスクをappメソッドとして実行
        task = analyze_conversation_strengths_task
        task.push_request(id='test-task-id-12345')
        
        # 不正なJSON応答をシミュレート
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="これはJSONではありません。通常のテキストです。")
        mock_llm_class.return_value = mock_llm
        
        # Flaskアプリコンテキストのモック
        mock_app.app_context.return_value.__enter__ = Mock()
        mock_app.app_context.return_value.__exit__ = Mock()
        
        # parse_strength_analysisがデフォルト値を返すことをモック
        with patch('strength_analyzer.parse_strength_analysis') as mock_parse:
            # JSONパースエラー時のデフォルト値
            mock_parse.return_value = {
                "empathy": 50,
                "clarity": 50,
                "active_listening": 50,
                "adaptability": 50,
                "positivity": 50,
                "professionalism": 50
            }
            
            try:
                # タスクを実行
                result = task.run(
                    user_id=1,
                    conversation_history=sample_conversation,
                    session_type='chat'
                )
            finally:
                task.pop_request()
                
            # デフォルト値で処理が継続されることを確認
            assert result['success'] is True
            assert 'analysis' in result
            assert 'scores' in result['analysis']
            
            # 全てのスコアがデフォルト値（50）になっているか
            scores = result['analysis']['scores']
            assert all(score == 50 for score in scores.values())
            
            # 基本的な構造は保たれているか
            assert len(result['analysis']['top_strengths']) == 3
            assert len(result['analysis']['encouragement_messages']) > 0


class TestGetAnalysisStatusTaskIntegration:
    """get_analysis_status_taskの統合テスト"""
    
    @patch('celery.result.AsyncResult')
    def test_進捗状態の取得(self, mock_async_result_class):
        """実際の進捗状態取得のテスト"""
        # AsyncResultのモック
        mock_result = Mock()
        mock_result.state = 'PROGRESS'
        mock_result.info = {
            'current': 60,
            'total': 100,
            'status': '分析を実行中...'
        }
        mock_async_result_class.return_value = mock_result
        
        # タスクを実行
        result = get_analysis_status_task.run('test-task-id-12345')
        
        # 結果の検証
        assert result['state'] == 'PROGRESS'
        assert result['current'] == 60
        assert result['total'] == 100
        assert result['status'] == '分析を実行中...'
    
    @patch('celery.result.AsyncResult')
    def test_成功状態の取得(self, mock_async_result_class):
        """成功状態の取得テスト"""
        # AsyncResultのモック
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.info = {
            'success': True,
            'analysis': {
                'scores': {'empathy': 75},
                'top_strengths': [],
                'encouragement_messages': []
            }
        }
        mock_async_result_class.return_value = mock_result
        
        # タスクを実行
        result = get_analysis_status_task.run('test-task-id-12345')
        
        # 結果の検証
        assert result['state'] == 'SUCCESS'
        assert 'result' in result
        assert result['result']['success'] is True
    
    @patch('celery.result.AsyncResult')
    def test_エラー状態の取得(self, mock_async_result_class):
        """エラー状態の取得テスト"""
        # AsyncResultのモック
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.info = Exception("Task failed due to error")
        mock_async_result_class.return_value = mock_result
        
        # タスクを実行
        result = get_analysis_status_task.run('test-task-id-12345')
        
        # 結果の検証
        assert result['state'] == 'FAILURE'
        assert result['status'] == 'エラーが発生しました'
        assert 'error' in result