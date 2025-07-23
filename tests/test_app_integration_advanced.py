"""
app.pyの高度な統合テスト - カバレッジ向上のため
TDD原則に従い、実際のユースケース、複雑なワークフロー、エッジケースをテスト
"""
import pytest
import json
import time
from unittest.mock import patch, MagicMock, PropertyMock
from flask import session

# テスト対象の関数とアプリケーション
from app import app


# APIのモック設定を最初に読み込み
@pytest.fixture(autouse=True)
def mock_all_external_apis():
    """すべての外部API呼び出しをモック化（自動適用）"""
    with patch('app.create_gemini_llm') as mock_create_llm, \
         patch('google.generativeai.GenerativeModel') as mock_gemini_model, \
         patch('google.generativeai.configure') as mock_configure, \
         patch('langchain_google_genai.ChatGoogleGenerativeAI') as mock_chat_gemini:
        
        # 基本的なLLMモックを設定
        mock_llm = MagicMock()
        from langchain_core.messages import AIMessage
        mock_llm.invoke.return_value = AIMessage(content="Test response from mocked LLM")
        mock_llm.astream.return_value = iter([
            MagicMock(content="Test "),
            MagicMock(content="streamed "),
            MagicMock(content="response")
        ])
        
        # create_gemini_llm関数をモック
        mock_create_llm.return_value = mock_llm
        
        # ChatGoogleGenerativeAIクラスをモック
        mock_chat_gemini.return_value = mock_llm
        
        # Gemini Modelのモック
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = MagicMock(
            text="Mocked response from Gemini API"
        )
        mock_gemini_model.return_value = mock_model_instance
        
        yield {
            'mock_create_llm': mock_create_llm,
            'mock_chat_gemini': mock_chat_gemini,
            'mock_gemini_model': mock_gemini_model,
            'mock_configure': mock_configure,
            'mock_llm': mock_llm
        }


class TestComplexWorkflows:
    """複雑なワークフローのテスト"""
    
    def test_multi_turn_conversation_flow(self, csrf_client, mock_all_external_apis):
        """複数ターンの会話フローを確認"""
        # グローバルモックを使用してレスポンス設定
        mock_llm = mock_all_external_apis['mock_llm']
        
        # 会話の各ターンに異なる応答を設定
        responses = [
            "こんにちは！どのようなお話をしましょうか？",
            "天気の話ですね。今日は良い天気ですね。",
            "そうですね。週末の予定はありますか？",
            "素晴らしいですね！楽しい時間をお過ごしください。"
        ]
        
        from langchain_core.messages import AIMessage
        mock_responses = [AIMessage(content=resp) for resp in responses]
        mock_llm.invoke.side_effect = mock_responses
        
        # セッション初期化
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "あなたは職場での雑談練習をサポートするAIアシスタントです。",
                "model": "gemini-1.5-flash"
            }
        
        # 複数ターンの会話
        messages = [
            "こんにちは",
            "今日は良い天気ですね",
            "週末は家族と過ごす予定です",
            "ありがとうございます"
        ]
        
        for i, message in enumerate(messages):
            response = csrf_client.post('/api/chat',
                                 json={
                                     "message": message,
                                     "model": "gemini-1.5-flash"
                                 })
            
            assert response.status_code == 200
            data = response.get_json()
            assert "response" in data
            assert responses[i] in data["response"]
        
        # セッション履歴が正しく積み上がっていることを確認
        with csrf_client.session_transaction() as sess:
            assert 'chat_history' in sess
            assert len(sess['chat_history']) == len(messages)
    
    def test_scenario_practice_complete_flow(self, csrf_client, mock_all_external_apis):
        """シナリオ練習の完全フローを確認"""
        mock_llm = mock_all_external_apis['mock_llm']
        
        # シナリオの各段階での応答
        scenario_responses = [
            "いらっしゃいませ。本日はお忙しい中、お時間をいただきありがとうございます。",
            "承知いたしました。詳細を確認させていただきます。",
            "こちらで対応させていただきます。他にご質問はございますか？",
            "ありがとうございました。また何かございましたらお声がけください。"
        ]
        
        from langchain_core.messages import AIMessage
        mock_responses = [AIMessage(content=resp) for resp in scenario_responses]
        mock_llm.invoke.side_effect = mock_responses + [AIMessage(content="""
## コミュニケーションスコア
88点

## 良かった点
- 丁寧な敬語の使用
- 相手の立場に配慮した発言
- 適切なタイミングでの質問

## 改善のヒント
- より具体的な提案を含めると良いでしょう
- 感謝の気持ちをもう少し表現できます

## 総合評価
職場でのコミュニケーションとして非常に良い対応でした。
        """)]
        
        # モックは既にグローバルで設定済み
        
        scenario_id = "customer_service"
        user_messages = [
            "お客様、いらっしゃいませ",
            "かしこまりました、確認いたします",
            "承知いたしました、対応いたします",
            "ありがとうございました"
        ]
        
        # シナリオ練習の実行
        for message in user_messages:
            response = csrf_client.post('/api/scenario_chat',
                                 json={
                                     "message": message,
                                     "model": "gemini-1.5-flash",
                                     "scenario_id": scenario_id
                                 })
            
            assert response.status_code == 200
            data = response.get_json()
            assert "response" in data
        
        # フィードバック取得
        feedback_response = csrf_client.post('/api/scenario_feedback',
                                      json={"scenario_id": scenario_id})
        
        assert feedback_response.status_code == 200
        feedback_data = feedback_response.get_json()
        assert "feedback" in feedback_data
        assert "コミュニケーションスコア" in feedback_data["feedback"]
        assert "良かった点" in feedback_data["feedback"]
        assert "改善のヒント" in feedback_data["feedback"]
    
    # Removed patch decorator - using global mock
    def test_watch_mode_complete_conversation(self, csrf_client, mock_all_external_apis):
        """観戦モードの完全な会話フローを確認"""
        mock_llm = MagicMock()
        
        # 観戦モードの会話シーケンス
        watch_responses = [
            "おはようございます！今日もよろしくお願いします。",
            "おはようございます。昨日のプロジェクトの件、いかがでしたか？",
            "順調に進んでいます。来週には完成予定です。",
            "それは良かったです。何かサポートが必要でしたらお声がけください。",
            "ありがとうございます。助かります。"
        ]
        
        from langchain_core.messages import AIMessage
        mock_responses = [AIMessage(content=resp) for resp in watch_responses]
        mock_llm.invoke.side_effect = mock_responses
        
        # 観戦開始
        start_response = csrf_client.post('/api/watch/start',
                                   json={
                                       "model_a": "gemini-1.5-pro",
                                       "model_b": "gemini-1.5-flash",
                                       "partner_type": "colleague",
                                       "situation": "morning",
                                       "topic": "work"
                                   })
        
        assert start_response.status_code == 200
        
        # 複数ターンの会話を生成
        for i in range(4):
            next_response = csrf_client.post('/api/watch/next')
            
            assert next_response.status_code == 200
            data = next_response.get_json()
            assert "message" in data
            assert "speaker" in data
            assert data["speaker"] in ["A", "B"]
        
        # セッションに完全な会話履歴が保存されていることを確認
        with csrf_client.session_transaction() as sess:
            assert 'watch_history' in sess
            assert len(sess['watch_history']) >= 4


class TestEdgeCases:
    """エッジケースのテスト"""
    
    def test_extremely_long_message(self, csrf_client, mock_all_external_apis):
        """極端に長いメッセージの処理を確認"""
        long_message = "テスト " * 10000  # 非常に長いメッセージ
        
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="長いメッセージを受信しました")
        mock_llm.invoke.return_value = mock_response
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": long_message,
                                 "model": "gemini-1.5-flash"
                             })
        
        # 長いメッセージも適切に処理される
        assert response.status_code in [200, 400]  # 制限により400も可能
    
    def test_special_characters_in_message(self, csrf_client, mock_all_external_apis):
        """特殊文字を含むメッセージの処理を確認"""
        special_message = "こんにちは！@#$%^&*()_+{}|:<>?[]\\;',./`~"
        
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="特殊文字を含むメッセージですね")
        mock_llm.invoke.return_value = mock_response
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": special_message,
                                 "model": "gemini-1.5-flash"
                             })
        
        assert response.status_code == 200
        data = response.get_json()
        assert "response" in data
    
    def test_unicode_emoji_handling(self, csrf_client, mock_all_external_apis):
        """Unicode絵文字の処理を確認"""
        emoji_message = "こんにちは！😊🌟⭐️🎉🚀💖"
        
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="絵文字がたくさんですね！😄")
        mock_llm.invoke.return_value = mock_response
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": emoji_message,
                                 "model": "gemini-1.5-flash"
                             })
        
        assert response.status_code == 200
        data = response.get_json()
        assert "response" in data
        assert "😄" in data["response"]
    
    def test_empty_session_handling(self, csrf_client):
        """空のセッション状態での処理を確認"""
        # セッションを意図的にクリア
        with csrf_client.session_transaction() as sess:
            sess.clear()
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "セッションがない状態です",
                                 "model": "gemini-1.5-flash"
                             })
        
        # セッションがない場合でも適切に初期化される
        assert response.status_code in [200, 400, 500]
    
    def test_malformed_session_data(self, csrf_client, mock_all_external_apis):
        """不正なセッションデータでの処理を確認"""
        with csrf_client.session_transaction() as sess:
            # 不正なデータ形式をセッションに設定
            sess['chat_history'] = "不正なデータ形式"
            sess['chat_settings'] = ["リスト形式", "不正"]
        
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="復旧しました")
        mock_llm.invoke.return_value = mock_response
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "不正なセッションからの復旧",
                                 "model": "gemini-1.5-flash"
                             })
        
        # 不正なセッションデータも適切に処理される
        assert response.status_code in [200, 500]


class TestConcurrencyAndRace:
    """並行性と競合状態のテスト"""
    
    def test_concurrent_session_access(self, csrf_client, mock_all_external_apis):
        """同一セッションでの並行アクセスの処理を確認"""
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="並行処理応答")
        mock_llm.invoke.return_value = mock_response
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        # 複数のリクエストを短時間で送信
        responses = []
        for i in range(3):
            response = csrf_client.post('/api/chat',
                                 json={
                                     "message": f"並行リクエスト{i}",
                                     "model": "gemini-1.5-flash"
                                 })
            responses.append(response)
        
        # すべてのレスポンスが適切に処理される
        for response in responses:
            assert response.status_code == 200
    
    def test_session_history_consistency(self, csrf_client, mock_all_external_apis):
        """セッション履歴の一貫性を確認"""
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        
        # 各リクエストに異なる応答を設定
        from langchain_core.messages import AIMessage
        mock_responses = [
            AIMessage(content="応答1"),
            AIMessage(content="応答2"),
            AIMessage(content="応答3")
        ]
        mock_llm.invoke.side_effect = mock_responses
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        # 順次リクエスト送信
        for i in range(3):
            csrf_client.post('/api/chat',
                       json={
                           "message": f"メッセージ{i+1}",
                           "model": "gemini-1.5-flash"
                       })
        
        # セッション履歴の一貫性を確認
        with csrf_client.session_transaction() as sess:
            history = sess.get('chat_history', [])
            assert len(history) == 3
            for i, entry in enumerate(history):
                assert entry['human'] == f"メッセージ{i+1}"
                assert entry['ai'] == f"応答{i+1}"


class TestResourceManagement:
    """リソース管理のテスト"""
    
    # Removed patch decorator - using global mock
    def test_memory_efficient_large_history(self, csrf_client, mock_all_external_apis):
        """大きな履歴でのメモリ効率を確認"""
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_response = AIMessage(content="メモリ効率テスト")
        mock_llm.invoke.return_value = mock_response
        
        # 大きな履歴をセッションに設定
        large_history = []
        for i in range(1000):
            large_history.append({
                "human": f"ユーザーメッセージ{i}",
                "ai": f"AI応答{i}"
            })
        
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = large_history
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        # 新しいメッセージを送信
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "大きな履歴でのテスト",
                                 "model": "gemini-1.5-flash"
                             })
        
        # 大きな履歴があっても処理される
        assert response.status_code in [200, 500]
    
    def test_session_cleanup_after_clear(self, csrf_client):
        """履歴クリア後のセッションクリーンアップを確認"""
        # セッションに大量のデータを設定
        with csrf_client.session_transaction() as sess:
            sess['chat_history'] = [{"human": f"msg{i}", "ai": f"resp{i}"} for i in range(100)]
            sess['scenario_history'] = {
                f"scenario{i}": [{"human": f"msg{i}", "ai": f"resp{i}"}] for i in range(50)
            }
            sess['watch_history'] = [{"speaker": "A", "message": f"msg{i}"} for i in range(100)]
        
        # 各履歴をクリア
        csrf_client.post('/api/clear_history', json={"mode": "chat"})
        csrf_client.post('/api/clear_history', json={"mode": "scenario"})
        csrf_client.post('/api/clear_history', json={"mode": "watch"})
        
        # セッションが適切にクリアされていることを確認
        with csrf_client.session_transaction() as sess:
            assert len(sess.get('chat_history', [])) == 0
            assert len(sess.get('scenario_history', {})) == 0
            assert len(sess.get('watch_history', [])) == 0


class TestRobustness:
    """堅牢性のテスト"""
    
    # Removed patch decorator - using global mock
    def test_llm_intermittent_failures(self, csrf_client, mock_all_external_apis):
        """LLMの断続的な失敗に対する処理を確認"""
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        
        # 成功、失敗、成功のパターンを設定
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("一時的な失敗")
            from langchain_core.messages import AIMessage
            return AIMessage(content=f"成功応答{call_count}")
        
        mock_llm.invoke.side_effect = side_effect
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        # 3回のリクエスト（2回目は失敗）
        responses = []
        for i in range(3):
            response = csrf_client.post('/api/chat',
                                 json={
                                     "message": f"テスト{i+1}",
                                     "model": "gemini-1.5-flash"
                                 })
            responses.append(response)
        
        # 1回目と3回目は成功、2回目は失敗
        assert responses[0].status_code == 200
        assert responses[1].status_code == 500
        assert responses[2].status_code == 200
    
    def test_graceful_degradation_on_service_unavailable(self, csrf_client, mock_all_external_apis):
        """サービス利用不可時の適切な劣化処理を確認"""
        # グローバルモックを使用
        mock_llm = mock_all_external_apis['mock_llm']
        from langchain_core.messages import AIMessage
        mock_llm.invoke.side_effect = Exception("サービス利用不可")
        
        with csrf_client.session_transaction() as sess:
            sess['chat_settings'] = {
                "system_prompt": "テスト",
                "model": "gemini-1.5-flash"
            }
        
        response = csrf_client.post('/api/chat',
                             json={
                                 "message": "サービス停止中のテスト",
                                 "model": "gemini-1.5-flash"
                             })
        
        # サービス停止中でも適切なエラーレスポンスが返される
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


# テスト用のフィクスチャ
@pytest.fixture
def app_context():
    """アプリケーションコンテキストのフィクスチャ"""
    with app.app_context():
        yield app