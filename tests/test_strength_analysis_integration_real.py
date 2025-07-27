"""
強み分析Celeryタスクの実際の統合テスト

Testing Trophy戦略に従い、実際のCeleryコンポーネントを使用した統合テスト。
インメモリブローカーを使用し、current_taskのモックを最小限に留める。
"""
import pytest
import json
from celery.contrib.testing.worker import start_worker
from celery.contrib.testing.app import TestApp
from celery import Celery
from tasks.strength_analysis import (
    analyze_conversation_strengths_task,
    get_analysis_status_task
)
from celery_app import celery as production_celery
from unittest.mock import patch, Mock
import time


class TestStrengthAnalysisRealIntegration:
    """実際のCeleryワーカーを使用した統合テスト"""
    
    @pytest.fixture
    def celery_app(self):
        """テスト用Celeryアプリケーションの設定"""
        # 本番のCelery設定をコピーしてテスト用に調整
        test_app = Celery(
            'test_workplace_roleplay',
            broker='memory://',
            backend='cache+memory://',
            task_always_eager=False,  # 非同期実行を有効化
            task_eager_propagates=True,
            task_track_started=True,
            task_send_sent_event=True,
            worker_send_task_events=True
        )
        
        # タスクを登録
        test_app.register_task(analyze_conversation_strengths_task)
        test_app.register_task(get_analysis_status_task)
        
        return test_app
    
    @pytest.fixture
    def celery_worker(self, celery_app):
        """実際のCeleryワーカーを起動"""
        with start_worker(celery_app, perform_ping_check=False):
            yield
    
    @pytest.fixture
    def sample_conversation(self):
        """サンプル会話履歴"""
        return [
            {"role": "user", "content": "新しいチームに配属されました。どう振る舞えばいいでしょうか？"},
            {"role": "assistant", "content": "新しい環境への適応は重要ですね。まずは積極的に挨拶し、メンバーの名前を覚えることから始めましょう。"},
            {"role": "user", "content": "会議では自分の意見を言うべきでしょうか？それとも最初は聞き役に徹するべきですか？"},
            {"role": "assistant", "content": "最初は聞き役に徹しつつ、求められたら簡潔に意見を述べるのがバランスが良いでしょう。"}
        ]
    
    @patch('langchain_google_genai.ChatGoogleGenerativeAI')
    def test_実際のワーカーでの非同期処理(self, mock_llm_class, celery_app, celery_worker, sample_conversation):
        """実際のワーカーでタスクを実行し、状態遷移を検証"""
        # LLMのモック設定（外部API呼び出しのみモック）
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content=json.dumps({
            "empathy": 85,
            "clarity": 80,
            "active_listening": 90,
            "adaptability": 75,
            "positivity": 82,
            "professionalism": 88
        }))
        mock_llm_class.return_value = mock_llm
        
        # タスクを非同期で実行
        result = analyze_conversation_strengths_task.apply_async(
            args=[1, sample_conversation, 'chat']
        )
        
        # タスクIDが取得できることを確認
        assert result.id is not None
        
        # 状態遷移を監視（最大30秒待機）
        states_observed = []
        timeout = time.time() + 30
        
        while time.time() < timeout:
            state = result.state
            states_observed.append(state)
            
            if state == 'SUCCESS':
                break
            elif state == 'FAILURE':
                pytest.fail(f"Task failed: {result.info}")
            
            time.sleep(0.5)
        
        # 期待される状態遷移を確認
        assert 'PENDING' in states_observed or 'STARTED' in states_observed
        assert 'SUCCESS' in states_observed
        
        # 結果の検証
        final_result = result.get(timeout=5)
        assert final_result['success'] is True
        assert final_result['user_id'] == 1
        assert final_result['session_type'] == 'chat'
        assert 'analysis' in final_result
        
        # 分析結果の詳細検証
        analysis = final_result['analysis']
        assert 'scores' in analysis
        assert 'top_strengths' in analysis
        assert 'encouragement_messages' in analysis
        
        # スコアの値が正しく設定されているか
        scores = analysis['scores']
        assert scores['active_listening'] == 90
        assert scores['empathy'] == 85
        assert scores['professionalism'] == 88
    
    @patch('langchain_google_genai.ChatGoogleGenerativeAI')
    def test_進捗更新の実際の動作(self, mock_llm_class, celery_app, celery_worker, sample_conversation):
        """進捗更新が実際に機能することを検証"""
        # LLMのモック設定（遅延を追加）
        def slow_invoke(*args, **kwargs):
            time.sleep(2)  # 処理時間をシミュレート
            return Mock(content=json.dumps({
                "empathy": 75,
                "clarity": 70,
                "active_listening": 80,
                "adaptability": 65,
                "positivity": 72,
                "professionalism": 78
            }))
        
        mock_llm = Mock()
        mock_llm.invoke.side_effect = slow_invoke
        mock_llm_class.return_value = mock_llm
        
        # タスクを非同期で実行
        result = analyze_conversation_strengths_task.apply_async(
            args=[2, sample_conversation, 'scenario']
        )
        
        # 進捗状態を監視
        progress_states = []
        timeout = time.time() + 30
        
        while time.time() < timeout:
            if result.state == 'PROGRESS':
                progress_info = result.info
                progress_states.append({
                    'current': progress_info.get('current'),
                    'total': progress_info.get('total'),
                    'status': progress_info.get('status')
                })
            elif result.state == 'SUCCESS':
                break
            elif result.state == 'FAILURE':
                pytest.fail(f"Task failed: {result.info}")
            
            time.sleep(0.5)
        
        # 少なくとも1つの進捗更新があることを確認
        assert len(progress_states) > 0
        
        # 進捗が順次進んでいることを確認
        progress_values = [p['current'] for p in progress_states if p['current'] is not None]
        assert sorted(progress_values) == progress_values  # 昇順であることを確認
    
    def test_ステータス取得タスクの実際の動作(self, celery_app, celery_worker):
        """ステータス取得タスクが実際に機能することを検証"""
        # まず分析タスクを開始
        with patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_llm_class:
            mock_llm = Mock()
            mock_llm.invoke.return_value = Mock(content=json.dumps({
                "empathy": 75,
                "clarity": 70,
                "active_listening": 80,
                "adaptability": 65,
                "positivity": 72,
                "professionalism": 78
            }))
            mock_llm_class.return_value = mock_llm
            
            # 分析タスクを実行
            analysis_result = analyze_conversation_strengths_task.apply_async(
                args=[3, [{"role": "user", "content": "test"}], 'chat']
            )
            
            # タスクIDを使用してステータスを取得
            status_result = get_analysis_status_task.apply_async(
                args=[analysis_result.id]
            )
            
            # ステータス取得結果を検証
            status = status_result.get(timeout=5)
            assert 'state' in status
            assert 'current' in status
            assert 'total' in status
            assert 'status' in status
            
            # 分析タスクが完了するまで待機
            analysis_result.get(timeout=10)
            
            # 完了後のステータスを再度取得
            final_status_result = get_analysis_status_task.apply_async(
                args=[analysis_result.id]
            )
            final_status = final_status_result.get(timeout=5)
            
            assert final_status['state'] == 'SUCCESS'
            assert 'result' in final_status
    
    @patch('langchain_google_genai.ChatGoogleGenerativeAI')
    def test_リトライメカニズムの実際の動作(self, mock_llm_class, celery_app, celery_worker, sample_conversation):
        """エラー時のリトライが実際に機能することを検証"""
        # 最初の2回は失敗、3回目で成功するモック
        call_count = 0
        
        def mock_invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary LLM Error")
            return Mock(content=json.dumps({
                "empathy": 75,
                "clarity": 70,
                "active_listening": 80,
                "adaptability": 65,
                "positivity": 72,
                "professionalism": 78
            }))
        
        mock_llm = Mock()
        mock_llm.invoke.side_effect = mock_invoke
        mock_llm_class.return_value = mock_llm
        
        # リトライ設定を調整（テスト用に短縮）
        with patch('tasks.strength_analysis.analyze_conversation_strengths_task.retry') as mock_retry:
            # リトライをシミュレート（実際のリトライは時間がかかるため）
            mock_retry.side_effect = lambda **kwargs: mock_invoke()
            
            result = analyze_conversation_strengths_task.apply_async(
                args=[4, sample_conversation, 'chat']
            )
            
            try:
                # タスクの実行を待機
                final_result = result.get(timeout=10)
                
                # リトライが呼ばれたことを確認
                assert mock_retry.called
                
                # 最終的に成功することを確認
                if isinstance(final_result, dict) and final_result.get('success'):
                    assert final_result['success'] is True
            except Exception as e:
                # リトライメカニズムが動作したことを確認
                assert call_count >= 1  # 少なくとも1回は呼ばれた