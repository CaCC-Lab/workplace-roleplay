"""
自己分析ワークシート統合テスト（CSRF無効化版）
"""
import pytest
import json
from datetime import datetime
from app import app


class TestSelfReflectionIntegration:
    """自己分析ワークシート統合テストクラス"""
    
    @pytest.fixture
    def client(self):
        """テスト用のFlaskクライアント（CSRF無効）"""
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['WTF_CSRF_ENABLED'] = False  # CSRFを無効化
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def sample_reflection_data(self):
        """サンプルの自己分析データ"""
        return {
            "scenarioId": "scenario1",
            "conversationId": "conv_test_123",
            "responses": {
                "reason": "相手に失礼にならないようにしたかったから",
                "perception": "理解してもらえたと思う",
                "future": "もっとはっきりと自分の意見を言いたい",
                "learning": "自分は緊張すると早口になることに気づいた"
            },
            "emotions": ["緊張", "不安", "安心"],
            "timestamp": datetime.now().isoformat()
        }
    
    def test_end_to_end_workflow(self, client, sample_reflection_data):
        """エンドツーエンドのワークフローテスト"""
        # 1. 会話履歴をセッションに設定
        with client.session_transaction() as sess:
            sess['scenario_history'] = {
                "scenario1": [
                    {"role": "assistant", "content": "どうしましたか？"},
                    {"role": "user", "content": "実は相談があるんです..."},
                    {"role": "assistant", "content": "どんな相談ですか？詳しく教えてください。"},
                    {"role": "user", "content": "プロジェクトの進め方で悩んでいます。"}
                ]
            }
        
        # 2. 自己分析ワークシートを提出
        response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        conversation_id = data['conversation_id']
        
        # 3. API経由で分析結果を取得
        response = client.get(f'/api/analysis/{conversation_id}')
        assert response.status_code == 200
        
        analysis_data = response.get_json()
        assert analysis_data['success'] is True
        assert analysis_data['conversation_id'] == conversation_id
        
        # 4. 分析結果の内容を検証
        analysis = analysis_data['analysis']
        assert 'communication_patterns' in analysis
        assert 'consultant_insights' in analysis
        assert 'growth_points' in analysis
        
        # 5. HTMLページの表示を確認
        response = client.get(f'/analysis/{conversation_id}')
        assert response.status_code == 200
        assert '会話分析結果'.encode('utf-8') in response.data
    
    def test_scenario_validation(self, client):
        """シナリオIDの検証テスト"""
        invalid_data = {
            "scenarioId": "999",  # 存在しないシナリオID
            "conversationId": "conv_test",
            "responses": {
                "reason": "test",
                "perception": "test",
                "future": "test",
                "learning": "test"
            },
            "emotions": ["test"]
        }
        
        response = client.post(
            '/api/self-reflection/submit',
            json=invalid_data,
            headers={'Content-Type': 'application/json'}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert '無効なシナリオID' in data['error']
    
    def test_analysis_persistence(self, client, sample_reflection_data):
        """分析結果の永続性テスト"""
        # 会話履歴を設定
        with client.session_transaction() as sess:
            sess['scenario_history'] = {
                "scenario1": [
                    {"role": "assistant", "content": "テスト"},
                    {"role": "user", "content": "テスト応答"}
                ]
            }
        
        # 提出
        response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code == 200
        
        # 複数回アクセスしても同じ結果が得られることを確認
        conversation_id = response.get_json()['conversation_id']
        
        for _ in range(3):
            response = client.get(f'/api/analysis/{conversation_id}')
            assert response.status_code == 200
            data = response.get_json()
            assert data['conversation_id'] == conversation_id
    
    def test_empty_responses_validation(self, client):
        """空の回答の検証テスト"""
        empty_data = {
            "scenarioId": "scenario1",
            "conversationId": "conv_test",
            "responses": {
                "reason": "",  # 空の回答
                "perception": "",
                "future": "",
                "learning": ""
            },
            "emotions": []
        }
        
        # 会話履歴を設定
        with client.session_transaction() as sess:
            sess['scenario_history'] = {"scenario1": [{"role": "user", "content": "test"}]}
        
        response = client.post(
            '/api/self-reflection/submit',
            json=empty_data,
            headers={'Content-Type': 'application/json'}
        )
        
        # PostConversationAnalyzerの現在の実装では空の回答も受け入れられる
        # 実際のアプリケーションではフロントエンドで検証される
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])