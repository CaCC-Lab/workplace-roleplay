"""
ChatServiceのユニットテスト
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import json
from typing import List, Dict, Any
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.chat_service import ChatService
from services.llm_service import LLMService
from services.session_service import SessionService
from utils.constants import MAX_MESSAGE_LENGTH, EMOTION_VOICE_MAPPING


class TestChatService:
    """ChatServiceのテストクラス"""
    
    def setup_method(self):
        """各テストメソッドの前に実行"""
        # モックサービス
        self.mock_llm_service = Mock(spec=LLMService)
        self.mock_session_service = Mock(spec=SessionService)
        
        # ChatServiceインスタンス
        self.service = ChatService(
            llm_service=self.mock_llm_service,
            session_service=self.mock_session_service
        )
        
        # デフォルトのモック設定
        self.mock_session_service.get_current_model.return_value = "gemini-1.5-flash"
        self.mock_session_service.get_current_voice.return_value = "kore"
        self.mock_session_service.get_chat_history.return_value = []
    
    @pytest.mark.asyncio
    async def test_process_chat_message_success(self):
        """雑談メッセージ処理の成功テスト"""
        # モック設定
        async def mock_stream_response(*args, **kwargs):
            chunks = ["こんにちは", "！", "お元気", "ですか", "？"]
            for chunk in chunks:
                yield chunk
        
        self.mock_llm_service.stream_chat_response = mock_stream_response
        
        # メッセージを処理
        response_chunks = []
        async for chunk in self.service.process_chat_message("こんにちは"):
            response_chunks.append(chunk)
        
        # 検証
        assert response_chunks == ["こんにちは", "！", "お元気", "ですか", "？"]
        self.mock_session_service.add_chat_message.assert_called_once_with(
            "こんにちは",
            "こんにちは！お元気ですか？"
        )
    
    @pytest.mark.asyncio
    async def test_process_chat_message_invalid_message(self):
        """無効なメッセージの処理テスト"""
        # 空のメッセージ
        response_chunks = []
        async for chunk in self.service.process_chat_message(""):
            response_chunks.append(chunk)
        
        assert response_chunks == ["メッセージが無効です。"]
        
        # 長すぎるメッセージ
        long_message = "a" * (MAX_MESSAGE_LENGTH + 1)
        response_chunks = []
        async for chunk in self.service.process_chat_message(long_message):
            response_chunks.append(chunk)
        
        assert response_chunks == ["メッセージが無効です。"]
    
    @pytest.mark.asyncio
    async def test_process_scenario_message_success(self):
        """シナリオメッセージ処理の成功テスト"""
        # シナリオデータのモック
        mock_scenario = {
            'id': 'scenario-001',
            'title': 'テストシナリオ',
            'situation': 'テスト状況',
            'character': {
                'name': '田中さん',
                'role': '上司',
                'personality': '優しくて理解がある'
            }
        }
        
        with patch('services.chat_service.get_scenario_by_id', return_value=mock_scenario):
            # モック設定
            async def mock_stream_response(*args, **kwargs):
                chunks = ["了解", "しました"]
                for chunk in chunks:
                    yield chunk
            
            self.mock_llm_service.stream_chat_response = mock_stream_response
            self.mock_session_service.get_scenario_history.return_value = []
            
            # メッセージを処理
            response_chunks = []
            async for chunk in self.service.process_scenario_message("scenario-001", "報告があります"):
                response_chunks.append(chunk)
            
            # 検証
            assert response_chunks == ["了解", "しました"]
            self.mock_session_service.set_current_scenario_id.assert_called_once_with("scenario-001")
            self.mock_session_service.add_scenario_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_scenario_message_invalid_scenario(self):
        """無効なシナリオIDの処理テスト"""
        with patch('services.chat_service.get_scenario_by_id', return_value=None):
            response_chunks = []
            async for chunk in self.service.process_scenario_message("invalid-id", "テスト"):
                response_chunks.append(chunk)
            
            assert response_chunks == ["シナリオが見つかりません。"]
    
    @pytest.mark.asyncio
    async def test_start_watch_conversation(self):
        """観戦モード会話開始のテスト"""
        # モック設定
        self.mock_session_service.get_watch_models.return_value = {
            'model1': 'gemini-1.5-flash',
            'model2': 'gemini-1.5-pro'
        }
        
        async def mock_stream_response(*args, **kwargs):
            chunks = ["今日は", "いい天気", "ですね"]
            for chunk in chunks:
                yield chunk
        
        self.mock_llm_service.stream_chat_response = mock_stream_response
        
        # 会話を開始
        response_chunks = []
        async for chunk in self.service.start_watch_conversation("天気について"):
            response_chunks.append(chunk)
        
        # 検証
        assert len(response_chunks) == 1
        response_data = json.loads(response_chunks[0])
        assert response_data['speaker'] == 'model1'
        assert response_data['message'] == "今日はいい天気ですね"
        
        self.mock_session_service.set_watch_models.assert_called_once()
        self.mock_session_service.set_watch_topic.assert_called_once_with("天気について")
        self.mock_session_service.clear_watch_history.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_continue_watch_conversation(self):
        """観戦モード会話継続のテスト"""
        # モック設定
        self.mock_session_service.get_watch_models.return_value = {
            'model1': 'gemini-1.5-flash',
            'model2': 'gemini-1.5-pro'
        }
        self.mock_session_service.get_watch_topic.return_value = "天気について"
        self.mock_session_service.get_watch_history.return_value = [
            {
                'model1': {'message': '今日はいい天気ですね', 'name': 'gemini-1.5-flash'},
                'model2': {'message': '', 'name': 'gemini-1.5-pro'}
            }
        ]
        
        async def mock_stream_response(*args, **kwargs):
            chunks = ["そうですね", "、", "散歩日和です"]
            for chunk in chunks:
                yield chunk
        
        self.mock_llm_service.stream_chat_response = mock_stream_response
        
        # 会話を継続
        response_chunks = []
        async for chunk in self.service.continue_watch_conversation():
            response_chunks.append(chunk)
        
        # 検証
        assert len(response_chunks) == 1
        response_data = json.loads(response_chunks[0])
        assert response_data['speaker'] == 'model2'
        assert response_data['message'] == "そうですね、散歩日和です"
    
    @pytest.mark.asyncio
    async def test_generate_chat_feedback(self):
        """雑談フィードバック生成のテスト"""
        # モック設定
        self.mock_session_service.get_chat_history.return_value = [
            {'human': 'こんにちは', 'ai': 'こんにちは！元気ですか？'},
            {'human': '元気です。今日は忙しいです', 'ai': 'お疲れ様です。'}
        ]
        
        self.mock_llm_service.invoke_sync.return_value = "良い雑談ができています。相手への配慮が感じられます。"
        
        # フィードバックを生成
        feedback = await self.service.generate_chat_feedback()
        
        # 検証
        assert "良い雑談ができています" in feedback
        self.mock_llm_service.invoke_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_chat_feedback_no_history(self):
        """履歴がない場合のフィードバック生成テスト"""
        # モック設定
        self.mock_session_service.get_chat_history.return_value = []
        
        # フィードバックを生成
        feedback = await self.service.generate_chat_feedback()
        
        # 検証
        assert feedback == "まだ会話がありません。雑談を始めてみましょう！"
    
    @pytest.mark.asyncio
    async def test_generate_scenario_feedback(self):
        """シナリオフィードバック生成のテスト"""
        # シナリオデータのモック
        mock_scenario = {
            'id': 'scenario-001',
            'title': 'テストシナリオ',
            'situation': 'テスト状況',
            'character': {
                'name': '田中さん',
                'role': '上司'
            },
            'feedback_points': ['明確な報告', '適切な敬語']
        }
        
        with patch('services.chat_service.get_scenario_by_id', return_value=mock_scenario):
            # モック設定
            self.mock_session_service.get_scenario_history.return_value = [
                {'human': '報告があります', 'ai': 'はい、聞きます'}
            ]
            
            self.mock_llm_service.invoke_sync.return_value = "適切な報告ができています。"
            
            # フィードバックを生成
            feedback = await self.service.generate_scenario_feedback("scenario-001")
            
            # 検証
            assert "適切な報告ができています" in feedback
            self.mock_session_service.add_learning_record.assert_called_once()
    
    def test_get_recommended_voice(self):
        """推奨音声取得のテスト"""
        # 感情に基づく音声
        voice = self.service.get_recommended_voice("happy")
        assert voice == EMOTION_VOICE_MAPPING["happy"]
        
        # デフォルト音声
        voice = self.service.get_recommended_voice()
        assert voice == "kore"
        
        # 未定義の感情
        voice = self.service.get_recommended_voice("unknown")
        assert voice == "kore"
    
    def test_validate_message(self):
        """メッセージ検証のテスト"""
        # 正常なメッセージ
        valid, error = self.service.validate_message("こんにちは")
        assert valid is True
        assert error is None
        
        # 空のメッセージ
        valid, error = self.service.validate_message("")
        assert valid is False
        assert error == "メッセージを入力してください。"
        
        # 長すぎるメッセージ
        long_message = "a" * (MAX_MESSAGE_LENGTH + 1)
        valid, error = self.service.validate_message(long_message)
        assert valid is False
        assert f"{MAX_MESSAGE_LENGTH}文字以内" in error
        
        # 不適切な内容
        valid, error = self.service.validate_message("ばかやろう")
        assert valid is False
        assert "不適切な表現" in error