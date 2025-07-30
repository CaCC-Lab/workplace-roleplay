"""
自己分析ワークシートAPIのテスト
"""
import pytest
import json
from datetime import datetime
from flask import session
from app import app, scenarios


class TestSelfReflectionAPI:
    """自己分析ワークシートAPIのテストクラス"""
    
    @pytest.fixture
    def client(self):
        """テスト用のFlaskクライアント"""
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['WTF_CSRF_ENABLED'] = False  # テスト環境でCSRFを無効化
        app.config['CSRF_ENABLED'] = False  # CSRFMiddlewareも無効化
        
        # CSRFToken.require_csrfデコレータを一時的に無効化
        import utils.security
        original_require_csrf = utils.security.CSRFToken.require_csrf
        
        def mock_require_csrf(f):
            return f
        
        utils.security.CSRFToken.require_csrf = staticmethod(mock_require_csrf)
        
        with app.test_client() as client:
            yield client
            
        # デコレータを元に戻す
        utils.security.CSRFToken.require_csrf = original_require_csrf
    
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
    
    @pytest.fixture
    def setup_session_with_conversation(self, client):
        """会話履歴を含むセッションをセットアップ"""
        with client.session_transaction() as sess:
            sess['scenario_history'] = {
                "scenario1": [
                    {"role": "assistant", "content": "どうしましたか？"},
                    {"role": "user", "content": "実は相談があるんです..."}
                ]
            }
    
    def test_submit_self_reflection_success(self, client, sample_reflection_data, setup_session_with_conversation):
        """自己分析ワークシート提出の成功テスト"""
        # CSRFトークンを適切に生成するため、まずGETリクエストでトークンを取得
        get_response = client.get('/api/csrf-token')
        assert get_response.status_code == 200
        token = get_response.get_json()['csrf_token']
        
        response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.get_json()}")
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['conversation_id'] == "conv_test_123"
        assert data['analysis_available'] is True
        assert 'message' in data
    
    def test_submit_self_reflection_missing_fields(self, client, setup_session_with_conversation):
        """必須フィールドが欠けている場合のテスト"""
        # CSRFトークンを取得
        get_response = client.get('/api/csrf-token')
        assert get_response.status_code == 200
        token = get_response.get_json()['csrf_token']
        
        incomplete_data = {
            "scenarioId": "scenario1",
            "conversationId": "conv_test_123"
            # responses と emotions が欠けている
        }
        
        response = client.post(
            '/api/self-reflection/submit',
            json=incomplete_data,
            headers={
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'responses' in data['error']
    
    def test_submit_self_reflection_invalid_scenario(self, client, sample_reflection_data):
        """無効なシナリオIDの場合のテスト"""
        # CSRFトークンを取得
        get_response = client.get('/api/csrf-token')
        assert get_response.status_code == 200
        token = get_response.get_json()['csrf_token']
        
        sample_reflection_data['scenarioId'] = 'invalid_scenario'
        
        response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert '無効なシナリオID' in data['error']
    
    def test_submit_self_reflection_no_conversation_history(self, client, sample_reflection_data):
        """会話履歴がない場合のテスト"""
        # CSRFトークンを取得
        get_response = client.get('/api/csrf-token')
        assert get_response.status_code == 200
        token = get_response.get_json()['csrf_token']
        
        # scenario_history を設定しない
        
        response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            }
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert '会話履歴が見つかりません' in data['error']
    
    def test_submit_self_reflection_csrf_protection(self, client, sample_reflection_data):
        """CSRF保護のテスト"""
        response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={'Content-Type': 'application/json'}
            # CSRFトークンなし
        )
        
        assert response.status_code in [400, 403]  # CSRFエラー
    
    def test_get_analysis_results_success(self, client, sample_reflection_data, setup_session_with_conversation):
        """分析結果取得の成功テスト"""
        # CSRFトークンを取得
        get_response = client.get('/api/csrf-token')
        assert get_response.status_code == 200
        token = get_response.get_json()['csrf_token']
        
        # まず自己分析を提出
        submit_response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            }
        )
        assert submit_response.status_code == 200
        
        # 分析結果を取得
        response = client.get('/api/analysis/conv_test_123')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['conversation_id'] == 'conv_test_123'
        assert 'scenario' in data
        assert 'self_reflection' in data
        assert 'analysis' in data
    
    def test_get_analysis_results_not_found(self, client):
        """存在しない分析結果の取得テスト"""
        response = client.get('/api/analysis/non_existent_id')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert '分析結果が見つかりません' in data['error']
    
    def test_show_analysis_page_success(self, client, sample_reflection_data, setup_session_with_conversation):
        """分析結果ページ表示の成功テスト"""
        # CSRFトークンを取得
        get_response = client.get('/api/csrf-token')
        assert get_response.status_code == 200
        token = get_response.get_json()['csrf_token']
        
        # まず自己分析を提出
        submit_response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            }
        )
        assert submit_response.status_code == 200
        
        # 分析結果ページを表示
        response = client.get('/analysis/conv_test_123')
        
        assert response.status_code == 200
        assert '会話分析結果'.encode('utf-8') in response.data  # HTMLに含まれるはず
    
    def test_show_analysis_page_not_found(self, client):
        """存在しない分析結果ページのテスト"""
        response = client.get('/analysis/non_existent_id')
        
        assert response.status_code == 404
        assert '分析結果が見つかりません'.encode('utf-8') in response.data
    
    def test_analysis_data_structure(self, client, sample_reflection_data, setup_session_with_conversation):
        """分析結果のデータ構造テスト"""
        # CSRFトークンを取得
        get_response = client.get('/api/csrf-token')
        assert get_response.status_code == 200
        token = get_response.get_json()['csrf_token']
        
        # まず自己分析を提出
        submit_response = client.post(
            '/api/self-reflection/submit',
            json=sample_reflection_data,
            headers={
                'X-CSRFToken': token,
                'Content-Type': 'application/json'
            }
        )
        assert submit_response.status_code == 200
        
        # 分析結果を取得して構造を確認
        response = client.get('/api/analysis/conv_test_123')
        data = response.get_json()
        
        # 分析結果の構造を検証
        analysis = data['analysis']
        assert 'communication_patterns' in analysis
        assert 'emotional_transitions' in analysis
        assert 'key_moments' in analysis
        assert 'alternative_responses' in analysis
        assert 'consultant_insights' in analysis
        assert 'growth_points' in analysis
        assert 'strengths_demonstrated' in analysis
        assert 'areas_for_improvement' in analysis
        
        # コミュニケーションパターンの構造
        patterns = analysis['communication_patterns']
        assert 'response_style' in patterns
        assert 'assertiveness_level' in patterns
        assert 'empathy_indicators' in patterns
        assert 'clarity_score' in patterns
        assert 'professionalism_score' in patterns
        
        # コンサルタント洞察の構造
        insights = analysis['consultant_insights']
        assert 'overall_assessment' in insights
        assert 'communication_style' in insights
        assert 'hidden_strengths' in insights
        assert 'growth_opportunities' in insights
        assert 'action_recommendations' in insights


if __name__ == "__main__":
    pytest.main([__file__, "-v"])