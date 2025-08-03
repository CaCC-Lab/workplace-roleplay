"""
SessionServiceのユニットテスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.session_service import SessionService
from utils.constants import SessionKeys, HistoryFormat, DEFAULT_CHAT_MODEL, DEFAULT_VOICE


class TestSessionService:
    """SessionServiceのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        # Flaskセッションのモック
        self.mock_session = {}
        self.patcher = patch('services.session_service.session', self.mock_session)
        self.patcher.start()
        
        # サービスインスタンス
        self.service = SessionService()
    
    def teardown_method(self):
        """各テストメソッドの後に実行"""
        self.patcher.stop()
    
    def test_initialization(self):
        """サービスの初期化テスト"""
        # 初期化確認
        assert self.service is not None
        assert self.service.KEYS == SessionKeys
    
    @patch('services.session_service.initialize_session_history')
    def test_initialize_session(self, mock_init_history):
        """セッション初期化のテスト"""
        self.service.initialize_session()
        # 4つの履歴が初期化される
        assert mock_init_history.call_count == 4
    
    def test_get_user_id(self):
        """ユーザーID取得のテスト"""
        # 初回取得（生成される）
        user_id1 = self.service.get_user_id()
        assert user_id1 is not None
        assert isinstance(user_id1, str)
        assert len(user_id1) > 0
        
        # 2回目取得（同じIDが返る）
        user_id2 = self.service.get_user_id()
        assert user_id1 == user_id2
    
    def test_model_management(self):
        """モデル管理のテスト"""
        # デフォルトモデルの取得
        model = self.service.get_current_model()
        assert model == DEFAULT_CHAT_MODEL
        
        # モデルの設定
        self.service.set_current_model("gemini-1.5-pro")
        assert self.service.get_current_model() == "gemini-1.5-pro"
    
    def test_voice_management(self):
        """音声管理のテスト"""
        # デフォルト音声の取得
        voice = self.service.get_current_voice()
        assert voice == DEFAULT_VOICE
        
        # 音声の設定
        self.service.set_current_voice("nova")
        assert self.service.get_current_voice() == "nova"
    
    def test_conversation_id_management(self):
        """会話ID管理のテスト"""
        # 初回取得
        conv_id1 = self.service.get_conversation_id()
        assert conv_id1 is not None
        
        # リセット
        conv_id2 = self.service.reset_conversation_id()
        assert conv_id2 != conv_id1
        assert self.service.get_conversation_id() == conv_id2
    
    @patch('services.session_service.add_to_session_history')
    def test_add_chat_message(self, mock_add_history):
        """チャットメッセージ追加のテスト"""
        self.service.add_chat_message("こんにちは", "こんにちは！お元気ですか？")
        
        # 呼び出し確認
        mock_add_history.assert_called_once()
        call_args = mock_add_history.call_args[0]
        assert call_args[0] == SessionKeys.CHAT_HISTORY
        assert call_args[1]['human'] == "こんにちは"
        assert call_args[1]['ai'] == "こんにちは！お元気ですか？"
        assert 'timestamp' in call_args[1]
    
    @patch('services.session_service.get_conversation_memory')
    def test_get_chat_history(self, mock_get_memory):
        """チャット履歴取得のテスト"""
        mock_get_memory.return_value = [
            {'human': 'test1', 'ai': 'response1'},
            {'human': 'test2', 'ai': 'response2'}
        ]
        
        history = self.service.get_chat_history()
        assert len(history) == 2
        mock_get_memory.assert_called_once_with('chat', max_messages=50)
    
    @patch('services.session_service.clear_session_history')
    def test_clear_chat_history(self, mock_clear_history):
        """チャット履歴クリアのテスト"""
        self.service.clear_chat_history()
        mock_clear_history.assert_called_once_with(SessionKeys.CHAT_HISTORY)
    
    @patch('services.session_service.add_to_session_history')
    def test_add_scenario_message(self, mock_add_history):
        """シナリオメッセージ追加のテスト"""
        self.service.add_scenario_message(
            "scenario-001",
            "提案があります",
            "はい、お聞きします",
            "部下"
        )
        
        # 呼び出し確認
        mock_add_history.assert_called_once()
        call_args = mock_add_history.call_args
        assert call_args[0][0] == SessionKeys.SCENARIO_HISTORY
        assert call_args[0][1]['role'] == "部下"
        assert call_args[0][2] == "scenario-001"  # sub_key
    
    def test_scenario_id_management(self):
        """シナリオID管理のテスト"""
        # 初期状態
        assert self.service.get_current_scenario_id() is None
        
        # 設定
        self.service.set_current_scenario_id("scenario-001")
        assert self.service.get_current_scenario_id() == "scenario-001"
        
        # クリア
        self.service.set_current_scenario_id(None)
        assert self.service.get_current_scenario_id() is None
    
    def test_clear_scenario_history_specific(self):
        """特定シナリオ履歴クリアのテスト"""
        # シナリオ履歴を設定
        self.mock_session[SessionKeys.SCENARIO_HISTORY] = {
            'scenario-001': [{'human': 'test1'}],
            'scenario-002': [{'human': 'test2'}]
        }
        
        # 特定シナリオのみクリア
        self.service.clear_scenario_history('scenario-001')
        assert self.mock_session[SessionKeys.SCENARIO_HISTORY]['scenario-001'] == []
        assert len(self.mock_session[SessionKeys.SCENARIO_HISTORY]['scenario-002']) == 1
    
    @patch('services.session_service.add_to_session_history')
    def test_add_watch_message(self, mock_add_history):
        """観戦モードメッセージ追加のテスト"""
        self.service.add_watch_message(
            "モデル1のメッセージ",
            "モデル2のメッセージ",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        )
        
        # 呼び出し確認
        mock_add_history.assert_called_once()
        call_args = mock_add_history.call_args[0]
        entry = call_args[1]
        assert entry['model1']['name'] == "gemini-1.5-flash"
        assert entry['model1']['message'] == "モデル1のメッセージ"
        assert entry['model2']['name'] == "gemini-1.5-pro"
        assert entry['model2']['message'] == "モデル2のメッセージ"
    
    def test_watch_models_management(self):
        """観戦モード用モデル管理のテスト"""
        # デフォルト値
        models = self.service.get_watch_models()
        assert models['model1'] == DEFAULT_CHAT_MODEL
        assert models['model2'] == DEFAULT_CHAT_MODEL
        
        # 設定
        self.service.set_watch_models("gemini-1.5-flash", "gemini-1.5-pro")
        models = self.service.get_watch_models()
        assert models['model1'] == "gemini-1.5-flash"
        assert models['model2'] == "gemini-1.5-pro"
    
    def test_watch_topic_management(self):
        """観戦モードトピック管理のテスト"""
        # 初期状態
        assert self.service.get_watch_topic() is None
        
        # 設定
        self.service.set_watch_topic("職場での雑談")
        assert self.service.get_watch_topic() == "職場での雑談"
        
        # クリア
        self.service.set_watch_topic(None)
        assert self.service.get_watch_topic() is None
    
    def test_add_learning_record(self):
        """学習記録追加のテスト"""
        # ユーザーIDを事前設定
        self.mock_session['user_id'] = "test-user-id"
        self.mock_session['conversation_id'] = "test-conv-id"
        
        # 学習記録を追加
        self.service.add_learning_record(
            activity_type="scenario",
            scenario_id="scenario-001",
            feedback={'score': 85},
            duration_seconds=300
        )
        
        # 確認
        assert SessionKeys.LEARNING_HISTORY in self.mock_session
        records = self.mock_session[SessionKeys.LEARNING_HISTORY]
        assert len(records) == 1
        
        record = records[0]
        assert record['activity_type'] == "scenario"
        assert record['scenario_id'] == "scenario-001"
        assert record['feedback'] == {'score': 85}
        assert record['duration_seconds'] == 300
        assert record['user_id'] == "test-user-id"
    
    def test_learning_history_limit(self):
        """学習履歴の件数制限テスト"""
        # 101件の記録を追加
        self.mock_session[SessionKeys.LEARNING_HISTORY] = []
        for i in range(101):
            self.service.add_learning_record(f"chat")
        
        # 100件に制限されることを確認
        history = self.mock_session[SessionKeys.LEARNING_HISTORY]
        assert len(history) == 100
    
    def test_get_learning_stats(self):
        """学習統計取得のテスト"""
        # テストデータ
        self.mock_session[SessionKeys.LEARNING_HISTORY] = [
            {'activity_type': 'chat', 'duration_seconds': 120},
            {'activity_type': 'scenario', 'scenario_id': 's1', 'duration_seconds': 300},
            {'activity_type': 'scenario', 'scenario_id': 's2', 'duration_seconds': 240},
            {'activity_type': 'scenario', 'scenario_id': 's1', 'duration_seconds': 180},
            {'activity_type': 'watch', 'duration_seconds': 60}
        ]
        
        stats = self.service.get_learning_stats()
        
        assert stats['total_sessions'] == 5
        assert stats['chat_sessions'] == 1
        assert stats['scenario_sessions'] == 3
        assert stats['watch_sessions'] == 1
        assert stats['scenarios_completed'] == 2  # s1とs2
        assert stats['total_duration_seconds'] == 900
        assert stats['total_duration_minutes'] == 15.0
    
    def test_export_session_data(self):
        """セッションデータエクスポートのテスト"""
        # テストデータを設定
        self.mock_session['user_id'] = "test-user"
        self.mock_session['conversation_id'] = "test-conv"
        self.mock_session[SessionKeys.CURRENT_MODEL] = "gemini-1.5-pro"
        self.mock_session[SessionKeys.CHAT_HISTORY] = []
        self.mock_session[SessionKeys.SCENARIO_HISTORY] = {}
        self.mock_session[SessionKeys.WATCH_HISTORY] = []
        self.mock_session[SessionKeys.LEARNING_HISTORY] = []
        
        # get_chat_historyをモック
        with patch.object(self.service, 'get_chat_history', return_value=[]):
            data = self.service.export_session_data()
        
        assert data['user_id'] == "test-user"
        assert data['conversation_id'] == "test-conv"
        assert data['current_model'] == "gemini-1.5-pro"
        assert 'learning_stats' in data
    
    def test_clear_all_session_data(self):
        """全セッションデータクリアのテスト"""
        # データを設定
        self.mock_session['user_id'] = "test-user"
        self.mock_session['test_key'] = "test_value"
        self.mock_session[SessionKeys.CHAT_HISTORY] = [{'test': 'data'}]
        
        # クリア
        with patch('services.session_service.SessionService.initialize_session'):
            self.service.clear_all_session_data()
        
        # ユーザーIDは保持される
        assert self.mock_session['user_id'] == "test-user"
        # その他はクリアされる
        assert 'test_key' not in self.mock_session
        assert SessionKeys.CHAT_HISTORY not in self.mock_session
    
    def test_generic_session_operations(self):
        """汎用セッション操作のテスト"""
        # 値の設定
        self.service.set_session_value("custom_key", "custom_value")
        assert self.mock_session["custom_key"] == "custom_value"
        
        # 値の取得
        value = self.service.get_session_value("custom_key")
        assert value == "custom_value"
        
        # デフォルト値付き取得
        value = self.service.get_session_value("nonexistent", "default")
        assert value == "default"
        
        # 値の削除
        self.service.delete_session_value("custom_key")
        assert "custom_key" not in self.mock_session