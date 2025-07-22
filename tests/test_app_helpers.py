"""
app.pyのヘルパー関数とユーティリティのテスト - カバレッジ向上のため
TDD原則に従い、セッション管理、エラーハンドリング、応答処理をテスト
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import json
from flask import session, g

# テスト対象の関数
from app import (
    extract_content,
    handle_llm_error,
    create_model_and_get_response,
    initialize_session_history
)
from errors import AppError, ValidationError, AuthenticationError


class TestContentExtraction:
    """コンテンツ抽出機能のテスト"""
    
    def test_extract_content_langchain_message(self):
        """LangChainメッセージからコンテンツを抽出することを確認"""
        # 実際のAIMessageを使用（MockではなくAIMessage型として認識される）
        from langchain_core.messages import AIMessage
        mock_message = AIMessage(content="テストメッセージ")
        
        result = extract_content(mock_message)
        
        assert result == "テストメッセージ"
    
    def test_extract_content_string(self):
        """文字列から直接コンテンツを抽出することを確認"""
        test_string = "直接文字列"
        
        result = extract_content(test_string)
        
        assert result == "直接文字列"
    
    def test_extract_content_dict_with_content(self):
        """contentキーを持つ辞書からコンテンツを抽出することを確認"""
        test_dict = {"content": "辞書のコンテンツ"}
        
        result = extract_content(test_dict)
        
        assert result == "辞書のコンテンツ"
    
    def test_extract_content_dict_without_content(self):
        """contentキーを持たない辞書の処理を確認"""
        test_dict = {"message": "メッセージ"}
        
        result = extract_content(test_dict)
        
        # 実装では"message"キーがあるのでその値を返す
        assert result == "メッセージ"
    
    def test_extract_content_none(self):
        """None値の処理を確認"""
        result = extract_content(None)
        
        # 実装ではstr(None)つまり"None"文字列を返す
        assert result == "None"
    
    def test_extract_content_empty_string(self):
        """空文字列の処理を確認"""
        result = extract_content("")
        
        assert result == ""


class TestBasicHelpers:
    """基本的なヘルパー関数のテスト"""
    
    def test_session_initialization_basic(self, app_context):
        """セッション初期化の基本動作を確認"""
        with app_context.test_request_context():
            initialize_session_history('test_history')
            
            assert 'test_history' in session
            assert session['test_history'] == []


class TestLLMErrorHandling:
    """LLMエラーハンドリングのテスト"""
    
    @patch('app.handle_error')
    def test_handle_llm_error_基本(self, mock_handle_error):
        """基本的なLLMエラーハンドリングを確認"""
        mock_response = MagicMock()
        mock_response.get_json.return_value = {
            'error': {'message': 'テストエラー'}
        }
        mock_handle_error.return_value = (mock_response, 500)
        
        error = Exception("LLMエラー")
        error_msg, status_code, fallback_result, fallback_model = handle_llm_error(error)
        
        assert error_msg == "テストエラー"
        assert status_code == 500
        assert fallback_result is None
        assert fallback_model is None
    
    @patch('app.handle_error')
    def test_handle_llm_error_フォールバック成功(self, mock_handle_error):
        """フォールバック機能が正常に動作することを確認"""
        mock_response = MagicMock()
        mock_response.get_json.return_value = {
            'error': {'message': 'API エラー'}
        }
        mock_handle_error.return_value = (mock_response, 503)
        
        # フォールバック関数のモック
        mock_fallback = MagicMock()
        mock_fallback.return_value = {"content": "フォールバック応答"}
        
        error = Exception("API接続エラー")
        error_msg, status_code, fallback_result, fallback_model = handle_llm_error(
            error, 
            fallback_function=mock_fallback,
            fallback_data={"test": "data"}
        )
        
        assert error_msg == "API エラー"
        assert status_code == 503
        assert fallback_result == {"content": "フォールバック応答"}
        assert fallback_model == "gemini-1.5-flash"
        mock_fallback.assert_called_once()
    
    @patch('app.handle_error')
    @patch('app.logger', create=True)
    def test_handle_llm_error_フォールバック失敗(self, mock_logger, mock_handle_error):
        """フォールバック失敗時の処理を確認"""
        mock_response = MagicMock()
        mock_response.get_json.return_value = {
            'error': {'message': 'LLMエラー'}
        }
        mock_handle_error.return_value = (mock_response, 500)
        
        # フォールバック関数が例外を発生
        mock_fallback = MagicMock()
        mock_fallback.side_effect = Exception("フォールバックエラー")
        
        error = Exception("元のエラー")
        error_msg, status_code, fallback_result, fallback_model = handle_llm_error(
            error,
            fallback_function=mock_fallback,
            fallback_data={"test": "data"}
        )
        
        assert error_msg == "LLMエラー"
        assert status_code == 500
        assert fallback_result is None
        assert fallback_model is None
        # ログが呼ばれることを確認
        mock_logger.error.assert_called()
    
    @patch('app.handle_error')
    def test_handle_llm_error_レスポンス形式不正(self, mock_handle_error):
        """レスポンス形式が不正な場合の処理を確認"""
        mock_handle_error.return_value = ("エラー文字列", 400)
        
        error = Exception("レスポンス形式エラー")
        error_msg, status_code, fallback_result, fallback_model = handle_llm_error(error)
        
        assert error_msg == "レスポンス形式エラー"
        assert status_code == 400


class TestCreateModelAndGetResponse:
    """モデル作成と応答取得のテスト"""
    
    @patch('app.initialize_llm')
    @patch('app.extract_content')
    def test_create_model_and_get_response_成功(self, mock_extract, mock_init_llm):
        """モデル作成と応答取得が成功することを確認"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_init_llm.return_value = mock_llm
        mock_extract.return_value = "応答コンテンツ"
        
        result = create_model_and_get_response(
            "gemini-1.5-flash", 
            "テストプロンプト",
            extract=True
        )
        
        assert result == "応答コンテンツ"
        mock_init_llm.assert_called_once_with("gemini-1.5-flash")
        mock_llm.invoke.assert_called_once_with("テストプロンプト")
        mock_extract.assert_called_once_with(mock_response)
    
    @patch('app.initialize_llm')
    def test_create_model_and_get_response_extract無効(self, mock_init_llm):
        """extract=Falseの場合に生レスポンスが返されることを確認"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_init_llm.return_value = mock_llm
        
        result = create_model_and_get_response(
            "gemini-1.5-pro",
            ["メッセージリスト"],
            extract=False
        )
        
        assert result == mock_response
    
    @patch('app.initialize_llm')
    def test_create_model_and_get_response_エラー(self, mock_init_llm):
        """エラーが適切に伝播されることを確認"""
        mock_init_llm.side_effect = Exception("初期化エラー")
        
        with pytest.raises(Exception, match="初期化エラー"):
            create_model_and_get_response("gemini-1.5-flash", "テストプロンプト")


class TestSessionHelpers:
    """セッション管理ヘルパーのテスト"""
    
    def test_initialize_session_history_新規(self, app_context):
        """新規セッション履歴の初期化を確認"""
        with app_context.test_request_context():
            initialize_session_history('test_history')
            
            assert 'test_history' in session
            assert session['test_history'] == []
    
    def test_initialize_session_history_サブキー(self, app_context):
        """サブキー付きセッション履歴の初期化を確認"""
        with app_context.test_request_context():
            initialize_session_history('test_history', 'sub_key')
            
            assert 'test_history' in session
            assert isinstance(session['test_history'], dict)
            assert session['test_history']['sub_key'] == []
    
    def test_initialize_session_history_既存(self, app_context):
        """既存セッション履歴がある場合の処理を確認"""
        with app_context.test_request_context():
            session['test_history'] = [{"existing": "data"}]
            
            initialize_session_history('test_history')
            
            # 既存データが保持される
            assert session['test_history'] == [{"existing": "data"}]
    
    def test_session_data_integrity(self, app_context):
        """セッションデータの整合性を確認"""
        with app_context.test_request_context():
            # セッションにデータを設定
            session['test_data'] = {"key": "value"}
            
            # データが正しく保存されることを確認
            assert session.get('test_data') == {"key": "value"}
    
    def test_session_modification(self, app_context):
        """セッションデータの変更を確認"""
        with app_context.test_request_context():
            # 初期データを設定
            session['counter'] = 0
            
            # データを変更
            session['counter'] += 1
            
            # 変更が反映されることを確認
            assert session['counter'] == 1


class TestAppHelperUtils:
    """アプリケーションヘルパーユーティリティのテスト"""
    
    def test_session_has_data_check(self, app_context):
        """セッションにデータが存在するかの確認"""
        with app_context.test_request_context():
            # データがない状態
            assert 'non_existent_key' not in session
            
            # データを追加
            session['existing_key'] = "value"
            assert 'existing_key' in session
    
    def test_session_data_types(self, app_context):
        """セッションに様々なデータ型を保存できることを確認"""
        with app_context.test_request_context():
            # 様々なデータ型をテスト
            session['string'] = "text"
            session['number'] = 123
            session['list'] = [1, 2, 3]
            session['dict'] = {"nested": "value"}
            session['boolean'] = True
            
            # 型が保持されることを確認
            assert isinstance(session['string'], str)
            assert isinstance(session['number'], int)
            assert isinstance(session['list'], list)
            assert isinstance(session['dict'], dict)
            assert isinstance(session['boolean'], bool)


# テスト用のフィクスチャ
@pytest.fixture
def app_context():
    """アプリケーションコンテキストのフィクスチャ"""
    from app import app
    return app