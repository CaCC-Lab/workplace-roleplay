"""
SessionServiceのユニットテスト
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from services.session_service import SessionService
from flask import Flask, session


class TestSessionService:
    """SessionServiceのテストクラス"""
    
    @pytest.fixture
    def app(self):
        """Flaskアプリケーションの作成"""
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Flaskテストクライアントの作成"""
        return app.test_client()
    
    def test_initialize_session_history_新規作成(self, app):
        """新規セッション履歴の初期化"""
        with app.test_request_context():
            SessionService.initialize_session_history('test_history')
            
            assert 'test_history' in session
            assert session['test_history'] == []
    
    def test_initialize_session_history_サブキー付き(self, app):
        """サブキー付きセッション履歴の初期化"""
        with app.test_request_context():
            SessionService.initialize_session_history('test_history', 'sub_key')
            
            assert 'test_history' in session
            assert isinstance(session['test_history'], dict)
            assert 'sub_key' in session['test_history']
            assert session['test_history']['sub_key'] == []
    
    def test_add_to_session_history_基本追加(self, app):
        """セッション履歴への基本的な追加"""
        with app.test_request_context():
            SessionService.initialize_session_history('test_history')
            
            entry = {'user': 'test message', 'timestamp': '2025-07-31'}
            SessionService.add_to_session_history('test_history', entry)
            
            assert len(session['test_history']) == 1
            assert session['test_history'][0] == entry
    
    def test_add_to_session_history_最大エントリ制限(self, app):
        """最大エントリ数の制限が機能することを確認"""
        with app.test_request_context():
            # 50個のエントリを持つ履歴を作成
            session['test_history'] = [{'id': i} for i in range(50)]
            
            # 51個目を追加
            new_entry = {'id': 50}
            SessionService.add_to_session_history('test_history', new_entry, max_entries=50)
            
            # 最大50個が維持され、古いものが削除されることを確認
            assert len(session['test_history']) == 50
            assert session['test_history'][-1] == new_entry
            assert session['test_history'][0]['id'] == 1  # 最初のエントリが削除されている
    
    def test_get_session_history_存在する履歴(self, app):
        """存在する履歴の取得"""
        with app.test_request_context():
            expected_history = [{'user': 'test', 'assistant': 'response'}]
            session['test_history'] = expected_history
            
            result = SessionService.get_session_history('test_history')
            
            assert result == expected_history
    
    def test_get_session_history_存在しない履歴(self, app):
        """存在しない履歴の取得時は空リストを返す"""
        with app.test_request_context():
            result = SessionService.get_session_history('non_existent')
            assert result == []
    
    def test_get_session_history_サブキー付き(self, app):
        """サブキー付き履歴の取得"""
        with app.test_request_context():
            session['test_history'] = {
                'sub1': [{'data': 'test1'}],
                'sub2': [{'data': 'test2'}]
            }
            
            result = SessionService.get_session_history('test_history', 'sub1')
            assert result == [{'data': 'test1'}]
    
    def test_clear_session_history_通常クリア(self, app):
        """履歴の通常クリア"""
        with app.test_request_context():
            session['test_history'] = [1, 2, 3]
            
            SessionService.clear_session_history('test_history')
            
            assert session['test_history'] == []
    
    def test_clear_session_history_サブキー付きクリア(self, app):
        """サブキー付き履歴のクリア"""
        with app.test_request_context():
            session['test_history'] = {'sub1': [1, 2, 3], 'sub2': [4, 5, 6]}
            
            SessionService.clear_session_history('test_history', 'sub1')
            
            # sub1のみがクリアされることを確認
            assert session['test_history']['sub1'] == []
            assert session['test_history']['sub2'] == [4, 5, 6]
    
    def test_set_session_start_time_基本設定(self, app):
        """開始時刻の基本設定"""
        with app.test_request_context():
            with patch('services.session_service.datetime') as mock_datetime:
                mock_datetime.now.return_value.isoformat.return_value = '2025-07-31T10:00:00'
                
                SessionService.set_session_start_time('chat')
                
                assert session['chat_start_time'] == '2025-07-31T10:00:00'
    
    def test_get_session_start_time_存在する場合(self, app):
        """存在する開始時刻の取得"""
        with app.test_request_context():
            session['chat_start_time'] = '2025-07-31T10:00:00'
            
            result = SessionService.get_session_start_time('chat')
            assert result == '2025-07-31T10:00:00'
    
    def test_get_session_data_デフォルト値(self, app):
        """セッションデータ取得時のデフォルト値"""
        with app.test_request_context():
            result = SessionService.get_session_data('non_existent', 'default_value')
            assert result == 'default_value'
    
    def test_set_session_data_基本設定(self, app):
        """セッションデータの基本設定"""
        with app.test_request_context():
            SessionService.set_session_data('test_key', 'test_value')
            assert session['test_key'] == 'test_value'
    
    def test_remove_session_data_存在するキー(self, app):
        """存在するキーの削除"""
        with app.test_request_context():
            session['test_key'] = 'test_value'
            
            SessionService.remove_session_data('test_key')
            assert 'test_key' not in session
    
    def test_remove_session_data_存在しないキー(self, app):
        """存在しないキーの削除は何もしない"""
        with app.test_request_context():
            # エラーが発生しないことを確認
            SessionService.remove_session_data('non_existent')