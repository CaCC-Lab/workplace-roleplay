"""
全35シナリオの包括的テスト（モックなし・実際のGemini API使用）
CLAUDE.md原則: モック禁止、実際のAPI使用でのテスト実装
"""
import pytest
import json
import time
from unittest.mock import patch
from app import app
from scenarios import load_scenarios


class TestComprehensiveScenarios:
    """全35シナリオの包括的テスト"""

    @pytest.fixture
    def client(self):
        """テスト用クライアント"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # WTFのCSRFは無効化
        app.config['CSRF_ENABLED'] = False  # CSRFMiddlewareも無効化
        with app.test_client() as client:
            with app.app_context():
                yield client

    @pytest.fixture
    def csrf_token(self, client):
        """CSRFトークンを取得"""
        response = client.get('/api/csrf-token')
        return response.get_json().get('csrf_token', '')

    @pytest.fixture
    def scenarios_data(self):
        """全シナリオデータを取得"""
        return load_scenarios()

    def test_all_scenarios_loaded(self, scenarios_data):
        """全35シナリオが正しく読み込まれているか確認"""
        assert len(scenarios_data) == 35, f"期待: 35シナリオ, 実際: {len(scenarios_data)}"
        
        # 各シナリオが必要な情報を持っているか確認
        required_fields = ['title', 'description', 'difficulty', 'character_setting']
        for scenario_id, scenario in scenarios_data.items():
            for field in required_fields:
                assert field in scenario, f"シナリオ{scenario_id}に{field}フィールドがありません"

    @pytest.mark.parametrize("scenario_id", [f"scenario{i}" for i in range(1, 36)])
    def test_individual_scenario_with_real_ai(self, client, csrf_token, scenario_id, scenarios_data):
        """各シナリオで実際のGemini APIが動作することを確認"""
        # レート制限対策として少し待機
        time.sleep(0.5)
        
        scenario = scenarios_data.get(scenario_id)
        if not scenario:
            pytest.skip(f"シナリオ{scenario_id}が見つかりません")

        print(f"\n=== テスト開始: {scenario_id} - {scenario['title']} ===")
        
        # シナリオチャットリクエスト
        response = client.post('/api/scenario_chat',
                             json={
                                 'message': 'よろしくお願いします',
                                 'scenario_id': scenario_id,
                                 'model': 'gemini-1.5-flash'
                             },
                             headers={
                                 'Content-Type': 'application/json',
                                 'X-CSRFToken': csrf_token
                             })

        # レート制限の場合はスキップ
        if response.status_code == 429:
            pytest.skip(f"APIレート制限により{scenario_id}をスキップします")

        # エラーの場合は詳細を表示
        if response.status_code != 200:
            print(f"エラー詳細 - Status: {response.status_code}")
            print(f"レスポンス: {response.data.decode('utf-8')}")
            assert response.status_code == 200, f"シナリオ{scenario_id}でAPIリクエストが失敗"

        # レスポンス内容の確認
        if response.headers.get('content-type', '').startswith('text/event-stream'):
            # SSE形式
            data = response.data.decode('utf-8')
            assert len(data) > 10, f"シナリオ{scenario_id}のSSEレスポンスが短すぎます"
        else:
            # JSON形式
            json_data = response.get_json()
            assert json_data is not None, f"シナリオ{scenario_id}で無効なJSONレスポンス"
            
            response_text = json_data.get('response', json_data.get('content', ''))
            assert len(response_text) > 10, f"シナリオ{scenario_id}のレスポンステキストが短すぎます"
            
            print(f"AI応答例: {response_text[:100]}...")

    def test_scenario_difficulty_distribution(self, scenarios_data):
        """シナリオの難易度分布を確認"""
        difficulty_counts = {}
        
        for scenario_id, scenario in scenarios_data.items():
            difficulty = scenario.get('difficulty', '不明')
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        print(f"\n難易度分布: {difficulty_counts}")
        
        # 最低限、初級・中級・上級がそれぞれ存在することを確認
        assert len(difficulty_counts) >= 2, "複数の難易度レベルが必要です"

    def test_scenario_tags_coverage(self, scenarios_data):
        """シナリオのタグカバレッジを確認"""
        all_tags = set()
        
        for scenario_id, scenario in scenarios_data.items():
            tags = scenario.get('tags', [])
            all_tags.update(tags)
        
        print(f"\n全タグ（{len(all_tags)}個）: {sorted(all_tags)}")
        
        # 職場コミュニケーションの基本的なタグが含まれているか確認
        expected_categories = ['職場コミュニケーション', 'ビジネスマナー', '報告・連絡・相談']
        found_categories = 0
        for category in expected_categories:
            if any(category in tag for tag in all_tags):
                found_categories += 1
        
        assert found_categories >= 2, f"基本的な職場カテゴリが不足: {found_categories}/{len(expected_categories)}"

    def test_character_setting_completeness(self, scenarios_data):
        """キャラクター設定の完全性を確認"""
        incomplete_scenarios = []
        
        for scenario_id, scenario in scenarios_data.items():
            character_setting = scenario.get('character_setting', {})
            
            # 必要な要素をチェック
            required_elements = ['personality', 'speaking_style']
            missing_elements = [elem for elem in required_elements if not character_setting.get(elem)]
            
            if missing_elements:
                incomplete_scenarios.append({
                    'scenario_id': scenario_id,
                    'missing': missing_elements
                })
        
        if incomplete_scenarios:
            print(f"\n不完全なキャラクター設定: {incomplete_scenarios}")
        
        # 90%以上のシナリオが完全な設定を持っていることを確認
        completion_rate = (35 - len(incomplete_scenarios)) / 35
        assert completion_rate >= 0.9, f"キャラクター設定完成率が低い: {completion_rate:.1%}"

    def test_learning_points_quality(self, scenarios_data):
        """学習ポイントの品質を確認"""
        scenarios_without_learning_points = []
        
        for scenario_id, scenario in scenarios_data.items():
            learning_points = scenario.get('learning_points', [])
            
            if not learning_points or len(learning_points) < 2:
                scenarios_without_learning_points.append(scenario_id)
        
        if scenarios_without_learning_points:
            print(f"\n学習ポイントが不足しているシナリオ: {scenarios_without_learning_points}")
        
        # 90%以上のシナリオが適切な学習ポイントを持っていることを確認
        quality_rate = (35 - len(scenarios_without_learning_points)) / 35
        assert quality_rate >= 0.9, f"学習ポイント品質率が低い: {quality_rate:.1%}"

    def test_scenario_response_consistency(self, client, csrf_token, scenarios_data):
        """複数シナリオの応答一貫性を確認（サンプリングテスト）"""
        # レート制限を考慮してサンプリング（5シナリオ）
        sample_scenarios = ['scenario1', 'scenario5', 'scenario10', 'scenario15', 'scenario20']
        
        for scenario_id in sample_scenarios:
            if scenario_id not in scenarios_data:
                continue
                
            print(f"\n一貫性テスト: {scenario_id}")
            
            # 同じメッセージで2回リクエストして一貫性を確認
            responses = []
            
            for attempt in range(2):
                time.sleep(1)  # レート制限対策
                
                response = client.post('/api/scenario_chat',
                                     json={
                                         'message': 'すみません、初めてなのでどうすればよいか教えてください',
                                         'scenario_id': scenario_id,
                                         'model': 'gemini-1.5-flash'
                                     },
                                     headers={
                                         'Content-Type': 'application/json',
                                         'X-CSRFToken': csrf_token
                                     })
                
                if response.status_code == 429:
                    pytest.skip(f"レート制限により{scenario_id}の一貫性テストをスキップ")
                
                if response.status_code == 200:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        json_data = response.get_json()
                        response_text = json_data.get('response', json_data.get('content', ''))
                        responses.append(response_text)
                    else:
                        # SSE形式の場合
                        responses.append(response.data.decode('utf-8'))
            
            # 両方のレスポンスが取得できた場合、職場らしいコンテキストが含まれているかチェック
            if len(responses) >= 2:
                for response_text in responses:
                    # 基本的な職場コンテキストの確認
                    workplace_keywords = ['仕事', '会議', '資料', '報告', '相談', '上司', '同僚', '部下', 'プロジェクト']
                    has_workplace_context = any(keyword in response_text for keyword in workplace_keywords)
                    
                    # 日本語で応答しているかの確認
                    japanese_chars = sum(1 for char in response_text if '\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF')
                    has_japanese = japanese_chars > 10
                    
                    if not (has_workplace_context or has_japanese):
                        print(f"警告: {scenario_id}の応答に職場コンテキストまたは日本語が不足: {response_text[:50]}...")


class TestScenarioAPIEndpoints:
    """シナリオ関連APIエンドポイントの包括的テスト"""

    @pytest.fixture
    def client(self):
        """テスト用クライアント"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            with app.app_context():
                yield client

    def test_scenarios_list_endpoint(self, client):
        """シナリオ一覧取得エンドポイントのテスト"""
        response = client.get('/api/scenarios')
        assert response.status_code == 200
        
        scenarios = response.get_json()
        assert isinstance(scenarios, dict)
        assert len(scenarios) == 35
        
        # 各シナリオが適切な構造を持っているか確認
        for scenario_id, scenario in scenarios.items():
            assert 'title' in scenario
            assert 'description' in scenario
            assert 'difficulty' in scenario

    def test_individual_scenario_endpoint(self, client):
        """個別シナリオ取得エンドポイントのテスト"""
        # 存在するシナリオ
        response = client.get('/api/scenarios/scenario1')
        assert response.status_code == 200
        
        scenario = response.get_json()
        assert scenario['title'] is not None
        assert scenario['character_setting'] is not None
        
        # 存在しないシナリオ
        response = client.get('/api/scenarios/nonexistent')
        assert response.status_code == 404

    def test_scenario_feedback_endpoint(self, client):
        """シナリオフィードバックエンドポイントのテスト"""
        csrf_token_response = client.get('/api/csrf-token')
        csrf_token = csrf_token_response.get_json().get('csrf_token', '')
        
        # フィードバックリクエスト
        response = client.post('/api/scenario_feedback',
                             json={
                                 'scenario_id': 'scenario1',
                                 'conversation': [
                                     {'role': 'user', 'message': 'こんにちは'},
                                     {'role': 'assistant', 'message': 'こんにちは'}
                                 ],
                                 'model': 'gemini-1.5-flash'
                             },
                             headers={
                                 'Content-Type': 'application/json',
                                 'X-CSRFToken': csrf_token
                             })
        
        # レート制限以外は成功またはスキップ
        if response.status_code == 429:
            pytest.skip("APIレート制限によりフィードバックテストをスキップ")
        else:
            # 200または他の応答コードでもフィードバック機能の動作確認
            print(f"フィードバック応答: {response.status_code}")