"""
LLMタスクのリトライ機構統合テスト
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from celery.exceptions import Retry

from tasks.llm import stream_chat_response, generate_feedback, LLMTask
from tasks.exceptions import RateLimitError, NetworkError, AuthenticationError


class TestLLMTaskBase:
    """LLMTask基底クラスのテスト"""
    
    @patch('tasks.llm.config')
    def test_llm_task_initialization(self, mock_config):
        """LLMTaskの初期化テスト"""
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_config.DEFAULT_TEMPERATURE = 0.7
        
        task = LLMTask()
        assert hasattr(task, '_llm_cache')
        assert isinstance(task._llm_cache, dict)
    
    @patch('tasks.llm.ChatGoogleGenerativeAI')
    @patch('tasks.llm.config')
    def test_get_llm_gemini_model(self, mock_config, mock_chat_class):
        """GeminiモデルのLLM取得テスト"""
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_config.DEFAULT_TEMPERATURE = 0.7
        
        mock_llm_instance = Mock()
        mock_chat_class.return_value = mock_llm_instance
        
        task = LLMTask()
        llm = task.get_llm("gemini-1.5-pro")
        
        # キャッシュされることを確認
        assert "gemini-1.5-pro" in task._llm_cache
        assert task._llm_cache["gemini-1.5-pro"] is mock_llm_instance
        
        # 2回目の呼び出しではキャッシュから取得
        llm2 = task.get_llm("gemini-1.5-pro")
        assert llm2 is mock_llm_instance
        
        # ChatGoogleGenerativeAIは1回だけ呼ばれる
        mock_chat_class.assert_called_once_with(
            model="gemini-1.5-pro",
            google_api_key="test-api-key",
            temperature=0.7,
            streaming=True
        )
    
    @patch('tasks.llm.ChatGoogleGenerativeAI')
    @patch('tasks.llm.config')
    def test_get_llm_with_provider_prefix(self, mock_config, mock_chat_class):
        """プロバイダープレフィックス付きモデル名のテスト"""
        mock_config.GOOGLE_API_KEY = "test-api-key"
        mock_config.DEFAULT_TEMPERATURE = 0.7
        
        mock_llm_instance = Mock()
        mock_chat_class.return_value = mock_llm_instance
        
        task = LLMTask()
        llm = task.get_llm("gemini/gemini-1.5-flash")
        
        mock_chat_class.assert_called_once_with(
            model="gemini-1.5-flash",
            google_api_key="test-api-key",
            temperature=0.7,
            streaming=True
        )
    
    def test_get_llm_unsupported_provider(self):
        """未サポートプロバイダーのエラーテスト"""
        task = LLMTask()
        
        with pytest.raises(ValueError, match="Unsupported provider: openai"):
            task.get_llm("openai/gpt-4")


class TestStreamChatResponse:
    """stream_chat_response タスクのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_task = Mock()
        self.mock_task.request = Mock()
        self.mock_task.request.id = "test-task-123"
        self.mock_task.request.retries = 0
        self.mock_task.get_llm = Mock()
        self.mock_task.save_partial_response = Mock()
        self.mock_task.retry_with_strategy = Mock()
    
    @patch('tasks.llm.redis_client')
    @patch('tasks.llm.time')
    def test_successful_streaming(self, mock_time, mock_redis):
        """正常なストリーミング処理のテスト"""
        mock_time.time.side_effect = [1000, 1001, 1002, 1003]  # start, chunk, chunk, complete
        
        # モックLLMとストリームの設定
        mock_llm = Mock()
        mock_chunk1 = Mock()
        mock_chunk1.content = "Hello"
        mock_chunk2 = Mock()
        mock_chunk2.content = " world"
        mock_llm.stream.return_value = [mock_chunk1, mock_chunk2]
        
        self.mock_task.get_llm.return_value = mock_llm
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        with patch('tasks.llm.track_streaming_chunks') as mock_track:
            result = stream_chat_response(
                self.mock_task,
                "session-123",
                "gemini-1.5-pro",
                messages
            )
        
        # 結果の確認
        assert result['status'] == 'success'
        assert result['content'] == 'Hello world'
        assert result['token_count'] == 2
        assert result['session_id'] == 'session-123'
        assert result['model'] == 'gemini-1.5-pro'
        
        # Redis Pub/Sub呼び出しの確認
        publish_calls = mock_redis.publish.call_args_list
        assert len(publish_calls) == 4  # start, chunk1, chunk2, complete
        
        # 開始通知
        start_call = json.loads(publish_calls[0][0][1])
        assert start_call['type'] == 'start'
        assert start_call['session_id'] == 'session-123'
        assert start_call['model'] == 'gemini-1.5-pro'
        
        # チャンク通知
        chunk1_call = json.loads(publish_calls[1][0][1])
        assert chunk1_call['type'] == 'chunk'
        assert chunk1_call['content'] == 'Hello'
        
        chunk2_call = json.loads(publish_calls[2][0][1])
        assert chunk2_call['type'] == 'chunk'
        assert chunk2_call['content'] == ' world'
        
        # 完了通知
        complete_call = json.loads(publish_calls[3][0][1])
        assert complete_call['type'] == 'complete'
        assert complete_call['total_content'] == 'Hello world'
        assert complete_call['token_count'] == 2
        
        # ストリーミングチャンク追跡の確認
        assert mock_track.call_count == 2
    
    @patch('tasks.llm.redis_client')
    def test_streaming_with_watch_mode(self, mock_redis):
        """観戦モードでのストリーミングテスト"""
        mock_llm = Mock()
        mock_chunk = Mock()
        mock_chunk.content = "Hello"
        mock_llm.stream.return_value = [mock_chunk]
        
        self.mock_task.get_llm.return_value = mock_llm
        
        messages = [{"role": "user", "content": "Hello"}]
        metadata = {"watch_mode": True, "speaker": "Assistant"}
        
        with patch('tasks.llm.track_streaming_chunks'):
            result = stream_chat_response(
                self.mock_task,
                "session-123",
                "gemini-1.5-pro",
                messages,
                metadata
            )
        
        # 観戦モード用の情報が含まれるか確認
        publish_calls = mock_redis.publish.call_args_list
        
        # チャンク通知に話者情報が含まれる
        chunk_call = json.loads(publish_calls[1][0][1])
        assert chunk_call['speaker'] == 'Assistant'
        
        # 完了通知にフォーマット済みコンテンツが含まれる
        complete_call = json.loads(publish_calls[2][0][1])
        assert complete_call['speaker'] == 'Assistant'
        assert complete_call['formatted_content'] == 'Assistant: Hello'
    
    @patch('tasks.llm.redis_client')
    @patch('tasks.llm.classify_error')
    def test_streaming_error_handling(self, mock_classify, mock_redis):
        """ストリーミング中のエラー処理テスト"""
        original_error = Exception("Connection failed")
        classified_error = NetworkError("Network error")
        mock_classify.return_value = classified_error
        
        # LLMがエラーを発生させる
        mock_llm = Mock()
        mock_llm.stream.side_effect = original_error
        self.mock_task.get_llm.return_value = mock_llm
        
        # リトライ戦略がRetryを発生させる
        self.mock_task.retry_with_strategy.side_effect = Retry("retry")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(Retry):
            stream_chat_response(
                self.mock_task,
                "session-123",
                "gemini-1.5-pro",
                messages
            )
        
        # エラー分類が呼ばれる
        mock_classify.assert_called_once_with(original_error)
        
        # リトライ戦略が呼ばれる
        self.mock_task.retry_with_strategy.assert_called_once()
    
    @patch('tasks.llm.redis_client')
    @patch('tasks.llm.classify_error')
    def test_streaming_final_error(self, mock_classify, mock_redis):
        """ストリーミングの最終エラー処理テスト"""
        original_error = Exception("Connection failed")
        classified_error = NetworkError("Network error")
        mock_classify.return_value = classified_error
        
        # LLMがエラーを発生させる
        mock_llm = Mock()
        mock_llm.stream.side_effect = original_error
        self.mock_task.get_llm.return_value = mock_llm
        
        # リトライ戦略も最終的にエラーを発生させる
        final_error = Exception("Max retries exceeded")
        self.mock_task.retry_with_strategy.side_effect = final_error
        
        messages = [{"role": "user", "content": "Hello"}]
        
        result = stream_chat_response(
            self.mock_task,
            "session-123",
            "gemini-1.5-pro",
            messages
        )
        
        # エラー結果が返される
        assert result['status'] == 'error'
        assert result['session_id'] == 'session-123'
        assert 'error' in result
        assert 'message' in result
        assert result['retry_count'] == 0
        
        # エラー通知がRedisに送信される
        error_publish_calls = [
            call for call in mock_redis.publish.call_args_list
            if 'error' in json.loads(call[0][1]).get('type', '')
        ]
        assert len(error_publish_calls) > 0
    
    @patch('tasks.llm.redis_client')
    def test_streaming_with_partial_content_on_error(self, mock_redis):
        """エラー時の部分コンテンツ処理テスト"""
        # 部分的にコンテンツが生成された後でエラーが発生する状況をシミュレート
        mock_llm = Mock()
        
        def streaming_with_error():
            # 最初のチャンクは成功
            mock_chunk = Mock()
            mock_chunk.content = "Hello"
            yield mock_chunk
            # 2番目でエラー
            raise Exception("Connection lost")
        
        mock_llm.stream.return_value = streaming_with_error()
        self.mock_task.get_llm.return_value = mock_llm
        
        # リトライ戦略が最終エラーを発生
        final_error = Exception("Max retries exceeded")
        self.mock_task.retry_with_strategy.side_effect = final_error
        
        messages = [{"role": "user", "content": "Hello"}]
        
        result = stream_chat_response(
            self.mock_task,
            "session-123",
            "gemini-1.5-pro",
            messages
        )
        
        # 部分コンテンツが結果に含まれる
        assert result['partial_content'] == 'Hello'
        
        # 部分レスポンス保存が呼ばれる
        self.mock_task.save_partial_response.assert_called_once()


class TestGenerateFeedback:
    """generate_feedback タスクのテスト"""
    
    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_task = Mock()
        self.mock_task.request = Mock()
        self.mock_task.request.id = "test-task-456"
        self.mock_task.request.retries = 0
        self.mock_task.get_llm = Mock()
        self.mock_task.retry_with_strategy = Mock()
    
    @patch('tasks.llm._analyze_strengths')
    @patch('tasks.llm._create_scenario_feedback_prompt')
    def test_scenario_feedback_generation(self, mock_create_prompt, mock_analyze):
        """シナリオフィードバック生成のテスト"""
        mock_create_prompt.return_value = "Test prompt"
        mock_analyze.return_value = {"empathy": 0.8, "clarity": 0.7}
        
        # モックLLMレスポンス
        mock_response = Mock()
        mock_response.content = "Great communication skills!"
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        self.mock_task.get_llm.return_value = mock_llm
        
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        scenario_info = {
            "title": "Meeting Introduction",
            "description": "Introduce yourself in a meeting"
        }
        
        result = generate_feedback(
            self.mock_task,
            "session-123",
            "gemini-1.5-pro",
            conversation_history,
            "scenario",
            scenario_info
        )
        
        # 結果の確認
        assert result['status'] == 'success'
        assert result['session_id'] == 'session-123'
        assert result['feedback'] == 'Great communication skills!'
        assert result['analysis'] == {"empathy": 0.8, "clarity": 0.7}
        assert result['model'] == 'gemini-1.5-pro'
        
        # プロンプト作成が呼ばれる
        mock_create_prompt.assert_called_once_with(conversation_history, scenario_info)
        
        # 強み分析が呼ばれる
        mock_analyze.assert_called_once_with('Great communication skills!')
    
    @patch('tasks.llm._analyze_strengths')
    @patch('tasks.llm._create_chat_feedback_prompt')
    def test_chat_feedback_generation(self, mock_create_prompt, mock_analyze):
        """雑談フィードバック生成のテスト"""
        mock_create_prompt.return_value = "Chat feedback prompt"
        mock_analyze.return_value = {"listening": 0.9}
        
        # モックLLMレスポンス
        mock_response = Mock()
        mock_response.content = "Good conversation flow!"
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        self.mock_task.get_llm.return_value = mock_llm
        
        conversation_history = [
            {"role": "user", "content": "How was your weekend?"},
            {"role": "assistant", "content": "It was great, thanks for asking!"}
        ]
        
        result = generate_feedback(
            self.mock_task,
            "session-456",
            "gemini-1.5-flash",
            conversation_history,
            "chat"
        )
        
        # 結果の確認
        assert result['status'] == 'success'
        assert result['feedback'] == 'Good conversation flow!'
        assert result['analysis'] == {"listening": 0.9}
        
        # チャット用プロンプト作成が呼ばれる
        mock_create_prompt.assert_called_once_with(conversation_history)
    
    @patch('tasks.llm.classify_error')
    def test_feedback_generation_error(self, mock_classify):
        """フィードバック生成エラーのテスト"""
        original_error = Exception("API Error")
        classified_error = RateLimitError("Rate limit exceeded")
        mock_classify.return_value = classified_error
        
        # LLMがエラーを発生させる
        mock_llm = Mock()
        mock_llm.invoke.side_effect = original_error
        self.mock_task.get_llm.return_value = mock_llm
        
        # リトライ戦略が最終エラーを発生
        final_error = Exception("Max retries exceeded")
        self.mock_task.retry_with_strategy.side_effect = final_error
        
        conversation_history = [{"role": "user", "content": "Hello"}]
        
        result = generate_feedback(
            self.mock_task,
            "session-789",
            "gemini-1.5-pro",
            conversation_history,
            "chat"
        )
        
        # エラー結果が返される
        assert result['status'] == 'error'
        assert result['session_id'] == 'session-789'
        assert 'error' in result
        assert result['message'] == 'フィードバックの生成中にエラーが発生しました'
        assert result['retry_count'] == 0


class TestPromptCreationFunctions:
    """プロンプト作成関数のテスト"""
    
    def test_create_scenario_feedback_prompt(self):
        """シナリオフィードバックプロンプト作成のテスト"""
        from tasks.llm import _create_scenario_feedback_prompt
        
        history = [
            {"role": "user", "content": "Hello, I'm new here"},
            {"role": "assistant", "content": "Welcome! Nice to meet you"}
        ]
        scenario = {
            "title": "First Day Introduction",
            "description": "Introduce yourself on your first day",
            "learning_points": ["confidence", "clarity", "friendliness"]
        }
        
        prompt = _create_scenario_feedback_prompt(history, scenario)
        
        # プロンプトに必要な要素が含まれているか確認
        assert "First Day Introduction" in prompt
        assert "Introduce yourself on your first day" in prompt
        assert "confidence, clarity, friendliness" in prompt
        assert "user: Hello, I'm new here" in prompt
        assert "assistant: Welcome! Nice to meet you" in prompt
    
    def test_create_chat_feedback_prompt(self):
        """雑談フィードバックプロンプト作成のテスト"""
        from tasks.llm import _create_chat_feedback_prompt
        
        history = [
            {"role": "user", "content": "How's the weather?"},
            {"role": "assistant", "content": "It's quite nice today!"}
        ]
        
        prompt = _create_chat_feedback_prompt(history)
        
        # プロンプトに会話内容が含まれているか確認
        assert "user: How's the weather?" in prompt
        assert "assistant: It's quite nice today!" in prompt
        assert "職場での雑談" in prompt
        assert "300-500文字程度" in prompt


class TestAnalyzeStrengths:
    """強み分析関数のテスト"""
    
    def test_analyze_strengths_basic(self):
        """基本的な強み分析のテスト"""
        from tasks.llm import _analyze_strengths
        
        feedback_text = "共感を示し、明確に意見を伝え、相手の話をよく聞いていました。"
        
        strengths = _analyze_strengths(feedback_text)
        
        # 各スキルのスコアが返される
        assert 'empathy' in strengths
        assert 'clarity' in strengths
        assert 'listening' in strengths
        assert 'problem_solving' in strengths
        assert 'assertiveness' in strengths
        assert 'flexibility' in strengths
        
        # キーワードマッチングによりスコアが上昇している
        assert strengths['empathy'] > 0.5  # "共感"が含まれる
        assert strengths['clarity'] > 0.5   # "明確"が含まれる
        assert strengths['listening'] > 0.5 # "聞いて"が含まれる
    
    def test_analyze_strengths_no_keywords(self):
        """キーワードがない場合の強み分析テスト"""
        from tasks.llm import _analyze_strengths
        
        feedback_text = "普通の会話でした。"
        
        strengths = _analyze_strengths(feedback_text)
        
        # すべてのスキルがデフォルト値（0.5）になる
        for skill, score in strengths.items():
            assert score == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])